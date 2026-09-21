#!/usr/bin/env python3
"""Generate a pre-registered balanced A/B/C formal run schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


TREATMENTS = ["A", "B", "C"]
TASKS = [f"T{i:02d}" for i in range(1, 25)]


def rotate(items: list[str], n: int) -> list[str]:
    n %= len(items)
    return items[n:] + items[:n]


def task_order(replication: int, seed: int) -> list[str]:
    """Return a deterministic pseudo-random task permutation.

    SHA-256 ordering avoids relying on language-runtime PRNG/shuffle details.
    """
    return sorted(
        TASKS,
        key=lambda task: hashlib.sha256(
            f"{seed}:{replication}:{task}".encode("utf-8")
        ).hexdigest(),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replications", type=int, choices=[1, 3], required=True)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--profile-id", required=True)
    ap.add_argument("--task-order-seed", type=int, default=20260921)
    args = ap.parse_args()

    entries = []
    sequence = 0
    task_orders: dict[str, list[str]] = {}
    for replication in range(1, args.replications + 1):
        ordered_tasks = task_order(replication, args.task_order_seed)
        task_orders[str(replication)] = ordered_tasks
        for task_id in ordered_tasks:
            task_index = TASKS.index(task_id)
            # Latin-square rotation balances treatment position by task and,
            # with three replications, by replication as well.
            order = rotate(TREATMENTS, task_index + replication - 1)
            for position, treatment in enumerate(order, start=1):
                sequence += 1
                entries.append({
                    "sequence": sequence,
                    "replication": replication,
                    "task_id": task_id,
                    "treatment": treatment,
                    "attempt": replication,
                    "within_task_position": position,
                })

    schedule = {
        "schema_version": 1,
        "status": "pre-registered",
        "profile_id": args.profile_id,
        "replications": args.replications,
        "run_count": len(entries),
        "design": (
            "deterministically permuted task blocks per replication + "
            "balanced cyclic Latin-square treatment order within each task"
        ),
        "task_order_policy": "sha256(seed:replication:task)",
        "task_order_seed": args.task_order_seed,
        "task_orders": task_orders,
        "entries": entries,
    }

    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} formal run entries to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
