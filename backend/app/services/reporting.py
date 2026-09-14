"""Building report snapshots and rendering them to HTML and PDF.

A report is frozen at submission: the findings are copied into the report row as they
read at that moment. Re-running an analysis afterwards cannot change what a supervisor
approved, and `content_sha256` lets anyone confirm a PDF matches the approved record.
"""

import hashlib
import html
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AnalysisRun, Claim, Evidence, Finding, FindingReview, User
from app.models.report import Report

TYPE_LABELS = {
    "possible_conflict": "Possible conflict",
    "unclear": "Unclear",
    "missing": "Missing detail",
    "match": "Matching information",
}


def build_snapshot(db: Session, report: Report) -> dict[str, Any]:
    """Copy every included finding, with its source wording and its review, into JSON."""
    items = []
    for item in sorted(report.items, key=lambda i: i.position):
        finding = db.get(Finding, item.finding_id)
        if finding is None:
            continue
        run = db.get(AnalysisRun, finding.run_id)
        claim_a = db.get(Claim, finding.claim_a_id) if finding.claim_a_id else None
        claim_b = db.get(Claim, finding.claim_b_id) if finding.claim_b_id else None
        review = (
            db.query(FindingReview)
            .filter(FindingReview.finding_id == finding.id)
            .order_by(FindingReview.created_at.desc())
            .first()
        )
        reviewer = db.get(User, review.reviewer_id) if review else None
        evidence = db.get(Evidence, run.evidence_id) if run and run.evidence_id else None

        items.append(
            {
                "finding_id": finding.id,
                "type": finding.finding_type.value,
                "field": finding.field.value,
                "score": round(finding.score, 3),
                "explanation": finding.explanation,
                "side_a": claim_a.text if claim_a else None,
                "side_b": claim_b.text if claim_b else finding.details.get("evidence_text"),
                "run_kind": run.kind.value if run else None,
                "analyzer": f"{run.analyzer_backend} {run.analyzer_version}" if run else None,
                "evidence": (
                    {"filename": evidence.original_filename, "sha256": evidence.sha256}
                    if evidence
                    else None
                ),
                "review": (
                    {
                        "decision": review.decision.value,
                        "comment": review.comment,
                        "reviewer": reviewer.full_name if reviewer else None,
                        "at": review.created_at.isoformat(),
                    }
                    if review
                    else None
                ),
                "investigator_note": item.note,
            }
        )

    counts: dict[str, int] = {}
    for item in items:
        counts[item["type"]] = counts.get(item["type"], 0) + 1

    return {
        "frozen_at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "items": items,
    }


def snapshot_digest(snapshot: dict[str, Any]) -> str:
    """Stable digest of the frozen content, so a PDF can be tied to its record."""
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _e(value: Any) -> str:
    return html.escape(str(value)) if value is not None else ""


