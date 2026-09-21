#!/usr/bin/env python3
"""Attach a human-reviewed failure taxonomy label to one sealed formal run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    if not success and not args.notes.strip():
        raise RuntimeError("failed run review requires a causal rationale in --notes")
    if not success and not args.evidence:
        raise RuntimeError(
            "failed run review requires at least one --evidence reference"
        )

    seal_path = run_dir / "seal.json"
    if not seal_path.exists():
        raise RuntimeError("sealed run has no seal.json")

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
        "review_policy_version": 1,
        "review_scope": "per-run-causal-review-before-aggregate-interpretation",
        "reviewed_run_seal_sha256": sha256_file(seal_path),
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
