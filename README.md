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

## Planned Architecture

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

The planned system contains the following specialist agents:

- Document Intelligence Agent
- Financial Analysis Agent
- Industry Research Agent
- Due Diligence Agent
- Risk Agent
- Scenario Analysis Agent
- Investment Memo Agent
- Deal Partner Agent
- Risk Officer Agent
- Operating Partner Agent
- Investment Committee Chairperson Agent

## Deterministic Engines

Financial calculations are performed outside the LLM.

Planned engines include:

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

- OpenAI API
- LangGraph

### Data Processing

- Pandas
- NumPy
- NumPy Financial

### Document Processing

- PyMuPDF
- Docling

### Frontend

- React
- Vite

### Infrastructure

- Docker
- Docker Compose

## Project Status

The project is currently under active development.

Current milestone:

```text
Milestone 1
Repository Foundation and Core Infrastructure
```

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

Run tests.

```bash
pytest
```

Run Ruff.

```bash
ruff check .
```

## Disclaimer

PE-Analyst is a research and educational decision-support system.

It does not provide financial, investment, legal, accounting, or tax advice.

The system should not be used as the sole basis for real-world investment decisions.