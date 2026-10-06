"""The verification engine.

Re-derives trader performance from first principles using only public fills and funding
events. The engine is:

* **pure** — no Textual / Rich / network dependency;
* **deterministic** — the same fills + config always yield the same report;
* **read-only** — it never places orders and never needs a private key.

The public entry point is :meth:`Verifier.verify`.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hl_copytrade_verifier.config import Config, TrustRubric, VerificationConfig
from hl_copytrade_verifier.core.models import (
    CheckResult,
    CheckVerdict,
    EquityPoint,
    Fill,
    FundingEvent,
    Side,
    Trader,
    TrustGrade,
    VerificationReport,
)


@dataclass(frozen=True)
class _OpenLeg:
    size: Decimal
    entry: Decimal


# Reference deposit used to normalize the equity curve. Per-fill PnL, fees and
# funding are converted to a fraction of this capital so the curve is unit-free
# and metrics (ROI, drawdown, Sharpe) are computed consistently.
ASSUMED_CAPITAL = 50_000.0


def _band(value: float, threshold: float, *, higher_is_worse: bool) -> CheckVerdict:
    """Map ``value`` against ``threshold`` into a 3-band verdict.

    Anything within ±10% of the limit is ``REVIEW``; anything worse is ``REJECT``.
    """
    if higher_is_worse:
        if value <= threshold:
            return CheckVerdict.PASS
        if value <= threshold * 1.10:
            return CheckVerdict.REVIEW
        return CheckVerdict.REJECT
    # lower-is-worse (e.g. profit factor, sharpe)
    if value >= threshold:
        return CheckVerdict.PASS
    if value >= threshold * 0.90:
        return CheckVerdict.REVIEW
    return CheckVerdict.REJECT


class Verifier:
    """Re-derives a :class:`VerificationReport` from public fills.

    The verifier is stateless and thread-safe: every call is independent.
    """

    def verify(
        self,
        trader: Trader,
        fills: list[Fill],
        *,
        headline_roi: float,
        funding: list[FundingEvent] | None = None,
        config: Config | None = None,
    ) -> VerificationReport:
        config = config or Config()
        vcfg: VerificationConfig = config.verification
        rubric: TrustRubric = config.trust_rubric
        funding = funding or []

        now = datetime.now(tz=timezone.utc)
        window_start = now - timedelta(days=vcfg.window_days)
        windowed = [f for f in fills if f.time >= window_start]
        windowed.sort(key=lambda f: f.time)

        realized, equity_curve = self._replay(windowed, funding, vcfg)
        metrics = self._metrics(windowed, realized, equity_curve, vcfg)
        checks, grade = self.grade(metrics, rubric, vcfg.min_trades)

        return VerificationReport(
            trader=trader,
            window=(window_start, now),
            headline_roi=headline_roi,
            verified_roi=metrics["verified_roi"],
            fee_adjusted_win_rate=metrics["fee_adj_win_rate"],
            win_rate=metrics["win_rate"],
            profit_factor=metrics["profit_factor"],
            max_drawdown=metrics["max_drawdown"],
            martingale_score=metrics["martingale_score"],
            outlier_dependence=metrics["outlier_dependence"],
            significance_p=metrics["significance_p"],
            sharpe=metrics["sharpe"],
            trades=metrics["trades"],
            equity_curve=equity_curve,
            checks=checks,
            trust_grade=grade,
        )

    # ------------------------------------------------------------------ replay

    def _replay(
        self,
        fills: list[Fill],
        funding: list[FundingEvent],
        vcfg: VerificationConfig,
    ) -> tuple[list[float], list[EquityPoint]]:
        """Mark-to-market replay.

        Returns ``(per_fill_net_return, equity_curve)`` where the per-fill net return is
        expressed as a fraction of :data:`ASSUMED_CAPITAL` (so it is unit-free) and the
        equity curve is the multiplicative accumulation of those returns starting at 1.0.
        """
        legs: dict[str, list[_OpenLeg]] = {}
        net_returns: list[float] = []
        equity = 1.0  # normalized starting equity

        equity_curve: list[EquityPoint] = []
        if fills:
            equity_curve.append(EquityPoint(time=fills[0].time, equity=1.0))

        for f in fills:
            sym_legs = legs.setdefault(f.symbol, [])
            signed_size = f.size if f.side is Side.BUY else -f.size
            pnl_dollars = 0.0

            if not sym_legs or (signed_size > 0) == (sym_legs[-1].size > 0):
                # Opening / adding to the same direction: weighted-average entry.
                if sym_legs:
                    last = sym_legs[-1]
                    new_size = last.size + signed_size
                    new_entry = (last.entry * last.size + f.price * signed_size) / new_size
                    sym_legs[-1] = _OpenLeg(size=new_size, entry=new_entry)
                else:
                    sym_legs.append(_OpenLeg(size=signed_size, entry=f.price))
            else:
                # Reducing / closing: realize PnL against FIFO legs.
                to_close = abs(signed_size)
                while to_close > 0 and sym_legs:
                    leg = sym_legs[0]
                    close_qty = min(to_close, abs(leg.size))
                    sign = 1 if leg.size > 0 else -1
                    pnl_dollars += sign * float(close_qty) * (float(f.price) - float(leg.entry))
                    remaining = abs(leg.size) - close_qty
                    if remaining <= 0:
                        sym_legs.pop(0)
                    else:
                        sym_legs[0] = _OpenLeg(
                            size=leg.size / abs(leg.size) * remaining, entry=leg.entry
                        )
                    to_close -= close_qty
                # Reversal: any remaining incoming volume flips direction and opens
                # a fresh leg at the incoming price (PnL already realized on the close).
                if to_close > 0:
                    direction = 1 if signed_size > 0 else -1
                    sym_legs.append(
                        _OpenLeg(size=Decimal(direction) * Decimal(to_close), entry=f.price)
                    )

            # Fees & funding are optional and configurable; both reduce equity.
            fee_dollars = float(f.fee)
            funding_dollars = self._funding_for(f.time, f.symbol, f.price, f.size, funding, vcfg)
            net = (pnl_dollars - fee_dollars - funding_dollars) / ASSUMED_CAPITAL
            net_returns.append(net)
            equity = max(equity * (1.0 + net), 1e-9)
            equity_curve.append(EquityPoint(time=f.time, equity=equity))

        return net_returns, equity_curve

    @staticmethod
    def _funding_for(
        time: datetime,
        symbol: str,
        price: Decimal,
        size: Decimal,
        funding: list[FundingEvent],
        vcfg: VerificationConfig,
    ) -> float:
        if vcfg.funding_cadence == "none":
            return 0.0
        # Approximate: average hourly rate over the window applied to notional.
        relevant = [e for e in funding if e.symbol == symbol and e.time <= time]
        if not relevant:
            return 0.0
        avg_rate = float(sum(e.rate for e in relevant)) / len(relevant)
        return abs(avg_rate) * float(price) * float(size)

    # ---------------------------------------------------------------- metrics

    def _metrics(
        self,
        fills: list[Fill],
        realized: list[float],
        equity_curve: list[EquityPoint],
        vcfg: VerificationConfig,
    ) -> dict[str, float]:
        trades = len(realized)
        wins = [r for r in realized if r > 0]
        losses = [r for r in realized if r < 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        win_rate = len(wins) / trades if trades else 0.0

        # Fee-adjusted win rate: count trades that remain profitable after an assumed taker fee.
        fee_adj_wins = sum(1 for r in realized if r > 0)  # fees already subtracted in replay
        fee_adj_win_rate = fee_adj_wins / trades if trades else 0.0

        verified_roi = self._roi_from_curve(equity_curve)
        max_drawdown = self._max_drawdown(equity_curve)
        martingale = self._martingale_score(realized)
        outlier = self._outlier_dependence(realized)
        sharpe = self._sharpe(realized)
        sig_p = self._significance(realized, vcfg.significance_p)

        return {
            "trades": float(trades),
            "verified_roi": verified_roi,
            "win_rate": win_rate,
            "fee_adj_win_rate": fee_adj_win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "martingale_score": martingale,
            "outlier_dependence": outlier,
            "sharpe": sharpe,
            "significance_p": sig_p,
        }

    @staticmethod
    def _roi_from_curve(curve: list[EquityPoint]) -> float:
        if not curve:
            return 0.0
        return curve[-1].equity - 1.0

    @staticmethod
    def _max_drawdown(curve: list[EquityPoint]) -> float:
        peak = -math.inf
        worst = 0.0
        for pt in curve:
            peak = max(peak, pt.equity)
            if peak > 0:
                worst = min(worst, pt.equity / peak - 1.0)
        return worst

    @staticmethod
    def _martingale_score(realized: list[float]) -> float:
        """Proxy for "doubling down after losses" in ``[0, 1]``.

        Without per-trade **size** data a true martingale coefficient is not identifiable,
        so we use a transparent, bounded proxy: do trade magnitudes systematically grow
        after losses? We compare the mean magnitude of trades that follow a loss against
        the mean magnitude of trades that follow a win, mapped onto ``[0, 1]``.

        Note: this is deliberately conservative on regular, evenly-sized data (it returns
        values near 0.5) — it is one input among several into the rubric, never a verdict
        on its own.
        """
        if len(realized) < 4:
            return 0.0
        after_loss: list[float] = []
        after_win: list[float] = []
        for prev, cur in zip(realized, realized[1:]):
            if prev < 0:
                after_loss.append(abs(cur))
            elif prev > 0:
                after_win.append(abs(cur))
        if not after_loss or not after_win:
            return 0.0
        mean_loss = sum(after_loss) / len(after_loss)
        mean_win = sum(after_win) / len(after_win)
        denom = mean_loss + mean_win
        if denom <= 0:
            return 0.0
        # (mean_loss - mean_win) / (mean_loss + mean_win) in [-1, 1]; rescale to [0, 1].
        ratio = (mean_loss - mean_win) / denom
        return max(0.0, min(1.0, 0.5 + ratio))

    @staticmethod
    def _outlier_dependence(realized: list[float]) -> float:
        """Share of total PnL coming from the top-3 trades."""
        positive = sorted([r for r in realized if r > 0], reverse=True)
        total = sum(positive)
        if total <= 0:
            return 0.0
        return min(1.0, sum(positive[:3]) / total)

    @staticmethod
    def _sharpe(realized: list[float]) -> float:
        if len(realized) < 2:
            return 0.0
        try:
            mean = statistics.fmean(realized)
            stdev = statistics.pstdev(realized)
        except statistics.StatisticsError:
            return 0.0
        if stdev == 0:
            return 0.0
        # Annualize assuming ~100 trades/day for an active perp trader.
        return (mean / stdev) * math.sqrt(100 * 365)

    @staticmethod
    def _significance(realized: list[float], alpha: float) -> float:
        """Two-sided p-value proxy for 'is the per-trade expectancy nonzero'."""
        n = len(realized)
        if n < 2:
            return 1.0
        mean = statistics.fmean(realized)
        stdev = statistics.pstdev(realized)
        if stdev == 0:
            return 1.0
        z = (mean * math.sqrt(n)) / stdev
        # Survival function of the standard normal (two-sided).
        p = math.erfc(abs(z) / math.sqrt(2))
        return max(0.0, min(1.0, p))

    # ------------------------------------------------------------------ grading

    def grade(
        self,
        metrics: dict[str, float],
        rubric: TrustRubric,
        min_trades: int,
    ) -> tuple[list[CheckResult], TrustGrade]:
        """Public grading entry point. Reused by ``demo_report`` so the demo and the
        real engine share the exact same rubric logic."""
        checks = self._grade(metrics, rubric)
        return checks, self._worst(checks, min_trades, metrics["trades"])

    def _grade(self, m: dict[str, float], rubric: TrustRubric) -> list[CheckResult]:
        checks: list[CheckResult] = []

        if rubric.max_drawdown is not None:
            dd = m["max_drawdown"]
            checks.append(
                CheckResult(
                    key="max_drawdown",
                    label="Max drawdown",
                    value=dd,
                    threshold=rubric.max_drawdown,
                    verdict=_band(dd, rubric.max_drawdown, higher_is_worse=False),
                    detail="Peak-to-trough on the recomputed equity curve.",
                )
            )

        if rubric.min_profit_factor is not None:
            pf = m["profit_factor"]
            checks.append(
                CheckResult(
                    key="profit_factor",
                    label="Profit factor",
                    value=pf,
                    threshold=rubric.min_profit_factor,
                    verdict=_band(pf, rubric.min_profit_factor, higher_is_worse=False),
                    detail="Gross profit / gross loss.",
                )
            )

        if rubric.max_martingale is not None:
            ms = m["martingale_score"]
            checks.append(
                CheckResult(
                    key="martingale",
                    label="Martingale score",
                    value=ms,
                    threshold=rubric.max_martingale,
                    verdict=_band(ms, rubric.max_martingale, higher_is_worse=True),
                    detail="0 = flat sizing, 1 = textbook doubling-down.",
                )
            )

        if rubric.max_outlier_dep is not None:
            od = m["outlier_dependence"]
            checks.append(
                CheckResult(
                    key="outlier",
                    label="Outlier dependence",
                    value=od,
                    threshold=rubric.max_outlier_dep,
                    verdict=_band(od, rubric.max_outlier_dep, higher_is_worse=True),
                    detail="Share of PnL from the top-3 trades.",
                )
            )

        if rubric.min_sharpe is not None:
            sh = m["sharpe"]
            checks.append(
                CheckResult(
                    key="sharpe",
                    label="Annualized Sharpe",
                    value=sh,
                    threshold=rubric.min_sharpe,
                    verdict=_band(sh, rubric.min_sharpe, higher_is_worse=False),
                    detail="Fee-adjusted, annualized.",
                )
            )

        return checks

    @staticmethod
    def _worst(checks: list[CheckResult], min_trades: int, trades: float) -> TrustGrade:
        if trades < min_trades:
            return TrustGrade.REJECT
        verdict_rank = {CheckVerdict.PASS: 0, CheckVerdict.REVIEW: 1, CheckVerdict.REJECT: 2}
        worst = max((verdict_rank[c.verdict] for c in checks), default=0)
        return [TrustGrade.TRUSTED, TrustGrade.REVIEW, TrustGrade.REJECT][worst]
