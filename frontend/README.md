# PE-Analyst frontend

A React + Vite + TypeScript frontend for the PE-Analyst backend: upload deal
documents, run the full agentic underwriting workflow, and review the
Investment Committee's simulated debate and final recommendation.

## Stack

- React 19 + Vite + TypeScript, styled with Tailwind CSS v4
- React Router for navigation
- Recharts for the scenario IRR/MOIC charts
- A thin axios wrapper (`src/lib/api.ts`) that attaches `Authorization: Bearer
  <token>` to every request and redirects to `/login` on a 401

## Setup

```bash
cd pe-analyst/frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` (pinned in `vite.config.ts` —
this is required, since the backend's CORS config only allows
`http://localhost:5173` and `http://127.0.0.1:5173`).

## Backend

**The backend must already be running on `http://localhost:8000`** before you
use the app (the API base URL is hardcoded in `src/lib/api.ts`). From the
`pe-analyst` directory, with the repo's venv:

```bash
../.venv/Scripts/python.exe -m uvicorn pe_analyst.main:app --port 8000 --app-dir src
```

This requires a reachable Postgres database matching `DATABASE_URL` in
`pe-analyst/.env` (the users/audit-log tables; `alembic upgrade head` creates
them). If you don't have that Postgres instance running, you can point the
backend at a throwaway SQLite file instead for local-only testing — the ORM
models the auth flow depends on (`users`, `audit_log`) work fine under SQLite,
only the pgvector-typed `vector_chunks` table doesn't, and that's only needed
when `VECTOR_STORE_PROVIDER=pgvector` (the default is `local`, a file-backed
store, so this isn't required for basic use):

```bash
DATABASE_URL="sqlite:///./dev.db" ../.venv/Scripts/python.exe -m uvicorn pe_analyst.main:app --port 8000 --app-dir src
```

(You'll need to create the `users`/`audit_log` tables on that SQLite file once
— `Base.metadata.create_all(engine, tables=[...])` for just those two tables,
the same way `tests/conftest.py`'s `db_session` fixture does it — since Alembic's
migration targets Postgres-specific types.)

## Build

```bash
npm run build
```

Runs `tsc -b` (type-check) then `vite build`. Must succeed with zero
TypeScript errors.

## Pages

- `/login`, `/register` — auth
- `/documents` — document library: upload a PDF, see extracted sections, risk
  factors, notes, and industry evidence with page/confidence provenance; ask
  questions about a document via the RAG endpoint
- `/analysis/new` — full deal-analysis form (financials, valuation/DCF/LBO
  assumptions, optional risk inputs, optional derive-from-document for
  industry + due-diligence evidence)
- `/analysis/result` — the deal report: pipeline stage trace, valuation +
  scenario charts, risk table, red-flag table, and the full IC debate
  (committee scorecard, Deal Partner / Risk Officer / Operating Partner
  opinions, Chairperson's ruling, and any dissent)
- `/sensitivity` — standalone LBO IRR/MOIC sensitivity grid, rendered as a
  heatmap

Deal reports are **not persisted anywhere** (the backend has no endpoint to
fetch a past run) — `/analysis/result` only renders a report handed to it via
in-memory navigation state from `/analysis/new`. Refreshing that page, or
visiting it directly, shows an empty state with a link back to start a new
analysis.
