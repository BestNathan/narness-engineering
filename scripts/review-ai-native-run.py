#!/usr/bin/env python3
"""Attach a human-reviewed failure taxonomy label to one sealed formal run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


TAXONOMY = {
    "R1": "target not found",
    "R2": "wrong semantic owner selected",
    "R3": "important dependency/consumer missed",
    "R4": "contract misunderstood",
    "R5": "invariant missed",
    "R6": "implementation error",
    "R7": "verification gap",
    "R8": "feedback insufficient or misleading",
    "R9": "tool/runtime failure",
    "R10": "task ambiguity",
    "R11": "treatment metadata stale/incorrect",
    "R12": "architecture treatment introduced accidental complexity",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--primary", choices=[*TAXONOMY, "NONE"], required=True)
    ap.add_argument("--secondary", action="append", default=[], choices=list(TAXONOMY))
    ap.add_argument("--notes", default="")
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    run = load(run_dir / "run.json")
    if not run.get("admissible_for_final_analysis"):
        raise RuntimeError("run is not sealed/admissible")

    success = bool(run.get("task_success"))
    if success and args.primary != "NONE":
        raise RuntimeError("successful run must use primary=NONE")
    if not success and args.primary == "NONE":
        raise RuntimeError("failed run requires one R1-R12 primary failure code")

    review_path = run_dir / "review.json"
    if review_path.exists() and not args.force:
        raise RuntimeError(f"review already exists: {review_path}; use --force to replace")

    secondary = [code for code in args.secondary if code != args.primary]
    review = {
        "schema_version": 1,
        "run_id": run["run_id"],
        "task_id": run["task_id"],
        "treatment": run["treatment"],
        "task_success": success,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "primary_failure_code": None if args.primary == "NONE" else args.primary,
        "primary_failure": None if args.primary == "NONE" else TAXONOMY[args.primary],
        "secondary_failure_codes": secondary,
        "secondary_failures": [TAXONOMY[x] for x in secondary],
        "notes": args.notes,
        "evidence": args.evidence,
    }
    review_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {review_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
