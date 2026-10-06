"""Verification pane — the detailed, per-check rubric report."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Static

from hl_copytrade_verifier.core.models import VerificationReport
from hl_copytrade_verifier.tui.widgets import TrustBadge

_VERDICT_ICON = {"PASS": "✅", "REVIEW": "🟠", "REJECT": "🔴"}


class VerificationPane(VerticalScroll):
    """Renders every check, threshold, value and verdict for the focused trader."""

    DEFAULT_CSS = """
    VerificationPane { padding: 1 2; }
    VerificationPane DataTable { margin-top: 1; height: auto; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._report: VerificationReport | None = None

    def show(self, report: VerificationReport) -> None:
        self._report = report
        self.query_one(TrustBadge).set_grade(report.trust_grade)
        self.query_one("#verify-meta", Static).update(
            f"Trader {report.trader.short}    window {report.window[0]:%Y-%m-%d} → {report.window[1]:%Y-%m-%d}    "
            f"trades {report.trades}"
        )
        table = self.query_one(DataTable)
        table.clear()
        for c in report.checks:
            thr = f"{c.threshold:+.2f}" if c.threshold is not None else "—"
            table.add_row(
                _VERDICT_ICON[c.verdict.value],
                c.label,
                f"{c.value:+.4f}",
                thr,
                c.verdict.value,
                c.detail,
            )

    def compose(self) -> ComposeResult:
        from hl_copytrade_verifier.core.models import TrustGrade

        yield Static("🧮  VERIFICATION REPORT", classes="pane-title")
        yield TrustBadge(TrustGrade.REVIEW)
        yield Static(id="verify-meta")
        table = DataTable(cursor_type="row", zebra_stripes=True)
        table.add_columns(" ", "Check", "Value", "Threshold", "Verdict", "Detail")
        yield table
