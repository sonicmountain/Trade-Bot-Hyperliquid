"""Positions pane — a focused view of the monitored trader's open positions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from hl_copytrade_verifier.core.mock_data import demo_positions
from hl_copytrade_verifier.core.models import Trader
from hl_copytrade_verifier.tui.widgets import PositionTable


class PositionsPane(Vertical):
    """Open positions for the focused trader (live-monitor preview)."""

    DEFAULT_CSS = """
    PositionsPane { padding: 1 2; }
    PositionsPane PositionTable { height: 1fr; margin-top: 1; }
    """

    def show(self, trader: Trader) -> None:
        self.query_one(PositionTable).show_positions(demo_positions(trader))
        self.query_one("#pos-meta", Static).update(
            f"Monitoring  {trader.short}   ({trader.alias or 'no alias'})"
        )

    def compose(self) -> ComposeResult:
        yield Static("📈  OPEN POSITIONS", classes="pane-title")
        yield Static(id="pos-meta")
        yield PositionTable()
