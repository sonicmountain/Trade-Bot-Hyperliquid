"""Hyperliquid Copy-Trade Verifier.

A read-only terminal verifier & monitor for Hyperliquid copy-trading. It independently
re-derives trader ROI / PnL / drawdown from public fills *before* you copy-trade someone.

The package is organized in two layers:

* :mod:`hl_copytrade_verifier.core` — pure, framework-free verification logic.
* :mod:`hl_copytrade_verifier.tui`  — the Textual terminal user interface.

There is **no** order-placement code path anywhere in this package. The tool is strictly
read-only by design — see ``SECURITY.rst``.
"""

from __future__ import annotations

__version__ = "0.4.1"
__all__ = ["__version__"]
