#!/usr/bin/env python3
"""Freeze/validate the machine and Git state used to start formal collection.

The first invocation writes one immutable collection-start record. Later invocations
must reproduce the same critical state, which prevents a resumed 216-run study from
silently changing harness commits, profile/schedule/plan bytes, or tool versions.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(cmd: list[str], *, cwd: Path = ROOT) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def require_tracked_head_file(path: Path, errors: list[str]) -> str | None:
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        errors.append(f"formal metadata is outside narness-engineering: {path}")
        return None

    code, _ = capture(["git", "ls-files", "--error-unmatch", str(rel)])
    if code != 0:
        errors.append(f"formal metadata is not committed/tracked: {rel}")
        return str(rel)

    code, _ = capture(["git", "diff", "--quiet", "HEAD", "--", str(rel)])
    if code != 0:
        errors.append(f"formal metadata differs from HEAD: {rel}")

    code, head_bytes = capture(["git", "show", f"HEAD:{rel}"])
    if code != 0:
        errors.append(f"cannot read formal metadata from HEAD: {rel}")
    else:
        # git show in text mode strips a final newline. Hash bytes via a binary
        # subprocess below instead of comparing this string.
        binary = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if binary.returncode != 0:
            errors.append(f"cannot hash formal metadata from HEAD: {rel}")
        elif hashlib.sha256(binary.stdout).hexdigest() != sha256_file(path):
            errors.append(f"working-tree bytes differ from committed HEAD: {rel}")

    return str(rel)


def version(command: list[str]) -> str | None:
    code, value = capture(command)
    return value if code == 0 else None


def current_environment() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": version(["git", "--version"]),
        "node": version(["node", "--version"]),
        "npm": version(["npm", "--version"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-repo", required=True, type=Path)
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--execution-profile", required=True, type=Path)
    ap.add_argument("--formal-plan-lock", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--codex-bin", default="codex")
    args = ap.parse_args()

    source = args.source_repo.resolve()
    schedule_path = args.schedule.resolve()
    profile_path = args.execution_profile.resolve()
    plan_path = args.formal_plan_lock.resolve()
    output = args.output.resolve()
    errors: list[str] = []

    schedule = load(schedule_path)
    profile = load(profile_path)
    plan = load(plan_path)
    benchmark = load(EXPERIMENT / "BENCHMARK-LOCK.json")
    analysis = load(EXPERIMENT / "ANALYSIS-LOCK.json")

    if profile.get("status") != "frozen":
        errors.append("execution profile is not frozen")
    if schedule.get("status") != "pre-registered":
        errors.append("formal schedule is not pre-registered")
    if plan.get("status") != "frozen":
        errors.append("formal plan is not frozen")
    if schedule.get("profile_id") != profile.get("profile_id"):
        errors.append("schedule/profile ID mismatch")
    if plan.get("execution_profile_id") != profile.get("profile_id"):
        errors.append("formal plan/profile ID mismatch")
    if plan.get("execution_profile_sha256") != sha256_file(profile_path):
        errors.append("execution profile bytes differ from formal plan")
    if plan.get("schedule_sha256") != sha256_file(schedule_path):
        errors.append("schedule bytes differ from formal plan")
    if plan.get("benchmark_revision") != benchmark.get("benchmark_revision"):
        errors.append("formal plan benchmark revision mismatch")
    if plan.get("benchmark_definition_sha") != benchmark.get("definition_sha"):
        errors.append("formal plan benchmark definition mismatch")
    if plan.get("analysis_revision") != analysis.get("analysis_revision"):
        errors.append("formal plan analysis revision mismatch")
    if plan.get("analysis_definition_sha") != analysis.get("definition_sha"):
        errors.append("formal plan analysis definition mismatch")

    # The three generated pre-registration files must already be committed.
    tracked = {}
    for key, path in {
        "execution_profile": profile_path,
        "formal_schedule": schedule_path,
        "formal_plan": plan_path,
    }.items():
        tracked[key] = require_tracked_head_file(path, errors)

    code, root_status = capture(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
    )
    if code != 0:
        errors.append("cannot inspect narness-engineering Git state")
    elif root_status:
        errors.append("narness-engineering has tracked changes at formal collection start")

    code, source_status = capture(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=source,
    )
    if code != 0:
        errors.append("cannot inspect Nession Git state")
    elif source_status:
        errors.append("Nession source checkout has tracked changes at formal collection start")

    # Verify benchmark/treatment/oracle semantics before spending model budget.
    integrity = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-native-benchmark.py"),
            "--source-repo",
            str(source),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if integrity.returncode != 0:
        errors.append("benchmark integrity failed: " + integrity.stdout.strip())

    env = current_environment()
    expected_env = profile.get("environment", {})
    for key in ("python", "platform", "git", "node", "npm"):
        expected = expected_env.get(key)
        if expected is not None and env.get(key) != expected:
            errors.append(
                f"environment drift for {key}: {env.get(key)!r} != {expected!r}"
            )

    codex_path = shutil.which(args.codex_bin)
    codex_version = None
    if codex_path is None:
        errors.append(f"Codex executable not found: {args.codex_bin!r}")
    else:
        codex_version = version([args.codex_bin, "--version"])
        expected_codex = profile.get("agent", {}).get("codex_version")
        if expected_codex is not None and codex_version != expected_codex:
            errors.append(
                f"Codex CLI drift: {codex_version!r} != {expected_codex!r}"
            )

    if profile.get("agent", {}).get("harness_environment_scrubbed") is not True:
        errors.append("execution profile does not prove harness environment scrubbing")

    code, head = capture(["git", "rev-parse", "HEAD"], cwd=ROOT)
    if code != 0:
        errors.append("cannot resolve narness-engineering HEAD")
        head = None

    source_head = None
    code, source_head_value = capture(["git", "rev-parse", "HEAD"], cwd=source)
    if code == 0:
        source_head = source_head_value

    tooling_paths = {
        "runner_file_sha256": ROOT / "scripts" / "ai-native-repo-experiment.py",
        "adapter_file_sha256": ROOT / "scripts" / "ai-native-codex-adapter.py",
        "scorer_file_sha256": ROOT / "scripts" / "score-ai-native-run.py",
        "seal_file_sha256": ROOT / "scripts" / "seal-ai-native-run.py",
        "run_seal_verifier_file_sha256": ROOT / "scripts" / "verify-ai-native-run-seal.py",
        "formal_orchestrator_file_sha256": ROOT / "scripts" / "run-ai-native-formal.py",
    }
    current_tooling = {}
    for key, path in tooling_paths.items():
        actual = sha256_file(path)
        current_tooling[key] = actual
        expected = profile.get("tooling", {}).get(key)
        if expected is not None and actual != expected:
            errors.append(f"formal tooling drift for {path.name}: {actual} != {expected}")

    if errors:
        print("Formal collection readiness FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    critical = {
        "experiment_id": benchmark["experiment_id"],
        "benchmark_revision": benchmark["benchmark_revision"],
        "benchmark_definition_sha": benchmark["definition_sha"],
        "analysis_revision": analysis["analysis_revision"],
        "analysis_definition_sha": analysis["definition_sha"],
        "formal_plan_id": plan["plan_id"],
        "formal_plan_sha256": sha256_file(plan_path),
        "execution_profile_id": profile["profile_id"],
        "execution_profile_sha256": sha256_file(profile_path),
        "schedule_sha256": sha256_file(schedule_path),
        "scheduled_run_count": int(schedule["run_count"]),
        "narness_repository_sha": head,
        "nession_source_checkout_sha": source_head,
        "environment": env,
        "codex_version": codex_version,
        "tooling": current_tooling,
        "tracked_metadata": tracked,
    }

    if output.exists():
        existing = load(output)
        existing_critical = existing.get("critical")
        if existing_critical != critical:
            print("Formal collection readiness FAILED")
            print("  - current execution state differs from existing collection-start lock")
            print("  - do not resume the same formal collection from a different environment")
            return 1
        print("Formal collection readiness OK (existing collection-start lock matches)")
        print(f"  narness HEAD: {head}")
        print(f"  plan: {plan['plan_id']}")
        return 0

    record = {
        "schema_version": 1,
        "status": "frozen-at-first-formal-run",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "critical": critical,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Formal collection readiness OK")
    print(f"  collection start: {output}")
    print(f"  narness HEAD: {head}")
    print(f"  profile: {profile['profile_id']}")
    print(f"  scheduled runs: {schedule['run_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
