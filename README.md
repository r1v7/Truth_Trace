# Truth Trace

A decision-support tool for investigators. It compares a subject's statements from
different interview sessions and surfaces matching information, possible conflicts,
missing details and unclear points — each shown next to the exact words it came from.

**Truth Trace does not decide whether anyone is lying or guilty.** It highlights
differences for a human to review. A difference between statements is not proof of
deception, and the engine's similarity score is an internal number, not a calibrated
confidence percentage.

## Status

All planned phases are implemented: project foundation, database and access control, the
comparison engine, the web interface, digital evidence with SHA-256 integrity, supervisor
approval with PDF reporting, and a labelled evaluation harness.

Not built: image and audio analysis (those files are stored and hashed, but not compared),
and any accuracy measurement on statements the engine's authors have not seen — see
[docs/evaluation.md](docs/evaluation.md).

## Running it

Requires Docker. The backend runs in a container (Python 3.11); the frontend runs on
Node 20+.

```bash
cp .env.example .env
docker compose up -d
```

The API is then on http://127.0.0.1:8000 (docs at `/docs`), and migrations run
automatically on start. On a fresh database, one admin account is created from
`FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` — change that password immediately.

```bash
npm install --prefix frontend
npm run dev --prefix frontend
```

The interface is then on http://localhost:5173.

## Public demo

The interface deploys to GitHub Pages; the API and its database run on Render. GitHub
Pages is static hosting, so the engine cannot run there — the Pages site is only the
interface, and it calls the deployed API.

See [docs/deployment.md](docs/deployment.md) for the setup and, more importantly, for
what the free tiers cost: the API sleeps after 15 minutes idle (the interface shows a
"waking the server" banner), the free database is deleted 30 days after it is created,
uploaded evidence does not survive a restart, and the demo credentials are public by
definition. Put nothing real in the demo database.

## Layout

```
backend/
  app/analysis/    the comparison engine (segment -> extract -> judge)
  app/api/routes/  auth, cases, interviews, analysis, evidence, reports
  app/services/    evidence storage and hashing, report rendering
  app/models/      SQLAlchemy tables
  evaluation/      labelled dataset and the measurement runner
  app/seed_demo.py demo case seeded with real engine output
  alembic/         migrations
  tests/           engine, extraction, storage and reporting tests
frontend/
  src/pages/       login, case list, case detail with results
  src/components/  findings, evidence panel, reports panel
  src/i18n/        English and Arabic strings
  src/fonts/       self-hosted typefaces (scripts/fetch-fonts.py regenerates)
```

## How the comparison works

Three stages, each auditable on its own:

1. **Link** — claims from the two interviews are paired when either their wording is
   similar or their extracted attributes overlap. Wording alone misses paraphrases
   ("the mall" / "the shopping centre"), so shared places, people, actions and agreeing
   times act as a second, independent signal. A *disagreeing* time never blocks a link —
   that contradiction is exactly what stage 3 exists to report.
2. **Extract** — time, location, people, action and negation are pulled from each claim
   by explicit rules. Times are normalised to minutes from midnight, so "8:00 PM",
   "20:00" and "eight in the evening" all compare equal.
3. **Judge** — each pair becomes `match`, `possible_conflict`, `missing` or `unclear`,
   with a readable reason naming the field that differs. Unpaired claims are reported as
   missing on the side where they do not appear.

Negation is checked before wording similarity on purpose: "I was at home" and "I was not
at home" are nearly identical as text and opposite in meaning.

### Similarity backends

| `ANALYZER_BACKEND` | Behaviour |
| --- | --- |
| `lexical` (default) | Token overlap. No model download, fully offline, deterministic. |
| `embedding` | A local sentence-transformers model, cached in the `models_cache` volume. |

To use embeddings, install the optional dependencies
(`pip install -r backend/requirements-ml.txt`, or add them to the Dockerfile) and set
`ANALYZER_BACKEND=embedding`. Everything else is unchanged — the engine only asks the
backend for a similarity matrix. Every analysis run records which backend and version
produced it, so results stay traceable after a model change.

## Digital evidence

A file is streamed to per-case storage while being hashed, so the recorded SHA-256 digest
describes the bytes that were actually stored. `GET /api/evidence/{id}/integrity`
recomputes the digest and compares it with the recorded one.

**What a matching digest means:** the stored file has not changed since it was uploaded.
**What it does not mean:** that its contents are accurate, or that the file was authentic
when it arrived. The interface and the report both say so.

If a file no longer matches its digest, comparing it against a statement is refused with
409 rather than producing a result that would look exactly like a sound one. Storage paths
are generated rather than taken from the upload, so a filename cannot escape the storage
root; executable types are refused outright.

Text evidence (call logs, message logs, transcripts) is segmented and compared through the
same engine and review flow as statements. Images and audio are stored and hashed but not
analysed, and the API says so instead of failing vaguely.

## Reports and supervisor approval

A report collects chosen findings, and **freezes them at submission**: the findings are
copied into the report with their source wording, their reviews and any evidence digests.
Re-running an analysis afterwards cannot change what a supervisor approved. The frozen
content is hashed into `content_sha256`, which the PDF carries in a response header.

The workflow is `draft → submitted → approved | returned`. Guards, all enforced by the API:

- A supervisor or admin decides — not an investigator.
- Nobody approves their own report; the second pair of eyes is the point of the step.
- Returning a report requires a written reason.
- An approved or submitted report cannot be edited — create a new version instead.
- A draft cannot be exported as PDF, so no draft circulates as though it were reviewed.

PDFs are rendered with WeasyPrint rather than a headless browser, so nothing needs to be
downloaded at build time and the system stays runnable offline. Every report carries the
disclaimer that it is decision support, not a determination, and any finding that no
investigator reviewed is marked as unreviewed rather than presented as settled.

## Access control

Global roles are `investigator`, `supervisor` and `admin`. Case access is separate:
a user reaches a case only through a `case_members` row (`owner`, `collaborator` or
`reviewer`); reviewers are read-only; admins see everything. A case a user cannot access
returns 404 rather than 403, so the existence of a case is not disclosed.

Every state-changing action writes to `audit_log` with actor, entity, case and IP.

## Tests

```bash
docker compose run --rm --no-deps --entrypoint sh api -c "pytest -q"
```

The engine tests encode the scenarios from the project brief directly: paraphrases must
not be flagged, 8:00 PM vs 10:30 PM must be, 8:00 vs 8:10 must not, and negation must beat
wording similarity.

Accuracy is measured separately against a labelled set:

```bash
docker compose run --rm --no-deps --entrypoint sh api -c "python -m evaluation.run_eval --errors"
```

Read [docs/evaluation.md](docs/evaluation.md) before quoting the number it prints — it is a
regression ratchet, not an accuracy estimate for real statements.

## Before this is used on real statements

- The similarity score is **not** calibrated. Do not present it as a confidence
  percentage until it has been measured against labelled statements.
- Attribute extraction is rule-based and tuned for English. Place aliases and person
  detection in `backend/app/analysis/extract.py` need widening from real case data.
- Run it over a labelled evaluation set and measure how often it flags a conflict that
  is not one, and how often it misses a real one, before drawing conclusions from it.
