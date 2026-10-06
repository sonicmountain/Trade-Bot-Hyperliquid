"""Settings pane — network, verification window, trust rubric, theme."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from hl_copytrade_verifier.config import Config


class SettingsPane(VerticalScroll):
    """Read-only rendering of the active config with hints on how to edit it."""

    DEFAULT_CSS = """
    SettingsPane { padding: 1 2; }
    SettingsPane .cfg-block { margin: 1 0; }
    SettingsPane .cfg-key   { color: $accent; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._config: Config | None = None

    def show(self, config: Config) -> None:
        self._config = config
        self.query_one("#cfg-net", Static).update(self._render_net(config))
        self.query_one("#cfg-verify", Static).update(self._render_verify(config))
        self.query_one("#cfg-rubric", Static).update(self._render_rubric(config))
        self.query_one("#cfg-copy", Static).update(self._render_copy(config))
        self.query_one("#cfg-ui", Static).update(self._render_ui(config))

    def compose(self) -> ComposeResult:
        yield Static("⚙️  SETTINGS", classes="pane-title")
        yield Static(
            "[dim]Edit [/][b]~/.hl-verify/config.toml[/][dim] and press [/][b]R[/][dim] to hot-reload.[/]"
        )
        yield Static(id="cfg-net", classes="cfg-block")
        yield Static(id="cfg-verify", classes="cfg-block")
        yield Static(id="cfg-rubric", classes="cfg-block")
        yield Static(id="cfg-copy", classes="cfg-block")
        yield Static(id="cfg-ui", classes="cfg-block")

    @staticmethod
    def _kv(key: str, value: object) -> str:
        return f"  [dim]{key}[/] = {value}"

    def _render_net(self, c: Config) -> str:
        n = c.network
        lines = ["[bold cyan]network[/]", self._kv("chain", n.chain), self._kv("api_url", n.api_url),
                 self._kv("timeout_seconds", n.timeout_seconds), self._kv("max_rps", n.max_rps)]
        return "\n".join(lines)

    def _render_verify(self, c: Config) -> str:
        v = c.verification
        lines = ["[bold cyan]verification[/]", self._kv("window_days", v.window_days),
                 self._kv("min_trades", v.min_trades), self._kv("recompute_fees", v.recompute_fees),
                 self._kv("significance_p", v.significance_p)]
        return "\n".join(lines)

    def _render_rubric(self, c: Config) -> str:
        r = c.trust_rubric
        lines = ["[bold cyan]trust_rubric[/]", self._kv("max_drawdown", r.max_drawdown),
                 self._kv("min_profit_factor", r.min_profit_factor),
                 self._kv("max_martingale", r.max_martingale),
                 self._kv("max_outlier_dep", r.max_outlier_dep),
                 self._kv("min_sharpe", r.min_sharpe)]
        return "\n".join(lines)

    def _render_copy(self, c: Config) -> str:
        ct = c.copytrade
        lines = ["[bold cyan]copytrade[/]", self._kv("size_mode", ct.size_mode),
                 self._kv("fixed_fraction", ct.fixed_fraction),
                 self._kv("leverage_cap", ct.leverage_cap),
                 self._kv("stop_loss_pct", ct.stop_loss_pct)]
        return "\n".join(lines)

    def _render_ui(self, c: Config) -> str:
        ui = c.ui
        return "\n".join(["[bold cyan]ui[/]", self._kv("theme", ui.theme),
                          self._kv("refresh_seconds", ui.refresh_seconds)])
