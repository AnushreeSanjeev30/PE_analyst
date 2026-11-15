# PE-Analyst
PE-Analyst is an evidence-grounded agentic AI system for private equity investment analysis and decision support.

The platform is designed to reproduce major stages of the private equity investment workflow:

1. Company document ingestion.
2. Financial statement extraction.
3. Deterministic financial analysis.
4. Industry and competitor research.
5. Due diligence and red-flag detection.
6. Leveraged Buyout (LBO) modeling.
7. Scenario and sensitivity analysis.
8. Investment memo generation.
9. Multi-agent Investment Committee simulation.
10. Evidence-backed investment recommendations.

## Core Design Principle

PE-Analyst separates language-model reasoning from deterministic financial computation.

```text
Evidence
   ↓
Structured Data
   ↓
Deterministic Financial Engines
   ↓
Specialist AI Agents
   ↓
Cross-Agent Critique
   ↓
Scenario Analysis
   ↓
Investment Committee Simulation
   ↓
Auditable Investment Recommendation
```

LLMs interpret and reason.

Python performs financial calculations.

The workflow engine orchestrates analysis.

The database stores persistent state and audit history.

Evidence supports material investment claims.

## Architecture

```text
React Frontend
      ↓
FastAPI Backend
      ↓
Application Services
      ↓
Agentic Investment Workflow
      ↓
Specialist Agents
      ↓
Financial / LBO / Scenario Engines
      ↓
Retrieval and Evidence Layer
      ↓
PostgreSQL + pgvector
```

## Specialist Agents

The workflow runs these agents in order (`src/agents/orchestrator.py`):

1. Financial Agent: ratios, growth and quality of earnings
2. Valuation Agent: DCF, comparables and LBO
3. Scenario Analysis Agent: probability-weighted returns, break-even and capital-preservation exit multiples, and an exit x EBITDA sensitivity grid
4. Risk Agent
5. Due Diligence Agent: cited red flags
6. Industry Agent: cited market and competition findings
7. Investment Committee Agent: weighted scorecard
8. Deal Partner, Risk Officer and Operating Partner: the IC debate
9. IC Chairperson: final BUY / HOLD / REJECT ruling
10. Investment Memo Agent: the committee memo in Markdown

Document Intelligence (PDF text, tables and OCR) runs at upload time and feeds stages 1, 5 and 6.

## Deterministic Engines

Financial calculations are performed outside the LLM.

Engines include:

- Financial Ratio Engine
- Growth Analysis Engine
- Cash Flow Analysis Engine
- Quality of Earnings Engine
- LBO Projection Engine
- Debt Schedule Engine
- Return Calculation Engine
- Return Attribution Engine
- Scenario Engine
- Sensitivity Analysis Engine
- Break-Even Analysis Engine

## Technology Stack

### Backend

- Python 3.11+
- FastAPI
- Pydantic
- PostgreSQL
- pgvector

### AI and Agent Orchestration

- Groq (default, free tier: gpt-oss-120b), with xAI Grok, OpenAI, Anthropic, Gemini
  and Ollama as alternatives behind one provider-neutral `LLMService`

### Data Processing

- Pandas
- NumPy
- NumPy Financial

### Document Processing

- pypdf and pdfplumber
- Tesseract OCR (optional)

### Frontend

- React
- Vite

### Infrastructure

- Docker
- Docker Compose

## Project Status

The full workflow is implemented: upload PDF → extraction → specialist agents → IC debate →
memo. It runs behind an authenticated FastAPI backend with a React frontend, Postgres and
pgvector, Docker and CI.

## What the analyst gets back

Not just BUY / HOLD / REJECT. Every ruling comes with a **decision explanation**
(`ic_decision.explanation`, built in `src/agents/decision_explanation.py`):

- The rule that decided it, in plain words: the scorecard result, a Risk Officer veto, or a cap
  to HOLD.
- Each of the five scorecard areas, whether it counted for or against the deal, and its weight.
- What each conclusion rests on: **Document evidence** (quoted passages with file and page),
  **Calculated** (an engine's output from the inputs), or **Analyst input** (typed in for the
  run). The three deserve different levels of trust, so they are labelled.
- The quoted passages themselves: the risk-factor text behind a red flag, the industry
  excerpts, and the statement lines each financial figure was read from.
- What would have to change for a different ruling, the conditions to settle before signing,
  and the gaps in the evidence.

The explanation is assembled from fixed rules with no LLM, so it cannot disagree with the
decision. The same content is written into the memo as "Decision Rationale and Evidence".

## Working as a deal team

**Deals** (`/api/v1/deal-rooms`) are the unit of sharing. A deal holds its documents, its
analyses and its team. The owner adds colleagues by email; every member can then read
everything filed in the deal. Only the owner changes the team, and only the person who ran an
analysis or uploaded a document can delete or move it. Anything not filed in a deal stays
private to the user who created it.

