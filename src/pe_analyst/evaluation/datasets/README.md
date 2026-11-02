# Evaluation datasets

One JSON file per case under each suite folder. Run every suite with:

```bash
python scripts/run_evals.py                 # dev split
python scripts/run_evals.py --split holdout # only after tuning is frozen
python scripts/run_evals.py --compare data/eval_reports/<baseline>.json
```

Each run writes a timestamped report to `data/eval_reports/`, so every change can be
compared with the previous baseline. Each case also has a `"split"` of `"dev"` (the default) or
`"holdout"`. Tune against dev only. Holdout is how you check that tuning generalised.

## What ships here

| Suite | Cases | Source |
|---|---|---|
| `recommendation_consistency/` | 6 synthetic archetypes | `scripts/seed_recommendation_cases.py` |
| `document_extraction/` | none yet | build with `scripts/build_edgar_cases.py` |
| `citation_accuracy/` | none yet | hand-labelled (see below) |

The recommendation cases are labelled from conventional PE judgment, **not** from the system's
own output, so a failure is a finding about the rules. They are synthetic. Replace or extend them
with deals labelled by someone with PE experience before trusting the score.

## `document_extraction/*.json`

Generate these from real 10-K filings. The filer's own XBRL tags are the ground truth:

```bash
python scripts/build_edgar_cases.py MSFT ADBE CRM ORCL INTU --fiscal-year 2024
python scripts/build_edgar_cases.py NOW WDAY --fiscal-year 2024 --split holdout
```

This downloads each filing to `document_extraction/samples/` (git-ignored) and converts it to
PDF with headless Edge/Chrome. Expected values are in raw currency units; the extractor's
"(in millions)" detection scales predictions to match.

```json
{
  "id": "msft_2024-10k-financials",
  "split": "dev",
  "input": "samples/msft_2024.pdf",
  "expected": {
    "current": {"revenue": 245122000000.0, "net_income": 88136000000.0},
    "previous": {"revenue": 211915000000.0, "net_income": 72361000000.0}
  }
}
```

A flat `expected` dict means current period only. Fields use `FinancialStatement` names.
Numbers match within 0.5%, because filings round.

## `citation_accuracy/*.json`

Write these by hand. Open the PDF, ask a question an analyst would ask, and record the pages
that actually answer it:

```json
{
  "id": "msft-2024-ai-competition-risk",
  "input": {
    "question": "What competitive risks does the company see in AI?",
    "document_id": "msft-2024",
    "pdf": "../document_extraction/samples/msft_2024.pdf"
  },
  "expected": [{"document_id": "msft-2024", "page_number": 21}]
}
```

`pdf` is ingested into the vector store once per `document_id`. The score is the fraction of
expected pages that appear in the answer's citations.

## `recommendation_consistency/*.json`

`input` is a full deal (the same fields as `POST /deals/analyze`). `expected` is
`BUY`, `HOLD` or `REJECT`. The workflow runs deterministically (no LLM), so this suite measures
the underwriting rules.
