"""Tests for report freezing and rendering.

These exercise the pure functions; the workflow guards (who may approve, what may be
edited) live in the routes and are covered by the API behaviour documented in the README.
"""

from datetime import UTC, datetime

from app.models.enums import ReportStatus
from app.models.report import Report
from app.services import reporting


def make_report(**overrides) -> Report:
    report = Report(
        id=1,
        case_id=1,
        version=1,
        title="Statement comparison",
        summary=None,
        status=ReportStatus.submitted,
        prepared_by_id=1,
        snapshot={
            "frozen_at": "2026-09-14T20:00:00+00:00",
            "counts": {"possible_conflict": 1},
            "items": [
                {
                    "finding_id": 7,
                    "type": "possible_conflict",
                    "field": "time",
                    "score": 1.0,
                    "explanation": "Time differs: 20:00 vs 22:30.",
                    "side_a": "I arrived at 8:00 PM.",
                    "side_b": "I arrived at 10:30 PM.",
                    "run_kind": "interview_pair",
                    "analyzer": "lexical 0.1.0+1.0",
                    "evidence": None,
                    "review": None,
                    "investigator_note": None,
                }
            ],
        },
        content_sha256="a" * 64,
    )
    for key, value in overrides.items():
        setattr(report, key, value)
    return report


def test_digest_is_stable_across_key_order():
    first = {"counts": {"match": 1}, "items": [], "frozen_at": "x"}
    second = {"frozen_at": "x", "items": [], "counts": {"match": 1}}
    assert reporting.snapshot_digest(first) == reporting.snapshot_digest(second)


def test_digest_changes_when_content_changes():
    snapshot = {"counts": {}, "items": [{"explanation": "Time differs"}]}
    altered = {"counts": {}, "items": [{"explanation": "Times agree"}]}
    assert reporting.snapshot_digest(snapshot) != reporting.snapshot_digest(altered)


def test_report_always_carries_its_limits():
    html = reporting.render_html(make_report(), "TT-1", "Case", "Investigator")
    assert "not a determination" in html
    assert "not a confidence percentage" in html
    # The evidence caveat must survive even when no evidence is cited.
    assert "does not establish that its contents are accurate" in html


def test_unreviewed_findings_are_marked_as_such():
    """A report must not let an unreviewed engine result look like a reviewed one."""
    html = reporting.render_html(make_report(), "TT-1", "Case", "Investigator")
    assert "Not reviewed by an investigator" in html


def test_reviewed_findings_name_their_reviewer():
    report = make_report()
    report.snapshot["items"][0]["review"] = {
        "decision": "accepted",
        "comment": "Confirmed with the duty log.",
        "reviewer": "Nora Supervisor",
        "at": "2026-09-14T20:10:00+00:00",
    }
    html = reporting.render_html(report, "TT-1", "Case", "Investigator")
    assert "Nora Supervisor" in html and "accepted" in html
    assert "Not reviewed by an investigator" not in html


def test_user_text_is_escaped():
    report = make_report(title="<script>alert('x')</script>")
    html = reporting.render_html(report, "TT-1", "Case", "Investigator")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_supervisor_decision_is_shown_when_decided():
    report = make_report(
        status=ReportStatus.approved,
        decided_at=datetime(2026, 9, 14, 20, 17, tzinfo=UTC),
        decision_note="Warrants a follow-up interview.",
    )
    html = reporting.render_html(report, "TT-1", "Case", "Investigator")
    assert "Supervisor decision" in html and "follow-up interview" in html


def test_report_renders_light_regardless_of_viewer_theme():
    """The HTML preview is a printed record, not a themed page."""
    html = reporting.render_html(make_report(), "TT-1", "Case", "Investigator")
    assert "color-scheme: light" in html
    assert "background: #fff" in html


def test_empty_report_renders_without_crashing():
    report = make_report(snapshot={"frozen_at": "x", "counts": {}, "items": []})
    html = reporting.render_html(report, "TT-1", "Case", "Investigator")
    assert "No findings were included" in html
