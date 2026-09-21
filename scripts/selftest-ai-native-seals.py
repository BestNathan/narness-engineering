#!/usr/bin/env python3
"""Smoke-test tamper-evident per-run and collection seals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != expected:
        print(proc.stdout)
        raise RuntimeError(
            f"expected exit {expected}, got {proc.returncode}: {' '.join(cmd)}"
        )
    return proc


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="narness-seal-selftest-") as tmp:
        root = Path(tmp)
        runs = root / "runs"
        run_dir = runs / "T01-A-01"
        run_dir.mkdir(parents=True)

        benchmark_sha = "benchmark-definition-sha"
        profile_id = "selftest-profile"
        run_json = {
            "run_id": "T01-A-01",
            "task_id": "T01",
            "treatment": "A",
            "attempt": 1,
            "task_success": True,
            "admissible_for_final_analysis": True,
            "admissibility": {
                "sealed": True,
                "benchmark_definition_sha": benchmark_sha,
                "execution_profile_id": profile_id,
            },
        }
        (run_dir / "run.json").write_text(json.dumps(run_json), encoding="utf-8")
        (run_dir / "score.json").write_text('{"metrics":{}}\n', encoding="utf-8")
        (run_dir / "trace.jsonl").write_text('{"type":"agent-config"}\n', encoding="utf-8")
        (run_dir / "final.diff").write_text("diff\n", encoding="utf-8")
        (run_dir / "prompt.txt").write_text("task\n", encoding="utf-8")

        artifacts = {
            name: sha(run_dir / name)
            for name in ("run.json", "score.json", "trace.jsonl", "final.diff", "prompt.txt")
        }
        seal = {
            "schema_version": 1,
            "run_id": "T01-A-01",
            "task_id": "T01",
            "treatment": "A",
            "benchmark_revision": 1,
            "benchmark_definition_sha": benchmark_sha,
            "execution_profile_id": profile_id,
            "sealed_at": "selftest",
            "artifacts": artifacts,
        }
        (run_dir / "seal.json").write_text(json.dumps(seal), encoding="utf-8")

        verifier = ROOT / "scripts" / "verify-ai-native-run-seal.py"
        run([
            sys.executable, str(verifier),
            "--run-dir", str(run_dir),
            "--expected-profile-id", profile_id,
            "--expected-benchmark-sha", benchmark_sha,
        ])

        original_score = (run_dir / "score.json").read_text(encoding="utf-8")
        (run_dir / "score.json").write_text('{"metrics":{"tampered":true}}\n', encoding="utf-8")
        run([
            sys.executable, str(verifier),
            "--run-dir", str(run_dir),
            "--expected-profile-id", profile_id,
            "--expected-benchmark-sha", benchmark_sha,
        ], expected=1)
        (run_dir / "score.json").write_text(original_score, encoding="utf-8")

        schedule = {
            "schema_version": 1,
            "status": "pre-registered",
            "profile_id": profile_id,
            "replications": 1,
            "run_count": 1,
            "entries": [{
                "sequence": 1,
                "replication": 1,
                "task_id": "T01",
                "treatment": "A",
                "attempt": 1,
                "within_task_position": 1,
            }],
        }
        profile = {
            "schema_version": 1,
            "status": "frozen",
            "profile_id": profile_id,
        }
        lock = {
            "schema_version": 1,
            "experiment_id": "selftest",
            "benchmark_revision": 1,
            "definition_sha": benchmark_sha,
        }
        (root / "schedule.json").write_text(json.dumps(schedule), encoding="utf-8")
        (root / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
        (root / "lock.json").write_text(json.dumps(lock), encoding="utf-8")

        collection = ROOT / "scripts" / "verify-ai-native-collection.py"
        manifest = root / "collection.json"
        run([
            sys.executable, str(collection),
            "--runs-root", str(runs),
            "--schedule", str(root / "schedule.json"),
            "--execution-profile", str(root / "profile.json"),
            "--benchmark-lock", str(root / "lock.json"),
            "--output", str(manifest),
        ])
        value = json.loads(manifest.read_text(encoding="utf-8"))
        assert value["complete"] is True
        assert value["verified_run_count"] == 1
        assert len(value["collection_digest_sha256"]) == 64

    print("Run/collection seal selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
