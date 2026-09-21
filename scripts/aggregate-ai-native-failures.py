#!/usr/bin/env python3
"""Aggregate the pre-registered R1-R12 failure taxonomy across sealed runs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


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


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--strata", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--allow-missing-reviews", action="store_true")
    args = ap.parse_args()

    strata = load(args.strata.resolve())
    task_class = {
        task: klass
        for klass, tasks in strata["task_classes"].items()
        for task in tasks
    }

    failed_runs: list[dict[str, Any]] = []
    missing_reviews: list[str] = []
    by_code = Counter()
    by_treatment: dict[str, Counter] = defaultdict(Counter)
    by_class: dict[str, Counter] = defaultdict(Counter)

    for run_path in sorted(args.runs_root.resolve().rglob("run.json")):
        run = load(run_path)
        if not run.get("admissible_for_final_analysis") or run.get("task_success"):
            continue
        review_path = run_path.parent / "review.json"
        if not review_path.exists():
            missing_reviews.append(run["run_id"])
            failed_runs.append({
                "run_id": run["run_id"],
                "task_id": run["task_id"],
                "treatment": run["treatment"],
                "task_class": task_class.get(run["task_id"]),
                "reviewed": False,
            })
            continue

        review = load(review_path)
        code = review.get("primary_failure_code")
        if code not in TAXONOMY:
            raise RuntimeError(f"{review_path}: invalid primary failure code {code!r}")
        if review.get("review_policy_version") != 1:
            raise RuntimeError(f"{review_path}: unsupported/missing review policy version")
        seal_path = run_path.parent / "seal.json"
        if not seal_path.exists():
            raise RuntimeError(f"{review_path}: reviewed run has no seal.json")
        expected_seal = sha256_file(seal_path)
        if review.get("reviewed_run_seal_sha256") != expected_seal:
            raise RuntimeError(
                f"{review_path}: review is not anchored to the current run seal"
            )
        if not str(review.get("notes", "")).strip():
            raise RuntimeError(f"{review_path}: failure rationale is empty")
        if not review.get("evidence"):
            raise RuntimeError(f"{review_path}: failure evidence references are empty")

        by_code[code] += 1
        by_treatment[run["treatment"]][code] += 1
        by_class[task_class.get(run["task_id"], "unknown")][code] += 1
        failed_runs.append({
            "run_id": run["run_id"],
            "task_id": run["task_id"],
            "treatment": run["treatment"],
            "task_class": task_class.get(run["task_id"]),
            "reviewed": True,
            "primary_failure_code": code,
            "primary_failure": TAXONOMY[code],
            "secondary_failure_codes": review.get("secondary_failure_codes", []),
            "notes": review.get("notes", ""),
        })

    result = {
        "schema_version": 1,
        "failed_admissible_runs": len(failed_runs),
        "reviewed_failed_runs": sum(1 for row in failed_runs if row["reviewed"]),
        "missing_review_count": len(missing_reviews),
        "missing_review_run_ids": missing_reviews,
        "primary_failures": {
            code: {
                "label": TAXONOMY[code],
                "count": by_code.get(code, 0),
            }
            for code in TAXONOMY
        },
        "by_treatment": {
            treatment: dict(sorted(counter.items()))
            for treatment, counter in sorted(by_treatment.items())
        },
        "by_task_class": {
            klass: dict(sorted(counter.items()))
            for klass, counter in sorted(by_class.items())
        },
        "runs": failed_runs,
    }

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "failure-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Failure Taxonomy — Generated",
        "",
        f"Failed admissible runs: {len(failed_runs)}",
        f"Reviewed failed runs: {result['reviewed_failed_runs']}",
        f"Missing reviews: {len(missing_reviews)}",
        "",
        "| Code | Failure class | Count |",
        "|---|---|---:|",
    ]
    for code, label in TAXONOMY.items():
        lines.append(f"| {code} | {label} | {by_code.get(code, 0)} |")
    if missing_reviews:
        lines.extend([
            "",
            "## Missing reviews",
            "",
            *[f"- {run_id}" for run_id in missing_reviews],
        ])
    (out / "failure-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Aggregated {len(failed_runs)} failed admissible runs")
    if missing_reviews:
        print(f"Missing failure reviews: {len(missing_reviews)}")
        if not args.allow_missing_reviews:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
