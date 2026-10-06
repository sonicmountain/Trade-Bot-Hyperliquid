"""A colored badge widget that renders a :class:`TrustGrade`."""

from __future__ import annotations

from textual.widgets import Static

from hl_copytrade_verifier.core.models import TrustGrade

# Rich markup colors keyed by grade (NOT Textual CSS classes).
_GRADE_COLOR = {
    TrustGrade.TRUSTED: "bold green",
    TrustGrade.REVIEW: "bold yellow",
    TrustGrade.REJECT: "bold red",
}


class TrustBadge(Static):
    """Renders ``🟢 TRUSTED`` / ``🟠 REVIEW`` / ``🔴 REJECT`` with themed coloring.

    Uses :meth:`Static.update` rather than overriding ``render`` so Textual's height
    calculation keeps working (overriding ``render`` to return a string breaks
    ``get_content_height`` in Textual 8.x).
    """

    def __init__(self, grade: TrustGrade) -> None:
        super().__init__()
        self.grade = grade
        self._refresh_text()

    def _refresh_text(self) -> None:
        color = _GRADE_COLOR[self.grade]
        self.update(f"[{color}]{self.grade.icon}  {self.grade.value}[/]")

    def set_grade(self, grade: TrustGrade) -> None:
        self.grade = grade
        self._refresh_text()