**Several documents per analysis.** A deal usually arrives as a set of files: a CIM, audited
accounts, a management presentation. An analysis takes `document_ids`, combines the evidence
from all of them, and takes each financial figure from the first document that reports it (so
list the audited accounts first). Documents in different units ("in thousands" vs "in
millions") are converted. Every citation records which file it came from.

**Inputs are proposed, then confirmed.** `POST /api/v1/deals/suggest-inputs` reads the selected
documents and proposes the financial statements, the operating assumptions, the competitive
position and the market growth rate. Each proposal is labelled **Document** (read from a cited
page), **Calculated** (arithmetic on such figures), **Default** (a house default the analyst
must set) or **Needs input**. The analyst corrects the form and submits a dozen
`valuation_assumptions`; the server expands them into the full DCF, comparables and LBO inputs
(`src/pe_analyst/deals/assumptions.py`). No JSON is typed. The raw `valuation_inputs` form
still works for scripts. The proposals use fixed rules, not an LLM: competitive position is
read from the company's own wording, which is a starting point to confirm, not a finding.

**Citations open the source.** `GET /api/v1/documents/{id}/file` returns the original PDF to
anyone allowed to read the document. In the app, clicking any cited page opens the PDF at that
page beside the report.

**Comparing runs.** `GET /api/v1/deals/analyses/compare?base=..&other=..` lines up two saved
runs: every input that differs, every headline result that moved (IRR, MOIC, value per share,
risk), and each scorecard area whose vote flipped. Tick two runs on the Analyses page or inside
a deal.

## Saved analyses and background runs

`POST /api/v1/deals/analyses` starts a run in the background and returns an id;
`GET /api/v1/deals/analyses/{id}` returns its status and, once finished, the full report.
`GET /api/v1/deals/analyses` lists your history. The frontend uses these, so a long narrated
run cannot hit a proxy timeout and a finished report can be reopened without re-running it.
`POST /api/v1/deals/analyze` still blocks and returns the report, and saves it too.

Runs execute inside the API process. If the process restarts mid-run, that analysis is marked
failed on startup and must be run again. Use a job queue before running more than one worker.

## Who can see what

Documents, document search and saved analyses belong to the user who created them, and are
shared with the team of the deal they are filed in. Anyone else gets a 404 for them. A user
whose role is `admin` can see everything. Documents uploaded before ownership was added have
no owner and are hidden; upload them again.

## Sample documents

`data/samples/` holds three fictional annual reports that land on BUY, HOLD and REJECT.
Regenerate them with `python scripts/make_sample_pdfs.py`.

## How the LLM is used

The LLM never produces a number or a decision. Each agent finishes its deterministic report
first. If an LLM key is configured, a narrator (`src/agents/narration.py`) then writes analyst
commentary over that report, and the Memo Agent gets a full written draft. Any figure in the
LLM's text that is missing from the report is flagged in `warnings`. Without a key, the workflow
is fully deterministic and returns identical decisions.

```bash
# .env: free key from https://console.groq.com/keys
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
```

## Market data

Comparable peers can be typed in, or fetched from Alpha Vantage (free key) by ticker:

```bash
MARKET_DATA_PROVIDER=alphavantage
MARKET_DATA_API_KEY=...
```

```json
"comparables": {"target": {...}, "peer_tickers": ["ORCL", "SAP", "ADBE"]}
```

Responses are cached for 24 hours in `data/market_cache/`, because the free tier allows about 25
calls a day.

## Document search quality

Search over uploaded documents needs an embedding model. `EMBEDDING_PROVIDER=auto` (the default)
uses OpenAI when `OPENAI_API_KEY` is set, otherwise Gemini when `GEMINI_API_KEY` is set (free
tier), otherwise an offline fallback that only matches exact words. Set one of the two keys for
real semantic search, then upload documents again so they are re-indexed.

## Evaluation and fine-tuning

```bash
python scripts/build_edgar_cases.py MSFT ADBE CRM --fiscal-year 2024  # extraction gold set (SEC XBRL)
python scripts/run_evals.py                                           # score; report -> data/eval_reports/
python scripts/export_finetune_data.py --review                       # approve/reject logged LLM outputs
python scripts/export_finetune_data.py                                # train.jsonl / val.jsonl
```

There are three suites: document extraction, citation accuracy and recommendation consistency.
See `src/pe_analyst/evaluation/datasets/README.md`. Every LLM call is logged in chat
fine-tuning format to `data/llm_logs/`. Reviewing those logs is how the fine-tuning dataset gets
built.

## Run with Docker

```bash
cp .env.example .env        # then set SECRET_KEY and, optionally, GROQ_API_KEY
docker compose up --build
```

This starts Postgres with pgvector, the API on http://localhost:8000 (migrations run on start)
and the frontend on http://localhost:5173.

`SECRET_KEY` must be a unique value of at least 32 characters when `APP_ENV=production`; the
app refuses to start otherwise.

Two settings matter when the frontend and API are not both on localhost:

- `VITE_API_BASE_URL`: the API URL the browser calls. It is baked into the frontend at build
  time, so rebuild the frontend image after changing it.
- `CORS_ORIGINS`: a JSON list of the frontend origins the API accepts, for example
  `CORS_ORIGINS=["https://your-frontend.example.com"]`.

## Development Setup

Clone the repository.

```bash
git clone <repository-url>
cd pe-analyst
```

Create a virtual environment.

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv

source .venv/bin/activate
```

Upgrade pip.

```bash
python -m pip install --upgrade pip
```

Install the project in editable mode with development dependencies.

```bash
pip install -e ".[dev]"
```

Run tests (unit and end-to-end; no API keys or network needed).

```bash
pytest
```

Run Ruff.

```bash
ruff check .
```

