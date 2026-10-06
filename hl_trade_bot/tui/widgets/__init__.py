"""Reusable TUI widgets for the verifier dashboard."""

from hl_copytrade_verifier.tui.widgets.equity_spark import EquitySpark
from hl_copytrade_verifier.tui.widgets.position_table import PositionTable
from hl_copytrade_verifier.tui.widgets.stats_panel import StatsPanel
from hl_copytrade_verifier.tui.widgets.trader_table import TraderTable
from hl_copytrade_verifier.tui.widgets.trust_badge import TrustBadge

__all__ = [
    "EquitySpark",
    "PositionTable",
    "StatsPanel",
    "TraderTable",
    "TrustBadge",
]
