"""A stats panel that compares headline vs. verified metrics.

Implemented as a :class:`Static` whose body is rebuilt via :meth:`Static.update` so the
numbers refresh reliably after the widget is mounted (``compose`` only runs once, so a
``Container``-based rebuild would never update).
"""

from __future__ import annotations

from textual.widgets import Static

from hl_copytrade_verifier.core.models import VerificationReport


def _pct(x: float) -> str:
    sign = "+" if x >= 0 else ""
    return f"{sign}{x * 100:.1f}%"


class StatsPanel(Static):
    """Renders the headline/verified comparison block on the dashboard."""

    def __init__(self) -> None:
        super().__init__()
        self._report: VerificationReport | None = None

    def show(self, report: VerificationReport) -> None:
        self._report = report
        self.update(self._content_text())

    def _content_text(self) -> str:
        r = self._report
        if r is None:
            return "[dim]No trader verified yet — pick one in the Traders tab and press [b]r[/].[/]"

        gap_str = f"[bold yellow]{r.roi_gap * 100:+.1f} pp[/]"

        def cell(label: str, value: str, color: str = "") -> str:
            inner = f"[{color}]{value}[/]" if color else value
            return f"[dim italic]{label}[/]\n{inner}"

        rows = [
            # Row 1: ROI comparison (the headline insight).
            (
                cell("Headline ROI", _pct(r.headline_roi)),
                cell("Verified ROI", _pct(r.verified_roi), "bold green"),
                cell("Δ ROI", gap_str),
            ),
            # Row 2.
            (
                cell("Win rate", f"{r.win_rate * 100:.1f}%"),
                cell("Fee-adj. win", f"{r.fee_adjusted_win_rate * 100:.1f}%"),
                cell("Profit factor", f"{r.profit_factor:.2f}"),
            ),
            # Row 3.
            (
                cell("Martingale", f"{r.martingale_score:.2f}", "bold yellow"),
                cell("Outlier dep.", f"{r.outlier_dependence * 100:.0f}%", "bold red"),
                cell("Max drawdown", _pct(r.max_drawdown), "bold red"),
            ),
            # Row 4.
            (
                cell("Sharpe", f"{r.sharpe:.2f}"),
                cell("Significance", f"p={r.significance_p:.3f}", "green"),
                cell("Trades (90d)", f"{r.trades:,}"),
            ),
        ]
        # Render as a grid of padded columns.
        lines: list[str] = []
        for row in rows:
            lines.append("  │  ".join(f"{c}" for c in row))
        return "\n\n".join(lines)
