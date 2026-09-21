#!/usr/bin/env python3
"""Freeze the exact execution profile and formal schedule before reportable runs."""

from __future__ import annotations

import argparse
from collections import Counter
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
    ap.add_argument("--execution-profile", required=True, type=Path)
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--benchmark-lock", required=True, type=Path)
    ap.add_argument("--analysis-lock", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--plan-id", default="formal-plan-r1")
    args = ap.parse_args()

    profile_path = args.execution_profile.resolve()
    schedule_path = args.schedule.resolve()
    benchmark_path = args.benchmark_lock.resolve()
    analysis_path = args.analysis_lock.resolve()

    profile = load(profile_path)
    schedule = load(schedule_path)
    benchmark = load(benchmark_path)
    analysis = load(analysis_path)

    if profile.get("status") != "frozen":
        raise RuntimeError("execution profile is not frozen")
    if schedule.get("status") != "pre-registered":
        raise RuntimeError("formal schedule is not pre-registered")
    if schedule.get("profile_id") != profile.get("profile_id"):
        raise RuntimeError("schedule/profile ID mismatch")
    if benchmark.get("status") != "frozen":
        raise RuntimeError("benchmark lock is not frozen")
    if analysis.get("status") != "frozen":
        raise RuntimeError("analysis lock is not frozen")

    entries = schedule.get("entries", [])
    if int(schedule.get("run_count", -1)) != len(entries):
        raise RuntimeError("schedule run_count does not match entries")

    replications = int(schedule.get("replications", 0) or 0)
    if replications not in {1, 3}:
        raise RuntimeError(f"unsupported replication count: {replications}")

    expected_tasks = [f"T{i:02d}" for i in range(1, 25)]
    expected_treatments = {"A", "B", "C"}
    by_task_treatment = Counter()
    by_task_replication: dict[tuple[str, int], list[dict[str, Any]]] = {}
    position_counts: dict[str, Counter] = {
        task: Counter() for task in expected_tasks
    }

    expected_sequence = 1
    for entry in entries:
        if int(entry.get("sequence", -1)) != expected_sequence:
            raise RuntimeError(
                f"schedule sequence is not contiguous at {expected_sequence}"
            )
        expected_sequence += 1

        task = entry.get("task_id")
        treatment = entry.get("treatment")
        replication = int(entry.get("replication", -1))
        attempt = int(entry.get("attempt", -2))
        position = int(entry.get("within_task_position", -1))

        if task not in expected_tasks:
            raise RuntimeError(f"unexpected task in schedule: {task}")
        if treatment not in expected_treatments:
            raise RuntimeError(f"unexpected treatment in schedule: {treatment}")
        if replication < 1 or replication > replications:
            raise RuntimeError(
                f"invalid replication for {task}/{treatment}: {replication}"
            )
        if attempt != replication:
            raise RuntimeError(
                f"attempt must equal replication for {task}/{treatment}: "
                f"{attempt} != {replication}"
            )
        if position not in {1, 2, 3}:
            raise RuntimeError(
                f"invalid within-task position for {task}/{treatment}: {position}"
            )

        by_task_treatment[(task, treatment)] += 1
        by_task_replication.setdefault((task, replication), []).append(entry)
        position_counts[task][(treatment, position)] += 1

    for task in expected_tasks:
        for treatment in sorted(expected_treatments):
            actual = by_task_treatment[(task, treatment)]
            if actual != replications:
                raise RuntimeError(
                    f"schedule cell count mismatch for {task}/{treatment}: "
                    f"{actual} != {replications}"
                )
        for replication in range(1, replications + 1):
            cell = by_task_replication.get((task, replication), [])
            treatments = {item.get("treatment") for item in cell}
            positions = {int(item.get("within_task_position", -1)) for item in cell}
            if len(cell) != 3 or treatments != expected_treatments or positions != {1, 2, 3}:
                raise RuntimeError(
                    f"unbalanced within-task block for {task}/replication-{replication}"
                )

        if replications == 3:
            for treatment in sorted(expected_treatments):
                for position in (1, 2, 3):
                    if position_counts[task][(treatment, position)] != 1:
                        raise RuntimeError(
                            f"Latin-square imbalance for {task}/{treatment}/position-{position}"
                        )

    run_ids = [
        f"{entry['task_id']}-{entry['treatment']}-{int(entry['attempt']):02d}"
        for entry in entries
    ]
    if len(run_ids) != len(set(run_ids)):
        raise RuntimeError("formal schedule contains duplicate run IDs")

    plan = {
        "schema_version": 1,
        "plan_id": args.plan_id,
        "status": "frozen",
        "experiment_id": benchmark["experiment_id"],
        "benchmark_revision": benchmark["benchmark_revision"],
        "benchmark_definition_sha": benchmark["definition_sha"],
        "analysis_revision": analysis["analysis_revision"],
        "analysis_definition_sha": analysis["definition_sha"],
        "execution_profile_id": profile["profile_id"],
        "execution_profile_sha256": sha256_file(profile_path),
        "schedule_sha256": sha256_file(schedule_path),
        "run_count": len(entries),
        "replications": schedule.get("replications"),
        "design": schedule.get("design"),
        "schedule_design_validation": {
            "tasks": 24,
            "treatments": 3,
            "unique_run_ids": True,
            "contiguous_sequence": True,
            "balanced_task_treatment_cells": True,
            "balanced_within_task_blocks": True,
            "latin_square_positions": replications == 3,
        },
        "freeze_rule": (
            "Any change to execution-profile or formal-schedule bytes after this "
            "lock is created invalidates this plan and requires a new formal plan."
        ),
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Frozen formal plan: {output}")
    print(f"  plan_id: {plan['plan_id']}")
    print(f"  runs: {plan['run_count']}")
    print(f"  profile sha256: {plan['execution_profile_sha256']}")
    print(f"  schedule sha256: {plan['schedule_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
