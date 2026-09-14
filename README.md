# Truth Trace

A decision-support tool for investigators. It compares a subject's statements from
different interview sessions and surfaces matching information, possible conflicts,
missing details and unclear points — each shown next to the exact words it came from.

**Truth Trace does not decide whether anyone is lying or guilty.** It highlights
differences for a human to review. A difference between statements is not proof of
deception, and the engine's similarity score is an internal number, not a calibrated
confidence percentage.

## Status

Phases 1–4 of the plan are implemented: project foundation, database and access
control, the comparison engine, and the web interface. Evidence upload with SHA-256
integrity (phase 5), supervisor approval and PDF reporting (phase 6) are not built yet.

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

## Layout

```
backend/
  app/analysis/    the comparison engine (segment -> extract -> judge)
  app/api/routes/  auth, cases, interviews, analysis
  app/models/      SQLAlchemy tables
  alembic/         migrations
  tests/           engine and extraction tests
frontend/
  src/pages/       login, case list, case detail with results
  src/i18n/        English and Arabic strings
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

## Before this is used on real statements

- The similarity score is **not** calibrated. Do not present it as a confidence
  percentage until it has been measured against labelled statements.
- Attribute extraction is rule-based and tuned for English. Place aliases and person
  detection in `backend/app/analysis/extract.py` need widening from real case data.
- Run it over a labelled evaluation set and measure how often it flags a conflict that
  is not one, and how often it misses a real one, before drawing conclusions from it.
