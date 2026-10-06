"""Sparkline widget wrapping Textual's :class:`Sparkline` for the equity curve."""

from __future__ import annotations

from textual.widgets import Sparkline


class EquitySpark(Sparkline):
    """A thin wrapper that exposes a semantic ``update_curve`` method.

    Relies on :class:`Sparkline`'s built-in reactive ``data`` attribute: assigning to
    ``self.data`` triggers the widget to re-render, so no manual ``watch_data`` override
    is needed.
    """

    def update_curve(self, points: list[float]) -> None:
        # Sparkline requires a non-empty series; fall back to a flat baseline.
        self.data = points if points else [1.0]
