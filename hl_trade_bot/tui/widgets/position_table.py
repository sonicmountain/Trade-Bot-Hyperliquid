"""A :class:`DataTable` of a trader's currently-open positions."""

from __future__ import annotations

from textual.widgets import DataTable

from hl_copytrade_verifier.core.models import Position


class PositionTable(DataTable):
    """Open positions: symbol, side, size, entry, mark, uPnL, leverage, liquidation."""

    def __init__(self) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:  # type: ignore[override]
        self.add_columns(
            "Symbol", "Side", "Size ($)", "Entry", "Mark", "uPnL ($)", "Lev.", "Liq."
        )

    def show_positions(self, positions: list[Position]) -> None:
        self.clear()
        for p in positions:
            side = "LONG" if p.side.value == "BUY" else "SHORT"
            upnl = float(p.upnl_usd)
            liq = f"{float(p.liquidation_price):,.1f}" if p.liquidation_price is not None else "—"
            self.add_row(
                p.symbol,
                side,
                f"{float(p.size_usd):,.2f}",
                f"{float(p.entry_price):,.4f}",
                f"{float(p.mark_price):,.4f}",
                f"{upnl:+,.2f}",
                f"{float(p.leverage):.1f}x",
                liq,
            )
