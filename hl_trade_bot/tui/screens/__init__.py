"""Tab panes for the verifier dashboard."""

from hl_copytrade_verifier.tui.screens.dashboard import DashboardPane
from hl_copytrade_verifier.tui.screens.log import LogPane
from hl_copytrade_verifier.tui.screens.positions import PositionsPane
from hl_copytrade_verifier.tui.screens.settings import SettingsPane
from hl_copytrade_verifier.tui.screens.traders import TradersPane
from hl_copytrade_verifier.tui.screens.verification import VerificationPane

__all__ = [
    "DashboardPane",
    "LogPane",
    "PositionsPane",
    "SettingsPane",
    "TradersPane",
    "VerificationPane",
]
