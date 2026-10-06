"""Deterministic demo dataset for ``--demo`` mode.

Seeds a handful of fictional trader addresses with plausible fill histories so the TUI
can be previewed, screenshot, and tested with **zero network access**. Every address here
is a fabricated placeholder — none of them correspond to real Hyperliquid accounts.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from hl_copytrade_verifier.core.models import (
    CheckResult,
    CheckVerdict,
    EquityPoint,
    Fill,
    Position,
    Side,
    Trader,
    TrustGrade,
    VerificationReport,
)

# Fixed "now" so the dataset is reproducible across runs (no wall-clock dependence).
_DEMO_NOW = datetime(2026, 7, 19, 14, 2, tzinfo=timezone.utc)

_SYMBOLS = ("BTC-PERP", "ETH-PERP", "SOL-PERP", "HYPE-PERP", "KASPA-PERP", "POKT-PERP")
_BASE_PRICES = {
    "BTC-PERP": Decimal("67210.5"),
    "ETH-PERP": Decimal("3418.2"),
    "SOL-PERP": Decimal("178.4"),
    "HYPE-PERP": Decimal("22.85"),
    "KASPA-PERP": Decimal("0.1460"),
    "POKT-PERP": Decimal("0.2940"),
}


def demo_traders() -> list[Trader]:
    """A small watchlist of fictional traders with graded personas."""
    return [
        Trader(
            address="0x7f3a91c4e1aabb02d774e9f0c5d8a1b3e6f9c4e1",
            alias="quant_kappa",
            verified_at=_DEMO_NOW,
        ),
        Trader(
            address="0xab24de0f7781cc5529b34f10a98c7d2e5b8a1033",
            alias="leverage_ape",
            verified_at=_DEMO_NOW - timedelta(hours=6),
        ),
        Trader(
            address="0xc0ffee15dec0ffee15dec0ffee15dec0ffee15de",
            alias="steady_basis",
            verified_at=_DEMO_NOW - timedelta(days=1),
        ),
        Trader(
            address="0x9999aaaabbbbccccddddeeee1111222233334444",
            alias="wash_suspect",
            verified_at=None,
        ),
    ]


def demo_headline_roi(trader: Trader) -> float:
    """The (inflated) number a leaderboard *would* show."""
    return {
        "quant_kappa": 4.128,
        "leverage_ape": 12.74,
        "steady_basis": 0.84,
        "wash_suspect": 3.05,
    }.get(trader.alias, 1.0)


def demo_fills(trader: Trader, *, days: int = 90, trades: int = 1284) -> list[Fill]:
    """Generate a deterministic fill history for a trader persona.

    Persona behaviour is keyed off the alias so each trader looks distinct:
    ``quant_kappa`` is a steady winner, ``leverage_ape`` is high-variance, etc.
    """
    persona = {
        "quant_kappa": {"edge": 0.0009, "vol": 0.012, "win_bias": 0.10, "leverage": 5},
        "leverage_ape": {"edge": 0.0004, "vol": 0.030, "win_bias": 0.03, "leverage": 20},
        "steady_basis": {"edge": 0.0006, "vol": 0.006, "win_bias": 0.06, "leverage": 2},
        "wash_suspect": {"edge": 0.0002, "vol": 0.020, "win_bias": 0.02, "leverage": 10},
    }.get(trader.alias, {"edge": 0.0005, "vol": 0.015, "win_bias": 0.05, "leverage": 5})

    fills: list[Fill] = []
    # Deterministic pseudo-random stream (no Math.random / time dependency).
    seed = sum(ord(c) for c in trader.alias) + days + trades
    rng = _LCG(seed)

    start = _DEMO_NOW - timedelta(days=days)
    for i in range(trades):
        sym = _SYMBOLS[i % len(_SYMBOLS)]
        base = _BASE_PRICES[sym]
        # Tiny drift + persona-vol noise on price.
        drift = persona["edge"] * (i % 17)
        noise = (rng() - 0.5) * persona["vol"]
        price = base * Decimal(1 + drift + noise)

        # Slight win-rate bias per persona; alternate direction to keep positions bounded.
        side = Side.BUY if (i + int(rng() * 2)) % 2 == 0 else Side.SELL
        # Sizing scales mildly with persona leverage.
        base_qty = {
            "BTC-PERP": Decimal("0.40"),
            "ETH-PERP": Decimal("5.0"),
            "SOL-PERP": Decimal("120"),
            "HYPE-PERP": Decimal("900"),
            "KASPA-PERP": Decimal("180000"),
            "POKT-PERP": Decimal("90000"),
        }[sym]
        size = base_qty * Decimal(str(round(0.5 + rng() * persona["leverage"] / 5, 3)))
        fee = (price * size * Decimal("0.00035")).quantize(Decimal("0.0001"))

        fills.append(
            Fill(
                time=start + timedelta(minutes=round(((days * 24 * 60) / trades) * i, 2)),
                symbol=sym,
                side=side,
                price=price.quantize(Decimal("0.0001")),
                size=size,
                fee=fee,
                is_taker=True,
            )
        )
    return fills


def demo_positions(trader: Trader) -> list[Position]:
    """A handful of currently-open positions for the live-monitor screen."""
    persona = trader.alias
    rows = [
        ("BTC-PERP", Side.BUY, Decimal("142300.00"), Decimal("67210.5"), Decimal("68015.2"), Decimal("5.0"), Decimal("54180.0")),
        ("ETH-PERP", Side.BUY, Decimal("88710.00"), Decimal("3418.2"), Decimal("3462.1"), Decimal("4.0"), Decimal("2724.0")),
        ("SOL-PERP", Side.SELL, Decimal("31400.00"), Decimal("178.4"), Decimal("174.9"), Decimal("3.0"), None),
    ]
    if persona == "leverage_ape":
        rows.append(
            ("HYPE-PERP", Side.BUY, Decimal("210500.00"), Decimal("21.40"), Decimal("22.85"), Decimal("20.0"), Decimal("20.35"))
        )
    return [
        Position(
            symbol=sym,
            side=sd,
            size_usd=sz,
            entry_price=ep,
            mark_price=mp,
            leverage=lv,
            liquidation_price=lq,
        )
        for sym, sd, sz, ep, mp, lv, lq in rows
    ]


def demo_now() -> datetime:
    """The frozen reference time used across the demo dataset."""
    return _DEMO_NOW


class _LCG:
    """A tiny deterministic linear-congruential generator (no global RNG state)."""

    def __init__(self, seed: int) -> None:
        self._state = seed & 0x7FFFFFFF

    def __call__(self) -> float:
        # Numerical Recipes constants.
        self._state = (1664525 * self._state + 1013904223) & 0x7FFFFFFF
        return self._state / 0x7FFFFFFF


# Predetermined, plausible metrics per trader persona.
# These are the *verified* (fee- & funding-adjusted) numbers the verifier would surface.
# The headline (inflated) ROI is in demo_headline_roi() above.
_PERSONA_REPORTS: dict[str, dict[str, float]] = {
    "quant_kappa": {
        "verified_roi": 3.184,
        "win_rate": 0.713,
        "fee_adj_win_rate": 0.649,
        "profit_factor": 2.84,
        "max_drawdown": -0.312,
        "martingale_score": 0.43,
        "outlier_dependence": 0.32,
        "sharpe": 1.82,
        "significance_p": 0.013,
        "trades": 1284,
    },
    "leverage_ape": {
        "verified_roi": 5.207,
        "win_rate": 0.521,
        "fee_adj_win_rate": 0.468,
        "profit_factor": 1.38,
        "max_drawdown": -0.612,
        "martingale_score": 0.81,
        "outlier_dependence": 0.58,
        "sharpe": 0.74,
        "significance_p": 0.094,
        "trades": 412,
    },
    "steady_basis": {
        "verified_roi": 0.624,
        "win_rate": 0.731,
        "fee_adj_win_rate": 0.704,
        "profit_factor": 2.41,
        "max_drawdown": -0.082,
        "martingale_score": 0.11,
        "outlier_dependence": 0.17,
        "sharpe": 2.73,
        "significance_p": 0.001,
        "trades": 2103,
    },
    "wash_suspect": {
        "verified_roi": -0.402,
        "win_rate": 0.481,
        "fee_adj_win_rate": 0.442,
        "profit_factor": 0.92,
        "max_drawdown": -0.718,
        "martingale_score": 0.85,
        "outlier_dependence": 0.71,
        "sharpe": -0.31,
        "significance_p": 0.612,
        "trades": 387,
    },
}


def _persona_curve(verified_roi: float, points: int) -> list[EquityPoint]:
    """Build a smooth equity curve ending at ``1 + verified_roi``."""
    target = 1.0 + verified_roi
    start = _DEMO_NOW - timedelta(days=90)
    if points <= 1:
        return [EquityPoint(time=_DEMO_NOW, equity=target)]
    span = points - 1
    out: list[EquityPoint] = []
    for i in range(points):
        frac = i / span
        # mild noise via deterministic LCG so the curve looks organic, not linear
        wobble = 0.012 * math.sin(i / 5.0) * (1 - frac)
        equity = 1.0 + (target - 1.0) * (frac ** 1.25) + wobble
        out.append(EquityPoint(time=start + timedelta(hours=span_hours(i, span)), equity=equity))
    return out


def span_hours(i: int, span: int) -> float:
    return round((90 * 24) * (i / max(span, 1)), 2)


def demo_report(trader: Trader, config) -> VerificationReport:
    """Return a fully-formed, predetermined :class:`VerificationReport`.

    In ``--demo`` mode the UI consumes this instead of running the verifier on
    synthetic fills, so the showcased numbers are stable and plausible. The
    rubric grading, however, still runs through the real :class:`Verifier` so
    the trust grade is computed by the exact same logic as live mode.
    """
    # Local import avoids a circular dependency at module load time.
    from hl_copytrade_verifier.core.verifier import Verifier

    persona = _PERSONA_REPORTS.get(trader.alias, _PERSONA_REPORTS["quant_kappa"])
    headline = demo_headline_roi(trader)
    points = getattr(getattr(config, "ui", None), "sparkline_points", 80) or 80
    curve = _persona_curve(persona["verified_roi"], points)

    checks, grade = Verifier().grade(persona, config.trust_rubric, config.verification.min_trades)

    return VerificationReport(
        trader=trader,
        window=(_DEMO_NOW - timedelta(days=90), _DEMO_NOW),
        headline_roi=headline,
        verified_roi=persona["verified_roi"],
        fee_adjusted_win_rate=persona["fee_adj_win_rate"],
        win_rate=persona["win_rate"],
        profit_factor=persona["profit_factor"],
        max_drawdown=persona["max_drawdown"],
        martingale_score=persona["martingale_score"],
        outlier_dependence=persona["outlier_dependence"],
        significance_p=persona["significance_p"],
        sharpe=persona["sharpe"],
        trades=int(persona["trades"]),
        equity_curve=curve,
        checks=checks,
        trust_grade=grade,
    )


def sample_equity_curve(points: int = 80) -> list[float]:
    """A smooth, upward-drifting equity curve for dashboard previews."""
    return [1.0 + 0.05 * i + 0.18 * math.sin(i / 6.0) + (i / points) ** 1.4 * 2.1 for i in range(points)]


def iter_demo_equity(points: Iterable[float]) -> list[tuple[datetime, float]]:
    return [(_DEMO_NOW - timedelta(minutes=(len(list(points)) - i) * 3), v) for i, v in enumerate(points)]
