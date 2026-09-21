#!/usr/bin/env python3
"""Verify the tamper-evident seal of one formal AI-native benchmark run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--expected-profile-id")
    ap.add_argument("--expected-benchmark-sha")
    ap.add_argument("--expected-formal-plan-sha256")
    ap.add_argument("--expected-analysis-sha")
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    run_path = run_dir / "run.json"
    seal_path = run_dir / "seal.json"
    errors: list[str] = []

    if not run_path.exists():
        errors.append("run.json missing")
    if not seal_path.exists():
        errors.append("seal.json missing")
    if errors:
        print("Run seal verification FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    run = load(run_path)
    seal = load(seal_path)

    if not run.get("admissible_for_final_analysis"):
        errors.append("run.json is not marked admissible")
    if not run.get("admissibility", {}).get("sealed"):
        errors.append("run.json admissibility.sealed is not true")
    if seal.get("run_id") != run.get("run_id"):
        errors.append("seal/run run_id mismatch")
    if seal.get("task_id") != run.get("task_id"):
        errors.append("seal/run task_id mismatch")
    if seal.get("treatment") != run.get("treatment"):
        errors.append("seal/run treatment mismatch")

    admissibility = run.get("admissibility", {})
    if seal.get("benchmark_definition_sha") != admissibility.get("benchmark_definition_sha"):
        errors.append("seal/run benchmark definition mismatch")
    if seal.get("analysis_revision") != admissibility.get("analysis_revision"):
        errors.append("seal/run analysis revision mismatch")
    if seal.get("analysis_definition_sha") != admissibility.get("analysis_definition_sha"):
        errors.append("seal/run analysis definition mismatch")
    if seal.get("execution_profile_id") != admissibility.get("execution_profile_id"):
        errors.append("seal/run execution profile mismatch")
    if seal.get("formal_plan_sha256") != admissibility.get("formal_plan_sha256"):
        errors.append("seal/run formal plan mismatch")
    if seal.get("formal_plan_id") != admissibility.get("formal_plan_id"):
        errors.append("seal/run formal plan ID mismatch")

    if args.expected_profile_id and seal.get("execution_profile_id") != args.expected_profile_id:
        errors.append(
            f"execution profile mismatch: {seal.get('execution_profile_id')} != "
            f"{args.expected_profile_id}"
        )
    if args.expected_benchmark_sha and seal.get("benchmark_definition_sha") != args.expected_benchmark_sha:
        errors.append(
            f"benchmark SHA mismatch: {seal.get('benchmark_definition_sha')} != "
            f"{args.expected_benchmark_sha}"
        )
    if args.expected_analysis_sha and seal.get("analysis_definition_sha") != args.expected_analysis_sha:
        errors.append(
            f"analysis SHA mismatch: {seal.get('analysis_definition_sha')} != "
            f"{args.expected_analysis_sha}"
        )
    if (
        args.expected_formal_plan_sha256
        and seal.get("formal_plan_sha256") != args.expected_formal_plan_sha256
    ):
        errors.append(
            f"formal plan SHA mismatch: {seal.get('formal_plan_sha256')} != "
            f"{args.expected_formal_plan_sha256}"
        )

    artifacts = seal.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        errors.append("seal has no artifact digest map")
    else:
        required = {"run.json", "score.json", "trace.jsonl", "final.diff"}
        missing_from_seal = sorted(required - set(artifacts))
        if missing_from_seal:
            errors.append(f"seal omits required artifacts: {missing_from_seal}")

        for name, expected in sorted(artifacts.items()):
            path = run_dir / name
            if not path.exists():
                errors.append(f"sealed artifact missing: {name}")
                continue
            actual = sha256_file(path)
            if actual != expected:
                errors.append(
                    f"sealed artifact changed: {name}: {actual} != {expected}"
                )

    if errors:
        print("Run seal verification FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Run seal verification OK")
    print(f"  run: {run['run_id']}")
    print(f"  artifacts: {len(artifacts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
