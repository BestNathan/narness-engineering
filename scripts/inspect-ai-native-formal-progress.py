#!/usr/bin/env python3
"""Inspect progress of a pre-registered formal AI-native run schedule."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_id_for(entry: dict[str, Any]) -> str:
    return f"{entry['task_id']}-{entry['treatment']}-{int(entry['attempt']):02d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--execution-profile", required=True, type=Path)
    ap.add_argument("--benchmark-lock", required=True, type=Path)
    ap.add_argument("--json-output", type=Path)
    args = ap.parse_args()

    runs_root = args.runs_root.resolve()
    schedule = load(args.schedule.resolve())
    profile = load(args.execution_profile.resolve())
    lock = load(args.benchmark_lock.resolve())
    verifier = ROOT / "scripts" / "verify-ai-native-run-seal.py"

    rows: list[dict[str, Any]] = []
    counts = Counter()
    by_treatment: dict[str, Counter] = {
        treatment: Counter() for treatment in ("A", "B", "C")
    }

    for entry in schedule.get("entries", []):
        run_id = run_id_for(entry)
        run_dir = runs_root / run_id
        state = "pending"
        detail = None

        if run_dir.exists():
            run_path = run_dir / "run.json"
            seal_path = run_dir / "seal.json"
            if not run_path.exists() or not seal_path.exists():
                state = "incomplete"
            else:
                verified = subprocess.run(
                    [
                        sys.executable,
                        str(verifier),
                        "--run-dir",
                        str(run_dir),
                        "--expected-profile-id",
                        str(profile["profile_id"]),
                        "--expected-benchmark-sha",
                        str(lock["definition_sha"]),
                    ],
                    cwd=ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                if verified.returncode == 0:
                    state = "sealed"
                    run = load(run_path)
                    detail = "success" if run.get("task_success") else "task-failed"
                else:
                    state = "tampered"
                    detail = verified.stdout.strip().replace("\n", " | ")

        counts[state] += 1
        by_treatment[entry["treatment"]][state] += 1
        rows.append({
            "sequence": int(entry["sequence"]),
            "run_id": run_id,
            "task_id": entry["task_id"],
            "treatment": entry["treatment"],
            "attempt": int(entry["attempt"]),
            "state": state,
            "detail": detail,
        })

    pending = [row for row in rows if row["state"] == "pending"]
    incomplete = [row for row in rows if row["state"] == "incomplete"]
    tampered = [row for row in rows if row["state"] == "tampered"]
    sealed = [row for row in rows if row["state"] == "sealed"]

    result = {
        "schema_version": 1,
        "scheduled": len(rows),
        "sealed": len(sealed),
        "pending": len(pending),
        "incomplete": len(incomplete),
        "tampered": len(tampered),
        "completion_fraction": (len(sealed) / len(rows)) if rows else 0.0,
        "next_pending": pending[0] if pending else None,
        "by_treatment": {
            treatment: dict(counter)
            for treatment, counter in by_treatment.items()
        },
        "runs": rows,
    }

    print("Formal collection progress")
    print(f"  sealed:     {len(sealed):3d} / {len(rows)}")
    print(f"  pending:    {len(pending):3d}")
    print(f"  incomplete: {len(incomplete):3d}")
    print(f"  tampered:   {len(tampered):3d}")
    if pending:
        row = pending[0]
        print(
            f"  next:       sequence {row['sequence']} "
            f"{row['run_id']}"
        )
    for treatment in ("A", "B", "C"):
        counter = by_treatment[treatment]
        print(
            f"  {treatment}: sealed={counter.get('sealed', 0)} "
            f"pending={counter.get('pending', 0)} "
            f"incomplete={counter.get('incomplete', 0)} "
            f"tampered={counter.get('tampered', 0)}"
        )

    if args.json_output:
        output = args.json_output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return 1 if tampered else 0


if __name__ == "__main__":
    raise SystemExit(main())
