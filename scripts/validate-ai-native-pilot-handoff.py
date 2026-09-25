#!/usr/bin/env python3
"""Validate a downloaded/local pilot handoff before promoting formal freeze files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)
EXPECTED_FILES = (
    "execution-profile-r3.json",
    "formal-schedule-r3.json",
    "formal-plan-r3.lock.json",
)
EXPECTED_RUNS = ("T05-A-01", "T08-B-01", "T20-C-01")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha256(ref: str, path: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"cannot read frozen execution tool {ref}:{path}: "
            + proc.stderr.decode("utf-8", errors="replace")
        )
    return hashlib.sha256(proc.stdout).hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff-dir", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    handoff = args.handoff_dir.resolve()
    lock = load(EXPERIMENT / "EXECUTION-PREPILOT-LOCK.json")
    benchmark = load(EXPERIMENT / "BENCHMARK-LOCK.json")
    analysis = load(EXPERIMENT / "ANALYSIS-LOCK.json")
    errors: list[str] = []

    files = {name: handoff / name for name in EXPECTED_FILES}
    for name, path in files.items():
        if not path.exists():
            errors.append(f"missing generated freeze file: {name}")

    pilot_root = handoff / "pilot-runs"
    if not pilot_root.exists():
        errors.append("missing pilot-runs directory")

    if errors:
        print("Pilot handoff validation FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    profile = load(files["execution-profile-r3.json"])
    schedule = load(files["formal-schedule-r3.json"])
    plan = load(files["formal-plan-r3.lock.json"])

    if profile.get("profile_id") != "claude-code-r10-r3":
        errors.append("expected the fresh R10/R3 execution profile")
    if plan.get("plan_id") != "formal-plan-r3":
        errors.append("expected formal-plan-r3")
    expected_repo_sha = lock["repository_sha"]
    if profile.get("status") != "frozen":
        errors.append("execution profile is not frozen")
    if profile.get("pilot_repository_sha") != expected_repo_sha:
        errors.append(
            "pilot repository SHA mismatch: "
            f"{profile.get('pilot_repository_sha')} != {expected_repo_sha}"
        )

    required_agent_config = lock.get("required_agent_config", {})
    actual_agent_config = profile.get("agent", {})
    for key, expected in required_agent_config.items():
        actual = actual_agent_config.get(key)
        if actual != expected:
            errors.append(
                f"execution profile agent.{key} mismatch: "
                f"{actual!r} != {expected!r}"
            )

    required_environment = lock.get("required_environment", {})
    actual_environment = profile.get("environment", {})
    for key, expected in required_environment.items():
        actual = actual_environment.get(key)
        if actual != expected:
            errors.append(
                f"execution profile environment.{key} mismatch: "
                f"{actual!r} != {expected!r}"
            )

    frozen_tool_paths = {
        "runner_file_sha256": "scripts/ai-native-repo-experiment.py",
        "adapter_file_sha256": ("scripts/narness-claude-adapter.py" if profile.get("agent", {}).get("agent") == "claude-code" else "scripts/ai-native-codex-adapter.py"),
        "scorer_file_sha256": "scripts/score-ai-native-run.py",
        "seal_file_sha256": "scripts/seal-ai-native-run.py",
        "run_seal_verifier_file_sha256": "scripts/verify-ai-native-run-seal.py",
        "formal_orchestrator_file_sha256": "scripts/run-ai-native-formal.py",
        "formal_readiness_file_sha256": "scripts/prepare-ai-native-formal-collection.py",
    }
    if profile.get("agent", {}).get("agent") == "claude-code":
        frozen_tool_paths.update({
            "command_mapper_file_sha256": "scripts/ai-native-codex-adapter.py",
        })
    profile_tooling = profile.get("tooling", {})
    for key, repo_path in frozen_tool_paths.items():
        expected = git_blob_sha256(expected_repo_sha, repo_path)
        actual = profile_tooling.get(key)
        if actual != expected:
            errors.append(
                f"execution profile tooling.{key} mismatch for "
                f"{repo_path}: {actual} != {expected}"
            )

    source_pilots = {
        item.get("run_id"): item
        for item in profile.get("source_pilots", [])
    }
    if set(source_pilots) != set(EXPECTED_RUNS):
        errors.append(
            "execution profile pilot set mismatch: "
            f"{sorted(source_pilots)} != {sorted(EXPECTED_RUNS)}"
        )

    validation_outputs: dict[str, str] = {}
    for run_id in EXPECTED_RUNS:
        run_dir = pilot_root / run_id
        if not run_dir.exists():
            errors.append(f"missing pilot run directory: {run_id}")
            continue
        run_json = load(run_dir / "run.json")
        if (
            run_json.get("environment", {}).get("harness_repository_sha")
            != expected_repo_sha
        ):
            errors.append(f"{run_id}: harness repository SHA mismatch")

        validation = run([
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-native-pilot.py"),
            "--run-dir",
            str(run_dir),
        ])
        validation_outputs[run_id] = validation.stdout.strip()
        if validation.returncode != 0:
            errors.append(
                f"{run_id}: pilot validation failed: "
                + validation.stdout.strip().replace("\n", " | ")
            )

        source = source_pilots.get(run_id)
        if source:
            for name, expected_hash in (source.get("artifacts") or {}).items():
                path = run_dir / name
                if not path.exists():
                    errors.append(f"{run_id}: profile artifact missing: {name}")
                    continue
                actual = sha256_file(path)
                if actual != expected_hash:
                    errors.append(
                        f"{run_id}: artifact hash mismatch for {name}: "
                        f"{actual} != {expected_hash}"
                    )

    profile_id = profile.get("profile_id")
    if schedule.get("status") != "pre-registered":
        errors.append("formal schedule is not pre-registered")
    if schedule.get("profile_id") != profile_id:
        errors.append("formal schedule/profile ID mismatch")
    if int(schedule.get("run_count", -1)) != 216:
        errors.append("formal schedule does not contain 216 runs")
    if int(schedule.get("replications", -1)) != 3:
        errors.append("formal schedule does not contain 3 replications")

    if plan.get("status") != "frozen":
        errors.append("formal plan is not frozen")
    if plan.get("execution_profile_id") != profile_id:
        errors.append("formal plan/profile ID mismatch")
    if plan.get("execution_profile_sha256") != sha256_file(
        files["execution-profile-r3.json"]
    ):
        errors.append("formal plan execution-profile hash mismatch")
    if plan.get("schedule_sha256") != sha256_file(
        files["formal-schedule-r3.json"]
    ):
        errors.append("formal plan schedule hash mismatch")
    if plan.get("benchmark_revision") != benchmark.get("benchmark_revision"):
        errors.append("formal plan benchmark revision mismatch")
    if plan.get("benchmark_definition_sha") != benchmark.get("definition_sha"):
        errors.append("formal plan benchmark definition mismatch")
    if plan.get("analysis_revision") != analysis.get("analysis_revision"):
        errors.append("formal plan analysis revision mismatch")
    if plan.get("analysis_definition_sha") != analysis.get("definition_sha"):
        errors.append("formal plan analysis definition mismatch")

    workflow_metadata_path = handoff / "workflow-metadata.txt"
    workflow_metadata = (
        workflow_metadata_path.read_text(encoding="utf-8")
        if workflow_metadata_path.exists()
        else None
    )
    if workflow_metadata and f"repository_sha={expected_repo_sha}" not in workflow_metadata:
        errors.append("workflow metadata repository SHA does not match pre-pilot lock")

    report = {
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
        "execution_prepilot_revision": lock["execution_prepilot_revision"],
        "expected_repository_sha": expected_repo_sha,
        "profile_id": profile_id,
        "pilot_set_digest_sha256": profile.get("pilot_set_digest_sha256"),
        "freeze_files": {
            name: sha256_file(path)
            for name, path in sorted(files.items())
        },
        "pilot_runs": {
            run_id: {
                "run_dir": str(pilot_root / run_id),
                "validation_output": validation_outputs.get(run_id),
            }
            for run_id in EXPECTED_RUNS
        },
        "workflow_metadata_present": workflow_metadata is not None,
        "errors": errors,
    }

    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if errors:
        print("Pilot handoff validation FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Pilot handoff validation OK")
    print(f"  pre-pilot revision: {lock['execution_prepilot_revision']}")
    print(f"  repository SHA: {expected_repo_sha}")
    print(f"  profile: {profile_id}")
    print(f"  pilot evidence digest: {profile.get('pilot_set_digest_sha256')}")
    print("  formal schedule: 216 runs / 3 replications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

