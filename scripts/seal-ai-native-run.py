#!/usr/bin/env python3
"""Seal one formal AI-native repository run after deterministic admissibility checks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(repo: Path, ref: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
    return proc.stdout


def check_command_list(
    commands: list[dict[str, Any]],
    *,
    name: str,
    errors: list[str],
) -> None:
    if not commands:
        errors.append(f"{name}: no command records")
        return
    for item in commands:
        if item.get("exit_code") != 0:
            errors.append(f"{name}: command failed: {item.get('command')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--benchmark-lock", required=True, type=Path)
    ap.add_argument("--definition-repo", required=True, type=Path)
    ap.add_argument("--execution-profile", required=True, type=Path)
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    lock = load(args.benchmark_lock.resolve())
    profile = load(args.execution_profile.resolve())
    run_path = run_dir / "run.json"
    score_path = run_dir / "score.json"
    trace_path = run_dir / "trace.jsonl"

    errors: list[str] = []
    for path in (run_path, score_path, trace_path, run_dir / "final.diff"):
        if not path.exists():
            errors.append(f"missing required artifact: {path.name}")
    if errors:
        print("\n".join(f"ERROR: {x}" for x in errors))
        return 1

    run = load(run_path)
    score = load(score_path)
    task_id = run.get("task_id")
    treatment = run.get("treatment")
    definition_sha = lock["definition_sha"]

    if lock.get("status") != "frozen":
        errors.append("benchmark lock is not frozen")
    if task_id not in {f"T{i:02d}" for i in range(1, 25)}:
        errors.append(f"unexpected formal task: {task_id}")
    expected_treatment_sha = lock.get("treatments", {}).get(treatment)
    if run.get("treatment_sha") != expected_treatment_sha:
        errors.append(
            f"treatment SHA mismatch: {run.get('treatment_sha')} != {expected_treatment_sha}"
        )

    if task_id:
        manifest_rel = (
            "docs/topics/agent-native-repository-architecture/research/experiments/"
            f"{lock['experiment_id']}/runner/manifests/{task_id}.json"
        )
        expected_task_hash = sha256_bytes(
            git_show(args.definition_repo.resolve(), definition_sha, manifest_rel)
        )
        if run.get("task_manifest_sha256") != expected_task_hash:
            errors.append("task manifest hash does not match frozen definition")

    treatments_rel = (
        "docs/topics/agent-native-repository-architecture/research/experiments/"
        f"{lock['experiment_id']}/runner/treatments.json"
    )
    expected_treatments_hash = sha256_bytes(
        git_show(args.definition_repo.resolve(), definition_sha, treatments_rel)
    )
    if run.get("treatments_manifest_sha256") != expected_treatments_hash:
        errors.append("treatments manifest hash does not match frozen definition")

    if run.get("runner_error"):
        errors.append(f"runner_error present: {run['runner_error']}")
    if not run.get("agent_exit_ok"):
        errors.append("agent process did not exit successfully")
    agent = run.get("commands", {}).get("agent") or {}
    if agent.get("timed_out"):
        errors.append("agent exceeded the formal time budget")
    if not run.get("trace_present") or not run.get("trace_complete"):
        errors.append("structured trace is absent or was not scored")
    if not run.get("task_success"):
        errors.append("task_success is false")
    if not run.get("acceptance_ok"):
        errors.append("hidden acceptance failed")
    if not run.get("verification_ok"):
        errors.append("repository verification failed")
    if not run.get("mutation_checks_ok"):
        errors.append("required mutation-strength checks failed")

    commands = run.get("commands", {})
    check_command_list(commands.get("acceptance", []), name="acceptance", errors=errors)
    check_command_list(commands.get("verification", []), name="verification", errors=errors)

    agent_end = float(agent.get("started_at_unix", 0)) + float(agent.get("duration_ms", 0)) / 1000.0
    for install in commands.get("oracle_install", []):
        installed_at = install.get("installed_at_unix")
        if installed_at is None or float(installed_at) < agent_end:
            errors.append("hidden oracle timing cannot prove post-agent installation")

    final_diff = (run_dir / "final.diff").read_text(encoding="utf-8")
    if "__research_" in final_diff or ".research/ai-native/acceptance" in final_diff:
        errors.append("hidden oracle material leaked into final diff")

    if score.get("run_id") != run.get("run_id"):
        errors.append("score/run run_id mismatch")
    if score.get("task_id") != task_id or score.get("treatment") != treatment:
        errors.append("score/run task or treatment mismatch")

    metrics = score.get("metrics", {})
    for metric in profile.get("required_metrics", []):
        if metrics.get(metric) is None:
            errors.append(f"required metric missing: {metric}")

    trace_events = [
        json.loads(raw)
        for raw in trace_path.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]
    agent_config = next((e for e in trace_events if e.get("type") == "agent-config"), None)
    if not agent_config:
        errors.append("agent-config trace event missing")
    else:
        for key in (
            "agent",
            "model",
            "reasoning_effort",
            "network",
            "subagents_enabled",
            "web_search",
            "codex_version",
            "adapter_repository_sha",
        ):
            expected = profile.get("agent", {}).get(key)
            if expected is not None and agent_config.get(key) != expected:
                errors.append(
                    f"agent profile mismatch for {key}: "
                    f"{agent_config.get(key)!r} != {expected!r}"
                )

    env = run.get("environment", {})
    for key, expected in profile.get("environment", {}).items():
        if expected is not None and env.get(key) != expected:
            errors.append(f"environment mismatch for {key}: {env.get(key)!r} != {expected!r}")

    expected_timeout = profile.get("agent_timeout_seconds")
    if expected_timeout is not None and agent.get("timeout_seconds") != expected_timeout:
        errors.append("agent timeout differs from execution profile")

    expected_setup = profile.get("setup_commands")
    if expected_setup is not None:
        actual_setup = [item.get("command") for item in commands.get("setup", [])]
        if actual_setup != expected_setup:
            errors.append(f"setup commands mismatch: {actual_setup!r} != {expected_setup!r}")

    if errors:
        print("Formal run NOT admissible")
        for error in errors:
            print(f"  - {error}")
        return 1

    run["admissible_for_final_analysis"] = True
    run["admissibility"] = {
        "benchmark_revision": lock["benchmark_revision"],
        "benchmark_definition_sha": definition_sha,
        "execution_profile_id": profile["profile_id"],
        "sealed": True,
    }
    run_path.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Formal run admissible")
    print(f"  run: {run['run_id']}")
    print(f"  profile: {profile['profile_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
