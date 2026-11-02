"""Review logged agent narrations and export them as a chat fine-tuning dataset.

Every LLM narration is logged to data/llm_logs/narration_*.jsonl (see agents/narration.py).
This script turns those logs into training data:

    python scripts/export_finetune_data.py --review     # approve / reject / skip, interactively
    python scripts/export_finetune_data.py              # write train.jsonl + val.jsonl

To correct a weak answer instead of rejecting it, edit the record's assistant message in the
.jsonl file and set "review": "edited". Exported records are approved or edited only, and never
ones flagged with ungrounded numbers unless a reviewer approved them anyway.

Output is the {"messages": [...]} chat format accepted by OpenAI-compatible fine-tuning APIs
and by open-source trainers (Unsloth, Axolotl, TRL) for fine-tuning Llama models.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from pe_analyst.core.config import PROJECT_ROOT

KEEP = {"approved", "edited"}


def load(log_dir: Path) -> list[tuple[Path, list[dict[str, Any]]]]:
    return [
        (path, [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line])
        for path in sorted(log_dir.glob("narration_*.jsonl"))
    ]


def save(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def review(files: list[tuple[Path, list[dict[str, Any]]]]) -> None:
    for path, records in files:
        for record in records:
            if record.get("review") is not None or not record["messages"][-1]["content"]:
                continue
            print("=" * 80)
            print(f"{record['agent']} | {record['model']} | {record['timestamp']}")
            if record.get("ungrounded_numbers"):
                print(f"!! ungrounded numbers: {record['ungrounded_numbers']}")
            print("-" * 80)
            print(record["messages"][-1]["content"])
            choice = input("[a]pprove  [r]eject  [s]kip  [q]uit > ").strip().lower()
            if choice == "q":
                save(path, records)
                return
            if choice in {"a", "r"}:
                record["review"] = "approved" if choice == "a" else "rejected"
        save(path, records)


def export(
    files: list[tuple[Path, list[dict[str, Any]]]], out_dir: Path, val_fraction: float, seed: int
) -> None:
    examples = [
        {"messages": record["messages"]}
        for _, records in files
        for record in records
        if record.get("review") in KEEP and record["messages"][-1]["content"]
    ]
    if not examples:
        print("No approved records yet. Run with --review first.")
        return
    random.Random(seed).shuffle(examples)
    cut = max(1, int(len(examples) * val_fraction)) if len(examples) > 4 else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    save(out_dir / "val.jsonl", examples[:cut])
    save(out_dir / "train.jsonl", examples[cut:])
    print(f"Wrote {len(examples) - cut} train / {cut} val examples to {out_dir}")
    if len(examples) < 200:
        print("Note: aim for a few hundred reviewed examples before fine-tuning is worthwhile.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--logs", type=Path, default=PROJECT_ROOT / "data" / "llm_logs")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "data" / "finetune")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    files = load(args.logs)
    if not files:
        print(f"No narration logs in {args.logs}. Run deals with an LLM key configured first.")
        return 0
    if args.review:
        review(files)
    else:
        export(files, args.out, args.val_fraction, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
