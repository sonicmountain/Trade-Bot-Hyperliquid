"""Copy-trade sizing simulator.

Produces the *paper-trail* entries that the Log tab renders. **Nothing here executes.**
The simulator only decides, given a verified trader's fill, what size you *would have*
mirrored under your configured risk policy — and writes that decision to a local log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from hl_copytrade_verifier.config import CopyTradeConfig
from hl_copytrade_verifier.core.models import Fill, Side


@dataclass(frozen=True)
class CopyTradePlan:
    """A single paper-trail entry: the decision to mirror one verified fill."""

    time: datetime
    symbol: str
    side: Side
    source_size_usd: Decimal       # what the verified trader did
    mirrored_size_usd: Decimal     # what your policy would have done
    leverage_used: float
    leverage_capped: bool          # True if your cap reduced the size
    stop_mark: Decimal | None      # mark at which the log entry is flagged "stopped"
    note: str = ""


class CopySimulator:
    """Stateless sizer. The policy lives in :class:`CopyTradeConfig`."""

    def __init__(self, policy: CopyTradeConfig) -> None:
        self.policy = policy

    def plan(self, fill: Fill, *, source_leverage: float = 1.0) -> CopyTradePlan:
        notional = float(fill.price) * float(fill.size)
        mirrored = self._size(notional)
        leverage = min(source_leverage, self.policy.leverage_cap)
        capped = source_leverage > self.policy.leverage_cap

        stop_mark: Decimal | None
        if self.policy.stop_loss_pct > 0:
            move = Decimal(str(self.policy.stop_loss_pct))
            stop_mark = (
                fill.price * (Decimal(1) + move)
                if fill.side is Side.BUY
                else fill.price * (Decimal(1) - move)
            )
        else:
            stop_mark = None

        return CopyTradePlan(
            time=fill.time,
            symbol=fill.symbol,
            side=fill.side,
            source_size_usd=Decimal(str(notional)),
            mirrored_size_usd=Decimal(str(mirrored)),
            leverage_used=leverage,
            leverage_capped=capped,
            stop_mark=stop_mark,
            note=self.policy.size_mode,
        )

    def _size(self, source_notional: float) -> float:
        mode = self.policy.size_mode
        if mode == "fixed_fraction":
            return source_notional * self.policy.fixed_fraction
        if mode == "fixed_notional":
            return self.policy.fixed_notional
        if mode == "mirror":
            return source_notional
        # Unknown mode: be conservative.
        return min(source_notional * self.policy.fixed_fraction, self.policy.fixed_notional)
