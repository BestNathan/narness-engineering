#!/usr/bin/env python3
"""Build all derived artifacts for the AI-native repository research report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)


def run(cmd: list[str], *, allow_codes: set[int] | None = None) -> int:
    proc = subprocess.run(cmd, cwd=ROOT)
    allowed = allow_codes or {0}
    if proc.returncode not in allowed:
        raise RuntimeError(f"command failed with {proc.returncode}: {' '.join(cmd)}")
    return proc.returncode


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--conclusions", type=Path)
    args = ap.parse_args()

    runs_root = args.runs_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    aggregate = ROOT / "scripts" / "aggregate-ai-native-results.py"
    analyze = ROOT / "scripts" / "analyze-ai-native-effects.py"
    failures = ROOT / "scripts" / "aggregate-ai-native-failures.py"
    report = ROOT / "scripts" / "generate-ai-native-research-report.py"
    validate_conclusion = ROOT / "scripts" / "validate-ai-native-conclusion.py"
    verify_collection = ROOT / "scripts" / "verify-ai-native-collection.py"

    schedule_path = EXPERIMENT / "runner" / "formal-schedule-r2.json"
    profile_path = EXPERIMENT / "runner" / "execution-profile-r2.json"
    plan_path = EXPERIMENT / "runner" / "formal-plan-r2.lock.json"
    lock_path = EXPERIMENT / "BENCHMARK-LOCK.json"
    analysis_lock_path = EXPERIMENT / "ANALYSIS-LOCK.json"
    collection_manifest_path = out / "collection-manifest.json"
    collection_manifest = None

    if schedule_path.exists() and profile_path.exists() and plan_path.exists():
        collection_cmd = [
            sys.executable, str(verify_collection),
            "--runs-root", str(runs_root),
            "--schedule", str(schedule_path),
            "--execution-profile", str(profile_path),
            "--benchmark-lock", str(lock_path),
            "--analysis-lock", str(analysis_lock_path),
            "--formal-plan-lock", str(plan_path),
            "--output", str(collection_manifest_path),
        ]
        if args.allow_incomplete:
            collection_cmd.append("--allow-incomplete")
        run(collection_cmd)
        collection_manifest = load(collection_manifest_path)
    elif not args.allow_incomplete:
        missing = []
        if not schedule_path.exists():
            missing.append(str(schedule_path))
        if not profile_path.exists():
            missing.append(str(profile_path))
        if not plan_path.exists():
            missing.append(str(plan_path))
        raise RuntimeError("formal collection metadata missing: " + ", ".join(missing))

    run([
        sys.executable, str(aggregate),
        "--runs-root", str(runs_root),
        "--output-dir", str(out),
    ])

    run([
        sys.executable, str(analyze),
        "--raw-runs", str(out / "raw-runs.csv"),
        "--strata", str(EXPERIMENT / "analysis-strata.json"),
        "--output-dir", str(out),
    ])

    failure_cmd = [
        sys.executable, str(failures),
        "--runs-root", str(runs_root),
        "--strata", str(EXPERIMENT / "analysis-strata.json"),
        "--output-dir", str(out),
    ]
    if args.allow_incomplete:
        failure_cmd.append("--allow-missing-reviews")
    run(failure_cmd, allow_codes={0, 2} if args.allow_incomplete else {0})

    conclusion_complete = False
    if args.conclusions:
        run([
            sys.executable, str(validate_conclusion),
            "--conclusions", str(args.conclusions.resolve()),
        ])
        conclusion_complete = True

    report_cmd = [
        sys.executable, str(report),
        "--results-dir", str(out),
        "--output", str(out / "research-report.md"),
    ]
    if args.conclusions:
        report_cmd.extend(["--conclusions", str(args.conclusions.resolve())])
    run(report_cmd)

    summary = load(out / "summary.json")
    total_runs = sum(int(summary.get(t, {}).get("n", 0) or 0) for t in ("A", "B", "C"))
    task_cells = {
        treatment: int(summary.get(treatment, {}).get("tasks", 0) or 0)
        for treatment in ("A", "B", "C")
    }

    expected_runs = None
    if schedule_path.exists():
        schedule = load(schedule_path)
        expected_runs = int(schedule.get("run_count", 0) or 0)

    failure_summary = load(out / "failure-summary.json")
    completeness = {
        "schema_version": 1,
        "sealed_admissible_runs": total_runs,
        "distinct_tasks_by_treatment": task_cells,
        "expected_runs_from_schedule": expected_runs,
        "all_24_tasks_present_per_treatment": all(v == 24 for v in task_cells.values()),
        "run_count_complete": (
            expected_runs is not None and total_runs == expected_runs
        ),
        "missing_failure_reviews": failure_summary.get("missing_review_count", 0),
        "report_generated": (out / "research-report.md").exists(),
        "hypothesis_classification_complete": conclusion_complete,
        "collection_manifest_present": collection_manifest is not None,
        "collection_verified_run_count": (
            collection_manifest.get("verified_run_count") if collection_manifest else None
        ),
        "collection_complete": (
            bool(collection_manifest.get("complete")) if collection_manifest else False
        ),
        "collection_digest_sha256": (
            collection_manifest.get("collection_digest_sha256")
            if collection_manifest else None
        ),
    }
    completeness_path = out / "research-completeness.json"
    completeness_path.write_text(
        json.dumps(completeness, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    benchmark_lock = load(EXPERIMENT / "BENCHMARK-LOCK.json")
    analysis_lock = load(EXPERIMENT / "ANALYSIS-LOCK.json")
    artifact_candidates = [
        out / "raw-runs.csv",
        out / "summary.json",
        out / "summary.md",
        out / "paired-effects.json",
        out / "paired-effects.md",
        out / "failure-summary.json",
        out / "failure-summary.md",
        out / "collection-manifest.json",
        runs_root / "_collection" / "collection-start.json",
        completeness_path,
        out / "research-report.md",
        EXPERIMENT / "BENCHMARK-LOCK.json",
        EXPERIMENT / "ANALYSIS-LOCK.json",
        EXPERIMENT / "treatments" / "construction-cost-r1.json",
        EXPERIMENT / "treatments" / "construction-cost.md",
        EXPERIMENT / "FAILURE-REVIEW-PROTOCOL.md",
        EXPERIMENT / "THREATS-TO-VALIDITY.md",
        EXPERIMENT / "DATA-RETENTION.md",
        schedule_path,
        profile_path,
        plan_path,
        EXPERIMENT / "runner" / "PILOT-FREEZE-r2.json",
        ROOT / "scripts" / "aggregate-ai-native-results.py",
        ROOT / "scripts" / "analyze-ai-native-effects.py",
        ROOT / "scripts" / "generate-ai-native-research-report.py",
        ROOT / "scripts" / "aggregate-ai-native-failures.py",
        ROOT / "scripts" / "verify-ai-native-collection.py",
        ROOT / "scripts" / "validate-ai-native-conclusion.py",
        ROOT / "scripts" / "finalize-ai-native-research.py",
    ]
    if args.conclusions:
        artifact_candidates.append(args.conclusions.resolve())

    artifact_hashes: dict[str, str] = {}
    for path in artifact_candidates:
        if not path.exists():
            continue
        try:
            label = str(path.relative_to(ROOT))
        except ValueError:
            try:
                label = "results/" + str(path.relative_to(out))
            except ValueError:
                label = "external/" + path.name
        artifact_hashes[label] = sha256_file(path)

    digest_material = "\n".join(
        f"{name}:{digest}" for name, digest in sorted(artifact_hashes.items())
    ).encode("utf-8")
    artifact_manifest = {
        "schema_version": 1,
        "experiment_id": benchmark_lock["experiment_id"],
        "benchmark_revision": benchmark_lock["benchmark_revision"],
        "benchmark_definition_sha": benchmark_lock["definition_sha"],
        "analysis_revision": analysis_lock["analysis_revision"],
        "analysis_definition_sha": analysis_lock["definition_sha"],
        "execution_profile_id": (
            load(profile_path).get("profile_id") if profile_path.exists() else None
        ),
        "collection_digest_sha256": (
            collection_manifest.get("collection_digest_sha256")
            if collection_manifest else None
        ),
        "complete": (
            completeness["run_count_complete"]
            and completeness["all_24_tasks_present_per_treatment"]
            and completeness["missing_failure_reviews"] == 0
            and completeness["hypothesis_classification_complete"]
            and completeness["collection_complete"]
        ),
        "artifacts": dict(sorted(artifact_hashes.items())),
        "artifact_set_digest_sha256": hashlib.sha256(digest_material).hexdigest(),
    }
    (out / "research-artifact-manifest.json").write_text(
        json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not args.allow_incomplete:
        errors = []
        if expected_runs is None:
            errors.append("formal schedule is not frozen/present")
        elif total_runs != expected_runs:
            errors.append(f"sealed run count {total_runs} != expected {expected_runs}")
        if not all(v == 24 for v in task_cells.values()):
            errors.append(f"task coverage incomplete: {task_cells}")
        if failure_summary.get("missing_review_count", 0):
            errors.append("failed runs still need taxonomy review")
        if not conclusion_complete:
            errors.append("reviewed H1-H5 conclusion file is required")
        if collection_manifest is None:
            errors.append("formal collection seal manifest is required")
        elif not collection_manifest.get("complete"):
            errors.append("formal collection seal verification is incomplete")
        if errors:
            print("Research data pipeline is INCOMPLETE")
            for error in errors:
                print(f"  - {error}")
            return 2

    print("Research data artifacts generated")
    print(f"  runs: {total_runs}")
    print(f"  report: {out / 'research-report.md'}")
    print(f"  artifact manifest: {out / 'research-artifact-manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
