"""Log pane — the local, append-only copy-trade paper-trail."""

from __future__ import annotations

from decimal import Decimal

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from hl_copytrade_verifier.core.models import Fill, Side, Trader
from hl_copytrade_verifier.core.mock_data import demo_fills, demo_now
from hl_copytrade_verifier.core.risk import CopySimulator
from hl_copytrade_verifier.config import CopyTradeConfig


class LogPane(Vertical):
    """Renders the JSONL paper-trail as a table (no execution, ever)."""

    DEFAULT_CSS = """
    LogPane { padding: 1 2; }
    LogPane DataTable { height: 1fr; margin-top: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._sim = CopySimulator(CopyTradeConfig())

    def show(self, trader: Trader) -> None:
        table = self.query_one(DataTable)
        table.clear()
        fills = demo_fills(trader, trades=24)
        for f in fills:
            plan = self._sim.plan(f, source_leverage=5.0)
            table.add_row(
                plan.time.strftime("%m-%d %H:%M"),
                plan.symbol,
                "BUY" if plan.side is Side.BUY else "SELL",
                f"{float(plan.source_size_usd):,.0f}",
                f"{float(plan.mirrored_size_usd):,.0f}",
                f"{plan.leverage_used:.1f}x",
                "capped" if plan.leverage_capped else "—",
                f"{float(plan.stop_mark):,.2f}" if plan.stop_mark is not None else "—",
            )
        self.query_one("#log-meta", Static).update(
            f"Paper-trail · {len(fills)} mirrored fills · last {demo_now():%Y-%m-%d %H:%M UTC} · local only"
        )

    def compose(self) -> ComposeResult:
        yield Static("📋  COPY-TRADE LOG (paper trail)", classes="pane-title")
        yield Static(
            "[dim]Append-only JSONL · nothing is sent anywhere · sizing from [/][b]copytrade.size_mode[/]",
            id="log-meta",
        )
        table = DataTable(cursor_type="row", zebra_stripes=True)
        table.add_columns("Time", "Symbol", "Side", "Source $", "Mirrored $", "Lev.", "Cap", "Stop")
        yield table
