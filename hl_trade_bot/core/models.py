"""Typed data models for the verification engine.

These types are intentionally framework-free (no Textual / Rich) so the entire
:mod:`hl_copytrade_verifier.core` package can be unit-tested and reused headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TrustGrade(str, Enum):
    """Final, human-readable grade assigned by the rubric."""

    TRUSTED = "TRUSTED"
    REVIEW = "REVIEW"
    REJECT = "REJECT"

    @property
    def icon(self) -> str:
        return {
            TrustGrade.TRUSTED.value: "🟢",
            TrustGrade.REVIEW.value: "🟠",
            TrustGrade.REJECT.value: "🔴",
        }[self.value]


class CheckVerdict(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Fill:
    """A single public fill. The atomic unit the verifier replays."""

    time: datetime
    symbol: str
    side: Side
    price: Decimal
    size: Decimal
    fee: Decimal = Decimal("0")
    is_taker: bool = True


@dataclass(frozen=True)
class FundingEvent:
    time: datetime
    symbol: str
    rate: Decimal  # hourly rate applied to open position notional


@dataclass(frozen=True)
class Position:
    """A currently-open position for the live monitor screen."""

    symbol: str
    side: Side
    size_usd: Decimal
    entry_price: Decimal
    mark_price: Decimal
    leverage: Decimal
    liquidation_price: Decimal | None

    @property
    def upnl_usd(self) -> Decimal:
        sign = 1 if self.side is Side.BUY else -1
        return sign * self.size_usd * (self.mark_price - self.entry_price) / self.entry_price


@dataclass(frozen=True)
class CheckResult:
    """One rubric check. The grade is the worst verdict across all checks."""

    key: str
    label: str
    value: float
    threshold: float | None
    verdict: CheckVerdict
    detail: str = ""


@dataclass(frozen=True)
class Trader:
    """A public Hyperliquid trader address under audit."""

    address: str
    alias: str = ""
    verified_at: datetime | None = None

    @property
    def short(self) -> str:
        return f"{self.address[:6]}…{self.address[-4:]}" if len(self.address) >= 12 else self.address


@dataclass(frozen=True)
class EquityPoint:
    time: datetime
    equity: float  # normalized to 1.0 at the start of the window


@dataclass(frozen=True)
class VerificationReport:
    """The full, deterministic output of :class:`Verifier.verify`."""

    trader: Trader
    window: tuple[datetime, datetime]
    headline_roi: float          # trust anchor (what the leaderboard says)
    verified_roi: float          # recomputed, fee- & funding-adjusted
    fee_adjusted_win_rate: float
    win_rate: float
    profit_factor: float
    max_drawdown: float          # negative, e.g. -0.34
    martingale_score: float      # 0..1
    outlier_dependence: float    # 0..1, share of PnL from top-3 trades
    significance_p: float
    sharpe: float
    trades: int
    equity_curve: list[EquityPoint] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    trust_grade: TrustGrade = TrustGrade.REVIEW

    @property
    def roi_gap(self) -> float:
        """Headline minus verified ROI, in percentage points."""
        return self.headline_roi - self.verified_roi

    def to_dict(self) -> dict[str, object]:
        return {
            "trader": self.trader.address,
            "headline_roi": self.headline_roi,
            "verified_roi": self.verified_roi,
            "fee_adjusted_win_rate": self.fee_adjusted_win_rate,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "martingale_score": self.martingale_score,
            "outlier_dependence": self.outlier_dependence,
            "significance_p": self.significance_p,
            "sharpe": self.sharpe,
            "trades": self.trades,
            "trust_grade": self.trust_grade.value,
            "checks": [c.__dict__ for c in self.checks],
        }
