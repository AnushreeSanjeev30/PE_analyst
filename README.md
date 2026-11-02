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

- Groq (default, free tier: Llama 3.3 70B / gpt-oss), with xAI Grok, OpenAI, Anthropic, Gemini
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