def render_html(report: Report, case_reference: str, case_title: str, prepared_by: str) -> str:
    snapshot = report.snapshot or {}
    items = snapshot.get("items", [])
    counts = snapshot.get("counts", {})

    summary_rows = "".join(
        f"<tr><td>{_e(TYPE_LABELS.get(key, key))}</td><td class='num'>{value}</td></tr>"
        for key, value in sorted(counts.items())
    )

    blocks = []
    for index, item in enumerate(items, start=1):
        review = item.get("review")
        evidence = item.get("evidence")
        blocks.append(f"""
        <section class="finding {_e(item['type'])}">
          <h3>{index}. {_e(TYPE_LABELS.get(item['type'], item['type']))}
            <span class="field">{_e(item['field'])}</span></h3>
          <p class="explanation" dir="auto">{_e(item['explanation'])}</p>
          <table class="sides">
            <tr>
              <th>{'Statement' if item.get('run_kind') == 'evidence' else 'First interview'}</th>
              <td dir="auto">{_e(item['side_a']) or '<em>not mentioned</em>'}</td>
            </tr>
            <tr>
              <th>{'Evidence' if item.get('run_kind') == 'evidence' else 'Second interview'}</th>
              <td dir="auto">{_e(item['side_b']) or '<em>not mentioned</em>'}</td>
            </tr>
          </table>
          {f'<p class="meta">Evidence: {_e(evidence["filename"])} — SHA-256 {_e(evidence["sha256"])}</p>' if evidence else ''}
          {f'<p class="meta">Reviewed by {_e(review["reviewer"])}: <strong>{_e(review["decision"])}</strong>{(" — " + _e(review["comment"])) if review.get("comment") else ""}</p>' if review else '<p class="meta unreviewed">Not reviewed by an investigator.</p>'}
          {f'<p class="meta" dir="auto">Investigator note: {_e(item["investigator_note"])}</p>' if item.get('investigator_note') else ''}
          <p class="meta score">Engine similarity score {item['score']} — {_e(item.get('analyzer'))}</p>
        </section>""")

    decided = ""
    if report.decided_at:
        decided = (
            f"<p><strong>Supervisor decision:</strong> {_e(report.status.value)} on "
            f"{report.decided_at:%Y-%m-%d %H:%M} UTC"
            f"{(' — ' + _e(report.decision_note)) if report.decision_note else ''}</p>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{_e(report.title)}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm; @bottom-center {{ content: "Page " counter(page) " of " counter(pages); font-size: 9pt; color: #666; }} }}
  /* A printed record: it stays light regardless of the viewer's theme, so the HTML
     preview looks like the PDF instead of inheriting a dark background. */
  :root {{ color-scheme: light; }}
  html, body {{ background: #fff; }}
  body {{ font-family: "DejaVu Sans", "Noto Naskh Arabic", sans-serif; font-size: 10.5pt; color: #111; line-height: 1.5; margin: 0 auto; max-width: 190mm; padding: 8mm; }}
  h1 {{ font-size: 18pt; margin: 0 0 2mm; }}
  h2 {{ font-size: 12pt; margin: 8mm 0 3mm; border-bottom: 1px solid #ccc; padding-bottom: 1mm; }}
  h3 {{ font-size: 11pt; margin: 0 0 2mm; }}
  .subtitle {{ color: #555; margin: 0 0 6mm; }}
  .disclaimer {{ background: #fff8e1; border: 1px solid #e6c34a; padding: 3mm 4mm; margin: 5mm 0; font-size: 9.5pt; }}
  table {{ border-collapse: collapse; width: 100%; }}
  table.summary td {{ border: 1px solid #ddd; padding: 1.5mm 3mm; }}
  table.summary .num {{ text-align: right; width: 20mm; }}
  .finding {{ border: 1px solid #ddd; border-left-width: 3mm; padding: 3mm 4mm; margin: 0 0 4mm; page-break-inside: avoid; }}
  .finding.possible_conflict {{ border-left-color: #c62828; }}
  .finding.unclear {{ border-left-color: #ef6c00; }}
  .finding.missing {{ border-left-color: #757575; }}
  .finding.match {{ border-left-color: #2e7d32; }}
  .field {{ font-weight: normal; color: #666; font-size: 9pt; }}
  .explanation {{ margin: 0 0 2mm; }}
  table.sides th {{ text-align: left; width: 32mm; vertical-align: top; color: #555; font-weight: 600; padding: 1mm 0; }}
  table.sides td {{ padding: 1mm 0; }}
  .meta {{ font-size: 9pt; color: #555; margin: 1.5mm 0 0; }}
  .meta.unreviewed {{ color: #c62828; }}
  .meta.score {{ color: #777; }}
</style></head><body>
  <h1 dir="auto">{_e(report.title)}</h1>
  <p class="subtitle">Case <span dir="auto">{_e(case_reference)}</span> —
     <span dir="auto">{_e(case_title)}</span> · Report version {report.version}
     · Prepared by <span dir="auto">{_e(prepared_by)}</span></p>

  <div class="disclaimer">
    <strong>This report is decision support, not a determination.</strong>
    Truth Trace highlights differences between statements for an investigator to review.
    A difference between statements is not evidence of deception, and the similarity score
    shown with each finding is an internal engine score that has not been calibrated
    against ground-truth data — it is not a confidence percentage. Where evidence is
    referenced, a matching SHA-256 digest shows the stored file has not changed since
    upload; it does not establish that its contents are accurate.
  </div>

  {f'<h2>Summary</h2><p dir="auto">{_e(report.summary)}</p>' if report.summary else ''}

  <h2>Findings included</h2>
  <table class="summary">{summary_rows or '<tr><td>No findings included</td><td class="num">0</td></tr>'}</table>
  {decided}

  <h2>Detail</h2>
  {''.join(blocks) or '<p>No findings were included in this report.</p>'}

  <h2>Record</h2>
  <p class="meta">Content frozen at {_e(snapshot.get('frozen_at'))}.
     Content digest SHA-256 {_e(report.content_sha256)}.</p>
</body></html>"""


def render_pdf(html_text: str) -> bytes:
    """Render to PDF with WeasyPrint.

    Chosen over a headless browser because it needs no browser download, which keeps
    the whole system runnable offline.
    """
    from weasyprint import HTML  # imported lazily: only report export needs it

    return HTML(string=html_text).write_pdf()
