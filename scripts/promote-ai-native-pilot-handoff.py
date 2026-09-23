#!/usr/bin/env python3
"""Promote a validated non-reportable pilot handoff into formal freeze metadata."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
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
RUNNER_DIR = EXPERIMENT / "runner"
FREEZE_FILES = (
    "execution-profile-r2.json",
    "formal-schedule-r2.json",
    "formal-plan-r2.lock.json",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_workflow_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in {
            "workflow_run_id",
            "repository_sha",
            "runner_os",
            "codex_version",
            "created_at",
        }:
            out[key] = value
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff-dir", required=True, type=Path)
    ap.add_argument(
        "--allow-identical-existing",
        action="store_true",
        help="Allow destination freeze files that already exist with identical bytes.",
    )
    args = ap.parse_args()

    handoff = args.handoff_dir.resolve()
    validation_path = handoff / "promotion-validation.json"

    validator = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-native-pilot-handoff.py"),
            "--handoff-dir",
            str(handoff),
            "--output",
            str(validation_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(validator.stdout, end="")
    if validator.returncode != 0:
        raise RuntimeError("pilot handoff validation failed; nothing was promoted")

    validation = load(validation_path)
    lock_path = EXPERIMENT / "EXECUTION-PREPILOT-LOCK.json"
    lock = load(lock_path)

    promoted: dict[str, str] = {}
    for name in FREEZE_FILES:
        source = handoff / name
        destination = RUNNER_DIR / name
        if destination.exists():
            if sha256_file(destination) != sha256_file(source):
                raise RuntimeError(
                    f"destination already exists with different bytes: {destination}"
                )
            if not args.allow_identical_existing:
                raise RuntimeError(
                    f"destination already exists; rerun with "
                    f"--allow-identical-existing only if this is intentional: "
                    f"{destination}"
                )
        else:
            shutil.copy2(source, destination)
        promoted[name] = sha256_file(destination)

    profile = load(RUNNER_DIR / "execution-profile-r2.json")
    schedule = load(RUNNER_DIR / "formal-schedule-r2.json")
    plan = load(RUNNER_DIR / "formal-plan-r2.lock.json")

    workflow_metadata = parse_workflow_metadata(
        handoff / "workflow-metadata.txt"
    )
    promotion = {
        "schema_version": 1,
        "status": "pilot-handoff-validated-and-promoted",
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "execution_prepilot_revision": lock["execution_prepilot_revision"],
        "execution_prepilot_repository_sha": lock["repository_sha"],
        "execution_prepilot_lock_sha256": sha256_file(lock_path),
        "profile_id": profile["profile_id"],
        "pilot_set_digest_sha256": profile["pilot_set_digest_sha256"],
        "formal_run_count": schedule["run_count"],
        "formal_replications": schedule["replications"],
        "formal_plan_id": plan["plan_id"],
        "freeze_files": dict(sorted(promoted.items())),
        "handoff_validation_sha256": sha256_file(validation_path),
        "workflow": workflow_metadata or None,
        "notes": {
            "pilot_runs_reportable": False,
            "pilot_task_success_required": False,
            "formal_collection_may_start_only_after_commit": True,
        },
    }

    promotion_path = RUNNER_DIR / "PILOT-FREEZE-r2.json"
    if promotion_path.exists():
        raise RuntimeError(
            f"refusing to overwrite existing pilot promotion record: {promotion_path}"
        )
    promotion_path.write_text(
        json.dumps(promotion, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Pilot handoff promoted")
    print(f"  profile: {profile['profile_id']}")
    print(f"  evidence digest: {profile['pilot_set_digest_sha256']}")
    print(f"  formal runs: {schedule['run_count']}")
    print(f"  promotion record: {promotion_path}")
    print()
    print("NEXT: review and commit these four files:")
    for name in FREEZE_FILES:
        print(f"  {RUNNER_DIR / name}")
    print(f"  {promotion_path}")
    print("Do not start formal collection before that commit exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
