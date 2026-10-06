"""A :class:`DataTable` of traders on the audit watchlist."""

from __future__ import annotations

from textual.widgets import DataTable

from hl_copytrade_verifier.core.models import Trader


class TraderTable(DataTable):
    """Watchlist table: address, alias, last-verified, headline vs verified ROI."""

    def __init__(self) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True)
        self._rows: list[tuple[Trader, float, float]] = []

    def on_mount(self) -> None:  # type: ignore[override]
        self.add_columns("Alias", "Address", "Verified", "Headline ROI", "Verified ROI")
        self.refresh_rows(self._rows)

    def refresh_rows(self, rows: list[tuple[Trader, float, float]]) -> None:
        self._rows = rows
        self.clear()
        for trader, headline, verified in rows:
            verified_at = trader.verified_at.strftime("%Y-%m-%d %H:%M") if trader.verified_at else "—"
            self.add_row(
                trader.alias or "—",
                trader.short,
                verified_at,
                f"{headline * 100:+.1f}%",
                f"{verified * 100:+.1f}%",
                key=trader.address,
            )
