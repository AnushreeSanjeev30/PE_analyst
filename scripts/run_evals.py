"""Run the evaluation suites and write a timestamped JSON report.

Usage:
    python scripts/run_evals.py                          # every suite, dev split
    python scripts/run_evals.py --suite recommendation_consistency
    python scripts/run_evals.py --split holdout          # only once tuning is frozen
    python scripts/run_evals.py --fail-under 0.8         # non-zero exit for CI

Each run is saved under data/eval_reports/ so a change can be compared against the baseline:
    python scripts/run_evals.py --compare data/eval_reports/<baseline>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents.narration import to_jsonable
from agents.prompts import PROMPT_VERSION
from pe_analyst.core.config import PROJECT_ROOT, get_settings
from pe_analyst.evaluation import SPLITS, SUITES, EvalReport, EvaluationRunner, load_cases
from pe_analyst.evaluation.systems import SUITE_METRICS, build_system

PASS_THRESHOLDS = {
    "document_extraction": 0.9,  # a case passes when >=90% of its fields match
    "citation_accuracy": 0.5,  # ... when at least half the expected pages are cited
    "recommendation_consistency": 1.0,
}


def run_suite(suite: str, split: str | None, root: Path) -> tuple[EvalReport, int]:
    cases = load_cases(suite, split=split, root=root)
    if not cases:
        return EvalReport([]), 0
    runner = EvaluationRunner(
        build_system(suite, get_settings()),
        SUITE_METRICS[suite],
        pass_threshold=PASS_THRESHOLDS[suite],
    )
    return runner.run(cases), len(cases)


def field_misses(result: Any) -> list[str]:
    """For extraction cases: which fields were wrong, for error analysis."""

    from pe_analyst.evaluation.metrics import values_match
    from pe_analyst.evaluation.systems import flatten_periods

    if not isinstance(result.prediction, dict) or not isinstance(result.expected, dict):
        return []
    expected = flatten_periods(result.expected)
    return [
        f"{key}: expected {value}, got {result.prediction.get(key)}"
        for key, value in expected.items()
        if not values_match(result.prediction.get(key), value)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--suite", choices=[*SUITES, "all"], default="all")
    parser.add_argument("--split", choices=[*SPLITS, "all"], default="dev")
    parser.add_argument("--datasets", type=Path, default=None, help="datasets root override")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "eval_reports")
    parser.add_argument("--compare", type=Path, default=None, help="baseline report to diff")
    parser.add_argument("--fail-under", type=float, default=None, help="min mean score per suite")
    args = parser.parse_args()

    from pe_analyst.evaluation import DATASETS_DIR

    root = args.datasets or DATASETS_DIR
    split = None if args.split == "all" else args.split
    suites = SUITES if args.suite == "all" else (args.suite,)
    baseline = json.loads(args.compare.read_text(encoding="utf-8")) if args.compare else None

    output: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "split": args.split,
        "prompt_version": PROMPT_VERSION,
        "suites": {},
    }
    failed = False
    print(f"{'suite':<28}{'cases':>6}{'mean':>8}{'pass':>8}  vs baseline")
    for suite in suites:
        report, count = run_suite(suite, split, root)
        previous = (baseline or {}).get("suites", {}).get(suite, {}).get("mean_score")
        delta = "" if previous is None or not count else f"{report.mean_score - previous:+.3f}"
        print(f"{suite:<28}{count:>6}{report.mean_score:>8.3f}{report.pass_rate:>8.1%}  {delta}")
        for result in report.results:
            if not result.passed:
                reason = result.details or "; ".join(field_misses(result)[:4])
                if not reason:
                    reason = f"expected {result.expected}, got {result.prediction}"
                print(f"    FAIL {result.case_id} ({result.score:.2f}): {reason}")
        output["suites"][suite] = {
            "cases": count,
            "mean_score": report.mean_score,
            "pass_rate": report.pass_rate,
            "results": to_jsonable(report.results, truncate=False),
        }
        if args.fail_under is not None and count and report.mean_score < args.fail_under:
            failed = True

    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f"eval_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nReport written to {path}")
    if not any(output["suites"][suite]["cases"] for suite in suites):
        print("No cases found. Add JSON cases under", root, "(see its README.md).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
