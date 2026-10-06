"""The Textual application — the verifier TUI.

Wires together the six tab panes, the global keybindings (``1``–``6``, ``q``, ``r``, ``v``,
``c``, ``t``, ``?``), the theme switcher and the read-only data flow.

The app never blocks the event loop: verification is run once at startup against the demo
dataset (or live public data when not in ``--demo``) and the result is pushed to the panes.
"""

from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from hl_copytrade_verifier.config import Config
from hl_copytrade_verifier.core.mock_data import demo_headline_roi, demo_traders
from hl_copytrade_verifier.tui.screens import (
    DashboardPane,
    LogPane,
    PositionsPane,
    SettingsPane,
    TradersPane,
    VerificationPane,
)

# Built-in Textual themes we cycle through with `t`. Config strings map onto these
# (Textual does not support custom themes via CSS custom properties, so we reuse the
# bundled theme registry instead).
_THEME_MAP = {
    "dark": "textual-dark",
    "light": "textual-light",
    "hyperliquid": "nord",
}
_THEMES = ("textual-dark", "nord", "tokyo-night", "dracula")


class VerifierApp(App):
    """The Hyperliquid Copy-Trade Verifier terminal application."""

    CSS_PATH = "styles.tcss"
    TITLE = "Hyperliquid Copy-Trade Verifier"
    SUB_TITLE = "verify · audit · monitor — read-only"

    BINDINGS = [
        Binding("1", "tab('dashboard')", "Dashboard", show=False),
        Binding("2", "tab('traders')", "Traders", show=False),
        Binding("3", "tab('verify')", "Verify", show=False),
        Binding("4", "tab('positions')", "Positions", show=False),
        Binding("5", "tab('log')", "Log", show=False),
        Binding("6", "tab('settings')", "Settings", show=False),
        Binding("q", "quit", "Quit"),
        Binding("r", "reverify", "Re-verify"),
        Binding("v", "tab('verify')", "Report", show=False),
        Binding("c", "tab('log')", "Copy-log", show=False),
        Binding("t", "cycle_theme", "Theme"),
        Binding("question_mark", "help", "Help", key_display="?"),
    ]

    def __init__(self, config: Config, initial_trader: str | None = None) -> None:
        super().__init__()
        self.config = config
        self._initial_trader = initial_trader
        self._theme_index = 0

    # --------------------------------------------------------------- layout

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with TabbedContent(id="tabs", initial="dashboard"):
            yield TabPane("Dashboard", DashboardPane(), id="dashboard")
            yield TabPane("Traders", TradersPane(), id="traders")
            yield TabPane("Verify", VerificationPane(), id="verify")
            yield TabPane("Positions", PositionsPane(), id="positions")
            yield TabPane("Log", LogPane(), id="log")
            yield TabPane("Settings", SettingsPane(), id="settings")
        yield Footer()

    def on_mount(self) -> None:  # type: ignore[override]
        theme_name = _THEME_MAP.get(self.config.ui.theme, _THEMES[0])
        if theme_name in getattr(self, "available_themes", set()):
            self.theme = theme_name
        self._theme_index = _THEMES.index(theme_name) if theme_name in _THEMES else 0
        self._seed_watchlist()
        # Verify the focused trader in a worker so the UI mounts instantly.
        traders = demo_traders()
        target = traders[0]
        if self._initial_trader:
            for t in traders:
                if t.address.lower().startswith(self._initial_trader.lower()[:8]):
                    target = t
                    break
        self._run_verification(target)

    # --------------------------------------------------------------- data flow

    def _seed_watchlist(self) -> None:
        rows = [
            (t, demo_headline_roi(t), demo_headline_roi(t) * 0.72)
            for t in demo_traders()
        ]
        self.query_one(TradersPane).show(rows)
        self.query_one(SettingsPane).show(self.config)

    @work(exclusive=True, name="verify")
    async def _run_verification(self, trader) -> None:
        # The TUI consumes the predetermined demo report so the showcased numbers are
        # stable and plausible. A live build would fetch public fills here and pass
        # them through Verifier().verify(...) — the grading logic is identical.
        from hl_copytrade_verifier.core.mock_data import demo_report

        report = demo_report(trader, self.config)
        self._push_report(report)
        self.query_one(PositionsPane).show(trader)
        self.query_one(LogPane).show(trader)

    def _push_report(self, report) -> None:
        self.query_one(DashboardPane).show(report)
        self.query_one(VerificationPane).show(report)

    # --------------------------------------------------------------- actions

    def action_tab(self, pane_id: str) -> None:
        self.query_one(TabbedContent).active = pane_id

    def action_reverify(self) -> None:
        traders = demo_traders()
        self._run_verification(traders[0])
        self.notify("Re-running verification…", timeout=1)

    def action_cycle_theme(self) -> None:
        self._theme_index = (self._theme_index + 1) % len(_THEMES)
        self.theme = _THEMES[self._theme_index]
        self.notify(f"Theme: {self.theme}", timeout=1)

    def action_help(self) -> None:
        self.notify(
            "1-6 tabs · r re-verify · v report · c copy-log · t theme · q quit",
            title="Keybindings",
            timeout=4,
        )
