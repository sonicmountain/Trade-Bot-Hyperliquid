"""Traders pane — searchable leaderboard / audit watchlist."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from hl_copytrade_verifier.core.models import Trader
from hl_copytrade_verifier.tui.widgets import TraderTable


class TradersPane(Vertical):
    """The audit watchlist. ``r`` re-verifies the selected row."""

    DEFAULT_CSS = """
    TradersPane { padding: 1 2; }
    TradersPane TraderTable { height: 1fr; margin-top: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[Trader, float, float]] = []

    def show(self, rows: list[tuple[Trader, float, float]]) -> None:
        self._rows = rows
        self.query_one(TraderTable).refresh_rows(rows)

    def compose(self) -> ComposeResult:
        yield Static("🕵️  TRADERS — audit watchlist", classes="pane-title")
        yield Static(
            "[dim]Press [/][b]/[/][dim] to filter · [/][b]Enter[/][dim] to load · [/][b]r[/][dim] to re-verify[/]"
        )
        yield TraderTable()
