#!/usr/bin/env python3
"""Verify a formal run collection against the pre-registered schedule and run seals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_id_for(entry: dict[str, Any]) -> str:
    return (
        f"{entry['task_id']}-{entry['treatment']}-"
        f"{int(entry['attempt']):02d}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--execution-profile", required=True, type=Path)
    ap.add_argument("--benchmark-lock", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args()

    runs_root = args.runs_root.resolve()
    schedule_path = args.schedule.resolve()
    profile_path = args.execution_profile.resolve()
    lock_path = args.benchmark_lock.resolve()
    schedule = load(schedule_path)
    profile = load(profile_path)
    lock = load(lock_path)

    errors: list[str] = []
    missing: list[str] = []
    records: list[dict[str, Any]] = []

    if schedule.get("status") != "pre-registered":
        errors.append("schedule is not pre-registered")
    if profile.get("status") != "frozen":
        errors.append("execution profile is not frozen")
    if schedule.get("profile_id") != profile.get("profile_id"):
        errors.append("schedule/profile ID mismatch")

    entries = schedule.get("entries", [])
    expected_ids = [run_id_for(entry) for entry in entries]
    if len(expected_ids) != len(set(expected_ids)):
        errors.append("schedule contains duplicate formal run IDs")

    verifier = ROOT / "scripts" / "verify-ai-native-run-seal.py"
    for entry, run_id in zip(entries, expected_ids):
        run_dir = runs_root / run_id
        run_path = run_dir / "run.json"
        seal_path = run_dir / "seal.json"

        if not run_path.exists() or not seal_path.exists():
            missing.append(run_id)
            continue

        run = load(run_path)
        if run.get("run_id") != run_id:
            errors.append(f"{run_id}: run.json run_id mismatch")
        if run.get("task_id") != entry.get("task_id"):
            errors.append(f"{run_id}: task_id differs from schedule")
        if run.get("treatment") != entry.get("treatment"):
            errors.append(f"{run_id}: treatment differs from schedule")
        if int(run.get("attempt", -1)) != int(entry.get("attempt", -2)):
            errors.append(f"{run_id}: attempt differs from schedule")

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
        if verified.returncode != 0:
            errors.append(
                f"{run_id}: seal verification failed: "
                + verified.stdout.strip().replace("\n", " | ")
            )
            continue

        seal = load(seal_path)
        review_path = run_dir / "review.json"
        records.append({
            "sequence": int(entry["sequence"]),
            "replication": int(entry["replication"]),
            "run_id": run_id,
            "task_id": run["task_id"],
            "treatment": run["treatment"],
            "attempt": int(run["attempt"]),
            "task_success": bool(run.get("task_success")),
            "run_seal_sha256": sha256_file(seal_path),
            "review_sha256": sha256_file(review_path) if review_path.exists() else None,
        })

    unexpected: list[str] = []
    if runs_root.exists():
        expected = set(expected_ids)
        for run_path in sorted(runs_root.glob("*/run.json")):
            run_id = run_path.parent.name
            run = load(run_path)
            if run.get("admissible_for_final_analysis") and run_id not in expected:
                unexpected.append(run_id)
    if unexpected:
        errors.append(
            "unexpected sealed runs outside pre-registered schedule: "
            + ", ".join(unexpected)
        )

    if missing and not args.allow_incomplete:
        errors.append(
            f"formal collection is missing {len(missing)} scheduled runs"
        )

    collection_material = "\n".join(
        f"{row['sequence']}:{row['run_id']}:{row['run_seal_sha256']}:"
        f"{row['review_sha256'] or '-'}"
        for row in sorted(records, key=lambda row: row["sequence"])
    ).encode("utf-8")

    manifest = {
        "schema_version": 1,
        "experiment_id": lock["experiment_id"],
        "benchmark_revision": lock["benchmark_revision"],
        "benchmark_definition_sha": lock["definition_sha"],
        "execution_profile_id": profile["profile_id"],
        "schedule_sha256": sha256_file(schedule_path),
        "execution_profile_sha256": sha256_file(profile_path),
        "benchmark_lock_sha256": sha256_file(lock_path),
        "scheduled_run_count": len(entries),
        "verified_run_count": len(records),
        "missing_run_count": len(missing),
        "missing_run_ids": missing,
        "unexpected_sealed_run_ids": unexpected,
        "complete": not missing and not unexpected and not errors,
        "collection_digest_sha256": hashlib.sha256(collection_material).hexdigest(),
        "runs": sorted(records, key=lambda row: row["sequence"]),
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if errors:
        print("Formal collection verification FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Formal collection verification OK")
    print(f"  verified: {len(records)} / {len(entries)}")
    print(f"  missing: {len(missing)}")
    print(f"  digest: {manifest['collection_digest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
