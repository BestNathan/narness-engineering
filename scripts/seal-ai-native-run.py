#!/usr/bin/env python3
"""Seal one formal AI-native repository run after deterministic admissibility checks."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def artifact_digests(run_dir: Path) -> dict[str, str]:
    names = {
        "run.json",
        "score.json",
        "trace.jsonl",
        "final.diff",
        "git-status.txt",
        "prompt.txt",
        "agent.stdout.log",
        "agent.stderr.log",
        "codex.raw.jsonl",
        "codex.stderr.log",
        "claude.raw.jsonl",
        "claude.stderr.log",
    }
    names.update(path.name for path in run_dir.glob("mutation-*.patch"))
    return {
        name: sha256_file(run_dir / name)
        for name in sorted(names)
        if (run_dir / name).exists()
    }


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
        if "exit_code" not in item:
            errors.append(f"{name}: command has no recorded exit code: {item.get('command')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--benchmark-lock", required=True, type=Path)
    ap.add_argument("--analysis-lock", required=True, type=Path)
    ap.add_argument("--definition-repo", required=True, type=Path)
    ap.add_argument("--execution-profile", required=True, type=Path)
    ap.add_argument("--formal-plan-lock", required=True, type=Path)
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    lock = load(args.benchmark_lock.resolve())
    analysis_lock = load(args.analysis_lock.resolve())
    profile_path = args.execution_profile.resolve()
    profile = load(profile_path)
    plan_path = args.formal_plan_lock.resolve()
    plan = load(plan_path)
    formal_plan_sha256 = sha256_file(plan_path)
    run_path = run_dir / "run.json"
    score_path = run_dir / "score.json"
    trace_path = run_dir / "trace.jsonl"

    errors: list[str] = []
    for path in (
        run_path,
        score_path,
        trace_path,
        run_dir / "final.diff",
        run_dir / "prompt.txt",
    ):
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
    if plan.get("status") != "frozen":
        errors.append("formal plan is not frozen")
    if plan.get("execution_profile_id") != profile.get("profile_id"):
        errors.append("formal plan/profile ID mismatch")
    if plan.get("execution_profile_sha256") != sha256_file(profile_path):
        errors.append("execution profile bytes differ from formal plan")
    if plan.get("benchmark_revision") != lock.get("benchmark_revision"):
        errors.append("formal plan benchmark revision mismatch")
    if plan.get("benchmark_definition_sha") != lock.get("definition_sha"):
        errors.append("formal plan benchmark definition mismatch")
    if plan.get("analysis_revision") != analysis_lock.get("analysis_revision"):
        errors.append("formal plan analysis revision mismatch")
    if plan.get("analysis_definition_sha") != analysis_lock.get("definition_sha"):
        errors.append("formal plan analysis definition mismatch")
    if task_id not in {f"T{i:02d}" for i in range(1, 25)}:
        errors.append(f"unexpected formal task: {task_id}")
    expected_treatment_sha = lock.get("treatments", {}).get(treatment)
    if run.get("treatment_sha") != expected_treatment_sha:
        errors.append(
            f"treatment SHA mismatch: {run.get('treatment_sha')} != {expected_treatment_sha}"
        )

    frozen_task: dict[str, Any] | None = None
    if task_id:
        manifest_rel = (
            "docs/topics/agent-native-repository-architecture/research/experiments/"
            f"{lock['experiment_id']}/runner/manifests/{task_id}.json"
        )
        frozen_task_bytes = git_show(
            args.definition_repo.resolve(), definition_sha, manifest_rel
        )
        expected_task_hash = sha256_bytes(frozen_task_bytes)
        if run.get("task_manifest_sha256") != expected_task_hash:
            errors.append("task manifest hash does not match frozen definition")
        frozen_task = json.loads(frozen_task_bytes.decode("utf-8"))

    treatments_rel = (
        "docs/topics/agent-native-repository-architecture/research/experiments/"
        f"{lock['experiment_id']}/runner/treatments.json"
    )
    frozen_treatments_bytes = git_show(
        args.definition_repo.resolve(), definition_sha, treatments_rel
    )
    expected_treatments_hash = sha256_bytes(frozen_treatments_bytes)
    if run.get("treatments_manifest_sha256") != expected_treatments_hash:
        errors.append("treatments manifest hash does not match frozen definition")
    frozen_treatments = json.loads(frozen_treatments_bytes.decode("utf-8"))

    if frozen_task is not None and treatment in frozen_treatments.get("treatments", {}):
        expected_prompt = frozen_task["prompt"].strip() + "\n"
        extra_instruction = frozen_treatments["treatments"][treatment].get(
            "agent_instruction"
        )
        if extra_instruction:
            expected_prompt = (
                expected_prompt + "\n" + extra_instruction.strip() + "\n"
            )
        expected_prompt_hash = sha256_bytes(expected_prompt.encode("utf-8"))
        actual_prompt_hash = sha256_bytes((run_dir / "prompt.txt").read_bytes())
        if run.get("prompt_sha256") != expected_prompt_hash:
            errors.append("recorded prompt hash does not match frozen task/treatment prompt")
        if actual_prompt_hash != expected_prompt_hash:
            errors.append("prompt.txt does not match frozen task/treatment prompt")

    if run.get("runner_error"):
        errors.append(f"runner_error present: {run['runner_error']}")
    agent = run.get("commands", {}).get("agent") or {}
    if not agent:
        errors.append("agent command record is missing")
    if not run.get("trace_present") or not run.get("trace_complete"):
        errors.append("structured trace is absent or was not scored")
    # Task/acceptance/verification/mutation failures are benchmark outcomes,
    # not admissibility failures. Excluding them would inflate success rates.
    commands = run.get("commands", {})
    check_command_list(commands.get("acceptance", []), name="acceptance", errors=errors)
    check_command_list(commands.get("verification", []), name="verification", errors=errors)

    if frozen_task is not None:
        fixture = frozen_task.get("fixtures", {}).get(treatment, {})
        expected_fixture_steps = (
            (1 if fixture.get("patch") else 0)
            + len(fixture.get("preflight_commands", []))
        )
        actual_fixture_steps = commands.get("fixture_preflight", [])
        if len(actual_fixture_steps) != expected_fixture_steps:
            errors.append(
                f"fixture-preflight record count mismatch: "
                f"{len(actual_fixture_steps)} != {expected_fixture_steps}"
            )
        for item in actual_fixture_steps:
            if item.get("exit_code") != 0:
                errors.append("fixture preflight contains a non-zero result")

        expected_oracle_files = frozen_task.get("oracle", {}).get("files", [])
        actual_oracle_installs = commands.get("oracle_install", [])
        if len(actual_oracle_installs) != len(expected_oracle_files):
            errors.append(
                f"oracle install count mismatch: "
                f"{len(actual_oracle_installs)} != {len(expected_oracle_files)}"
            )

        expected_mutations = list(frozen_task.get("mutation_checks", []))
        expected_mutations.extend(
            frozen_task.get("mutation_checks_by_treatment", {}).get(treatment, [])
        )
        actual_mutations = commands.get("mutation_checks", [])
        if len(actual_mutations) != len(expected_mutations):
            errors.append(
                f"mutation-check record count mismatch: "
                f"{len(actual_mutations)} != {len(expected_mutations)}"
            )
        for index, item in enumerate(actual_mutations):
            if "apply_exit_code" not in item:
                errors.append(f"mutation check {index + 1} has no apply exit code")
            if "killed" not in item:
                errors.append(f"mutation check {index + 1} has no killed result")
            if item.get("apply_exit_code") == 0 and "revert_exit_code" not in item:
                errors.append(f"mutation check {index + 1} has no revert exit code")

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
    expected_scorer_hash = profile.get("tooling", {}).get("scorer_file_sha256")
    if expected_scorer_hash is not None and score.get("scorer_file_sha256") != expected_scorer_hash:
        errors.append("scorer file identity differs from execution profile")
    if score.get("task_id") != task_id or score.get("treatment") != treatment:
        errors.append("score/run task or treatment mismatch")

    metrics = score.get("metrics", {})
    for metric in profile.get("required_metrics", []):
        if metrics.get(metric) is None:
            # A hard wall-clock timeout is a valid benchmark outcome. The
            # interrupted agent may not emit final usage/accounting events.
            if not agent.get("timed_out"):
                errors.append(f"required metric missing: {metric}")

    trace_events = [
        json.loads(raw)
        for raw in trace_path.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]
    forbidden_evaluation_fragments = (
        "runner/gold.json",
        "runner/oracle.json",
        "BENCHMARK-LOCK.json",
        "ANALYSIS-LOCK.json",
        "__research_",
        ".research/ai-native/acceptance",
    )
    usage_events = [
        event for event in trace_events if event.get("type") == "usage"
    ]
    if len(usage_events) != 1:
        errors.append(
            "expected exactly one usage event for one fresh agent task; "
            f"captured {len(usage_events)}"
        )

    for event in trace_events:
        if event.get("type") not in {"command", "search", "glob", "read"}:
            continue
        serialized = json.dumps(event, sort_keys=True)
        leaked = [
            fragment
            for fragment in forbidden_evaluation_fragments
            if fragment in serialized
        ]
        if leaked:
            errors.append(
                "coding-agent trace accessed hidden evaluation infrastructure: "
                + ", ".join(leaked)
            )
            break
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
            "permission_profile",
            "provider_policy",
            "filesystem_read_scope",
            "bash_network",
            "git_metadata",
            "shell_environment_allowlist",
            "harness_environment_scrubbed",
            "codex_version",
            "claude_version",
            "bubblewrap_version",
            "sandbox_runtime_version",
            "container_image_id",
            "proxy_image_id",
            "upstream_base_url",
            "max_turns",
            "command_mapper_sha256",
            "raw_trace_file",
            "adapter_file_sha256",
        ):
            expected = profile.get("agent", {}).get(key)
            if expected is not None and agent_config.get(key) != expected:
                errors.append(
                    f"agent profile mismatch for {key}: "
                    f"{agent_config.get(key)!r} != {expected!r}"
                )

    if profile.get("agent", {}).get("agent") == "claude-code":
        if not (run_dir / "claude.raw.jsonl").is_file():
            errors.append("Claude raw stream is missing")

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
        "analysis_revision": analysis_lock.get("analysis_revision"),
        "analysis_definition_sha": analysis_lock.get("definition_sha"),
        "execution_profile_id": profile["profile_id"],
        "formal_plan_id": plan.get("plan_id"),
        "formal_plan_sha256": formal_plan_sha256,
        "sealed": True,
        "agent_exit_ok": run.get("agent_exit_ok"),
        "agent_timed_out": bool(agent.get("timed_out")),
        "task_success": run.get("task_success"),
    }
    run_path.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    seal = {
        "schema_version": 1,
        "run_id": run["run_id"],
        "task_id": run["task_id"],
        "treatment": run["treatment"],
        "benchmark_revision": lock["benchmark_revision"],
        "benchmark_definition_sha": definition_sha,
        "analysis_revision": analysis_lock.get("analysis_revision"),
        "analysis_definition_sha": analysis_lock.get("definition_sha"),
        "execution_profile_id": profile["profile_id"],
        "formal_plan_id": plan.get("plan_id"),
        "formal_plan_sha256": formal_plan_sha256,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifact_digests(run_dir),
    }
    (run_dir / "seal.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Formal run admissible")
    print(f"  run: {run['run_id']}")
    print(f"  profile: {profile['profile_id']}")
    print(f"  seal: {run_dir / 'seal.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

