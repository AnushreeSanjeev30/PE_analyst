"""Loads JSON eval cases from ``datasets/<suite>/*.json`` (see ``datasets/README.md``)."""

from __future__ import annotations

import json
from pathlib import Path

from pe_analyst.core.config import PROJECT_ROOT

from .models import EvalCase

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

SUITES = ("document_extraction", "citation_accuracy", "recommendation_consistency")

# Tune against "dev"; report "holdout" only after tuning is frozen, so the score isn't overfit.
SPLITS = ("dev", "holdout")


def _resolve(raw: str, base_dir: Path) -> str:
    """PDF paths may be relative to the case file or to the project root."""

    path = Path(raw)
    if path.is_absolute():
        return str(path)
    for candidate in (base_dir / path, PROJECT_ROOT / path):
        if candidate.exists():
            return str(candidate)
    return str(base_dir / path)


def load_cases(
    suite: str, *, split: str | None = None, root: Path = DATASETS_DIR
) -> list[EvalCase]:
    if suite not in SUITES:
        raise ValueError(f"Unknown suite {suite!r}; expected one of {', '.join(SUITES)}")
    cases = []
    for path in sorted((root / suite).glob("*.json")):
        body = json.loads(path.read_text(encoding="utf-8"))
        case_split = body.get("split", "dev")
        if split is not None and case_split != split:
            continue
        case_input = body["input"]
        if suite == "document_extraction" and isinstance(case_input, str):
            case_input = _resolve(case_input, path.parent)
        elif isinstance(case_input, dict) and isinstance(case_input.get("pdf"), str):
            case_input = {**case_input, "pdf": _resolve(case_input["pdf"], path.parent)}
        cases.append(
            EvalCase(
                id=body.get("id", path.stem),
                input=case_input,
                expected=body["expected"],
                metadata={**body.get("metadata", {}), "split": case_split, "path": str(path)},
            )
        )
    return cases


__all__ = ["DATASETS_DIR", "SPLITS", "SUITES", "load_cases"]
