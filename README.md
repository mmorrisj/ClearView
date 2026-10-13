# ClearView

Turns public local-government meetings into **searchable, verified, citable records**:
timestamped transcripts, summaries where every claim links to the exact moment in the
recording, and structured decisions/votes. Nothing is published until it passes automated
grounding checks and human review.

The differentiator is trust, not transcription. See the project brief for goals, milestones,
and ethics constraints (e.g. public commenters are labeled "Public commenter", not by name).

## Status

- [x] **M0 — Scaffold**: uv, ruff, mypy (strict), pytest, pre-commit, Postgres + pgvector,
      Alembic baseline, CI, `/health`
- [ ] M1 — Discovery for one body
- [ ] M2 — Fetch + transcribe
- [ ] M3 — Index + search API
- [ ] M4 — Gold set + eval harness
- [ ] M5 — Grounded summarization
- [ ] M6 — Verification gate
- [ ] M7 — Review + publish

## Development

Requirements: [uv](https://docs.astral.sh/uv/), Docker.

```bash
cp .env.example .env
docker compose up -d --wait        # Postgres 16 + pgvector on :5432
uv sync
uv run pre-commit install
uv run alembic upgrade head
uv run uvicorn lt.api.app:app --reload
curl localhost:8000/health
```

Checks (same as CI):

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest                      # DB tests are skipped unless TEST_DATABASE_URL is set
# DB tests reset the schema, so they only ever use the separate clearview_test database:
TEST_DATABASE_URL=postgresql+psycopg://clearview:clearview@localhost:5432/clearview_test uv run pytest
```

## Layout

```
src/lt/
  config.py      pydantic-settings (env / .env)
  db/            declarative base, engine/session
  api/           FastAPI app factory + routers
  discovery/ fetch/ transcribe/ index/ summarize/ verify/ pipeline/   (stages, M1+)
alembic/         migrations (URL comes from lt.config, never alembic.ini)
eval/            gold set + metrics (M4)
tests/
```
