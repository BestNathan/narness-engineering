#!/usr/bin/env python3
"""Generate a pre-registered balanced A/B/C formal run schedule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TREATMENTS = ["A", "B", "C"]
TASKS = [f"T{i:02d}" for i in range(1, 25)]


def rotate(items: list[str], n: int) -> list[str]:
    n %= len(items)
    return items[n:] + items[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replications", type=int, choices=[1, 3], required=True)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--profile-id", required=True)
    args = ap.parse_args()

    entries = []
    sequence = 0
    for replication in range(1, args.replications + 1):
        for task_index, task_id in enumerate(TASKS):
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
        "design": "balanced cyclic Latin-square order within each task",
        "entries": entries,
    }

    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} formal run entries to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
