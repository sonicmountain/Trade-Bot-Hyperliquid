"""Pure verification & risk logic — no UI, no network.

This package is the reusable heart of the project. Importing it must not pull in
Textual or Rich.
"""

from hl_copytrade_verifier.core.models import (
    CheckResult,
    CheckVerdict,
    EquityPoint,
    Fill,
    FundingEvent,
    Position,
    Side,
    Trader,
    TrustGrade,
    VerificationReport,
)
from hl_copytrade_verifier.core.risk import CopySimulator, CopyTradePlan
from hl_copytrade_verifier.core.verifier import Verifier

# Convenience aliases documented in README / docs.
TraderAddress = str

__all__ = [
    "Verifier",
    "CopySimulator",
    "CopyTradePlan",
    "Fill",
    "FundingEvent",
    "Position",
    "Side",
    "Trader",
    "TraderAddress",
    "TrustGrade",
    "CheckResult",
    "CheckVerdict",
    "EquityPoint",
    "VerificationReport",
]
