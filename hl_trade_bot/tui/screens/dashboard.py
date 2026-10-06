"""Dashboard pane — the single-pane-of-glass overview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from hl_copytrade_verifier.core.models import Position, TrustGrade, VerificationReport
from hl_copytrade_verifier.core.mock_data import demo_positions, sample_equity_curve
from hl_copytrade_verifier.tui.widgets import EquitySpark, PositionTable, StatsPanel, TrustBadge


class DashboardPane(Vertical):
    """Top-level overview: trust badge, stats, equity curve, top open positions."""

    DEFAULT_CSS = """
    DashboardPane { padding: 1 2; }
    DashboardPane Static#dash-title { text-style: bold; margin-bottom: 1; }
    DashboardPane EquitySpark { height: 6; margin: 1 0; border: round $accent; }
    DashboardPane PositionTable { height: 1fr; margin-top: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._report: VerificationReport | None = None

    def show(self, report: VerificationReport) -> None:
        self._report = report
        stats = self.query_one(StatsPanel)
        stats.show(report)
        spark = self.query_one(EquitySpark)
        spark.update_curve([p.equity for p in report.equity_curve] or sample_equity_curve())
        self.query_one(TrustBadge).set_grade(report.trust_grade)
        positions = demo_positions(report.trader)
        self.query_one(PositionTable).show_positions(positions)
        self.query_one("#dash-trader", Static).update(
            f"VERIFIED TRADER   {report.trader.short}     last verified "
            f"{(report.trader.verified_at.strftime('%Y-%m-%d %H:%M UTC') if report.trader.verified_at else '—')}"
        )

    def compose(self) -> ComposeResult:
        yield Static("📡  DASHBOARD", id="dash-title")
        yield TrustBadge(TrustGrade.REVIEW)
        yield Static(id="dash-trader")
        yield StatsPanel()
        yield EquitySpark()
        yield Static("[dim]TOP OPEN POSITIONS[/]")
        yield PositionTable()
