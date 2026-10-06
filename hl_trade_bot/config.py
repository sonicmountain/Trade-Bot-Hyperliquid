"""Configuration loader.

Configuration is stored as TOML under the user config directory (``~/.hl-verify/config.toml``).
On first run a default config is written there. All values have sensible defaults so the tool
works out of the box.

The :class:`Config` object is the single source of truth that every other module reads from.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib  # noqa: F401
    _LOAD = tomllib.loads
else:  # pragma: no cover - exercised only on 3.10
    import tomli as _tomli  # type: ignore[import-not-found]
    _LOAD = _tomli.loads


def default_config_path() -> Path:
    """Return the platform-appropriate default config directory."""
    # Local import keeps `platformdirs` out of the import path for non-config callers.
    from platformdirs import user_config_dir  # type: ignore[import-not-found]

    return Path(user_config_dir("hl-verify", appauthor=False)) / "config.toml"


DEFAULT_CONFIG_TOML = """\
[network]
chain            = "mainnet"
api_url          = "https://api.hyperliquid.xyz"
ws_url           = "wss://api.hyperliquid.xyz/ws"
timeout_seconds  = 10
max_rps          = 5

[verification]
window_days      = 90
min_trades       = 100
recompute_fees   = true
funding_cadence  = "hourly"
significance_p   = 0.05

[trust_rubric]
max_drawdown      = -0.35
min_profit_factor = 1.6
max_martingale    = 0.40
max_outlier_dep   = 0.30
min_sharpe        = 1.0

[copytrade]
size_mode        = "fixed_fraction"
fixed_fraction   = 0.02
fixed_notional   = 1000
leverage_cap     = 5.0
stop_loss_pct    = 0.08

[ui]
theme            = "dark"
refresh_seconds  = 5
sparkline_points = 80
"""


@dataclass(frozen=True)
class NetworkConfig:
    chain: str = "mainnet"
    api_url: str = "https://api.hyperliquid.xyz"
    ws_url: str = "wss://api.hyperliquid.xyz/ws"
    timeout_seconds: int = 10
    max_rps: int = 5


@dataclass(frozen=True)
class VerificationConfig:
    window_days: int = 90
    min_trades: int = 100
    recompute_fees: bool = True
    funding_cadence: str = "hourly"
    significance_p: float = 0.05


@dataclass(frozen=True)
class TrustRubric:
    """Thresholds used to grade a trader. ``None`` disables a check."""

    max_drawdown: float | None = -0.35
    min_profit_factor: float | None = 1.6
    max_martingale: float | None = 0.40
    max_outlier_dep: float | None = 0.30
    min_sharpe: float | None = 1.0


@dataclass(frozen=True)
class CopyTradeConfig:
    """Sizing *hints* for the paper-trail log. The verifier never executes."""

    size_mode: str = "fixed_fraction"
    fixed_fraction: float = 0.02
    fixed_notional: float = 1000.0
    leverage_cap: float = 5.0
    stop_loss_pct: float = 0.08


@dataclass(frozen=True)
class UIConfig:
    theme: str = "dark"
    refresh_seconds: int = 5
    sparkline_points: int = 80


@dataclass(frozen=True)
class Config:
    """Top-level configuration object."""

    network: NetworkConfig = field(default_factory=NetworkConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    trust_rubric: TrustRubric = field(default_factory=TrustRubric)
    copytrade: CopyTradeConfig = field(default_factory=CopyTradeConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    demo: bool = False
    no_color: bool = False

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        demo: bool = False,
        no_color: bool = False,
        theme_override: str | None = None,
    ) -> Config:
        """Load config from ``path``, writing the default file on first run."""
        path = Path(path)
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
            except OSError:
                # Read-only home / sandbox: fall back to defaults in memory.
                pass

        raw = _LOAD(path.read_text(encoding="utf-8")) if path.exists() else {}

        network = NetworkConfig(**raw.get("network", {}))
        verification = VerificationConfig(**raw.get("verification", {}))
        rubric = TrustRubric(**raw.get("trust_rubric", {}))
        copytrade = CopyTradeConfig(**raw.get("copytrade", {}))
        ui = UIConfig(**raw.get("ui", {}))

        if theme_override:
            ui = replace(ui, theme=theme_override)

        return cls(
            network=network,
            verification=verification,
            trust_rubric=rubric,
            copytrade=copytrade,
            ui=ui,
            demo=demo,
            no_color=no_color,
        )
