#!/usr/bin/env python3
"""Freeze a formal execution profile from the three non-reportable pilot runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_PILOTS = {("T05", "A"), ("T08", "B"), ("T20", "C")}
REQUIRED_METRICS = [
    "search_calls",
    "glob_calls",
    "resolver_calls",
    "files_read",
    "unique_files_read",
    "irrelevant_files_read",
    "navigation_precision",
    "navigation_recall",
    "first_hit_correct",
    "time_to_first_relevant_artifact_ms",
    "time_to_first_edit_ms",
    "navigation_events_before_first_edit",
    "search_calls_before_first_edit",
    "files_read_before_first_edit",
    "important_artifacts_missed_count",
    "out_of_scope_edit_count",
    "validation_failures",
    "patch_count",
    "repair_loops",
    "input_tokens",
    "output_tokens",
]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def one_agent_config(run_dir: Path) -> dict[str, Any]:
    events = load_jsonl(run_dir / "trace.jsonl")
    configs = [e for e in events if e.get("type") == "agent-config"]
    if len(configs) != 1:
        raise RuntimeError(f"{run_dir}: expected exactly one agent-config event")
    return configs[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="append", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--profile-id", default="codex-gpt-5.6-sol-high-r1")
    args = ap.parse_args()

    if len(args.pilot) != 3:
        raise RuntimeError("exactly three pilot run directories are required")

    rows: list[dict[str, Any]] = []
    observed = set()
    for run_dir in [p.resolve() for p in args.pilot]:
        run = load(run_dir / "run.json")
        score = load(run_dir / "score.json")
        cfg = one_agent_config(run_dir)
        key = (run.get("task_id"), run.get("treatment"))
        observed.add(key)

        if not run.get("trace_present") or not run.get("trace_complete"):
            raise RuntimeError(f"{run_dir}: trace is incomplete")
        if run.get("runner_error"):
            raise RuntimeError(f"{run_dir}: runner error: {run['runner_error']}")
        agent = run.get("commands", {}).get("agent") or {}
        if not run.get("agent_exit_ok") or agent.get("timed_out"):
            raise RuntimeError(f"{run_dir}: agent did not complete cleanly")
        metrics = score.get("metrics", {})
        for metric in REQUIRED_METRICS:
            if metric not in metrics:
                raise RuntimeError(f"{run_dir}: scorer omitted metric {metric}")
        if metrics.get("input_tokens") is None or metrics.get("output_tokens") is None:
            raise RuntimeError(f"{run_dir}: model usage was not captured")
        if metrics.get("patch_count", 0) <= 0:
            raise RuntimeError(f"{run_dir}: no edit event captured")

        rows.append({
            "run_dir": run_dir,
            "run": run,
            "score": score,
            "agent": agent,
            "cfg": cfg,
        })

    if observed != EXPECTED_PILOTS:
        raise RuntimeError(f"pilot matrix mismatch: {sorted(observed)}")

    first = rows[0]
    agent_keys = [
        "agent",
        "model",
        "reasoning_effort",
        "network",
        "subagents_enabled",
        "web_search",
        "codex_version",
        "adapter_file_sha256",
    ]
    env_keys = ["python", "platform", "git", "node", "npm", "runner_file_sha256"]

    agent_profile = {key: first["cfg"].get(key) for key in agent_keys}
    environment = {
        key: first["run"].get("environment", {}).get(key)
        for key in env_keys
    }
    setup_commands = [
        item.get("command")
        for item in first["run"].get("commands", {}).get("setup", [])
    ]
    timeout = first["agent"].get("timeout_seconds")
    scorer_file_sha256 = first["score"].get("scorer_file_sha256")
    pilot_repository_sha = first["run"].get("environment", {}).get("harness_repository_sha")

    for row in rows[1:]:
        for key, expected in agent_profile.items():
            if row["cfg"].get(key) != expected:
                raise RuntimeError(
                    f"pilot execution drift in agent.{key}: "
                    f"{row['cfg'].get(key)!r} != {expected!r}"
                )
        for key, expected in environment.items():
            actual = row["run"].get("environment", {}).get(key)
            if actual != expected:
                raise RuntimeError(
                    f"pilot execution drift in environment.{key}: "
                    f"{actual!r} != {expected!r}"
                )
        actual_setup = [
            item.get("command")
            for item in row["run"].get("commands", {}).get("setup", [])
        ]
        if actual_setup != setup_commands:
            raise RuntimeError("pilot setup commands differ")
        if row["agent"].get("timeout_seconds") != timeout:
            raise RuntimeError("pilot agent timeout differs")
        if row["score"].get("scorer_file_sha256") != scorer_file_sha256:
            raise RuntimeError("pilot scorer file identity differs")

    profile = {
        "schema_version": 1,
        "profile_id": args.profile_id,
        "status": "frozen",
        "source_pilots": [
            {
                "run_id": row["run"]["run_id"],
                "task_id": row["run"]["task_id"],
                "treatment": row["run"]["treatment"],
            }
            for row in rows
        ],
        "agent": agent_profile,
        "environment": environment,
        "agent_timeout_seconds": timeout,
        "setup_commands": setup_commands,
        "tooling": {
            "runner_file_sha256": environment.get("runner_file_sha256"),
            "adapter_file_sha256": agent_profile.get("adapter_file_sha256"),
            "scorer_file_sha256": scorer_file_sha256,
        },
        "pilot_repository_sha": pilot_repository_sha,
        "required_metrics": REQUIRED_METRICS,
        "notes": {
            "pilot_task_success_required": False,
            "formal_task_success_required_for_admissibility": False,
            "network_policy": "offline coding agent; dependency install occurs before agent",
        },
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Frozen execution profile: {output}")
    print(f"  profile_id: {profile['profile_id']}")
    print(f"  codex_version: {agent_profile.get('codex_version')}")
    print(f"  pilot repository SHA: {pilot_repository_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
