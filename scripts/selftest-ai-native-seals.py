#!/usr/bin/env python3
"""End-to-end smoke test for formal run sealing and collection verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "seal-selftest"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def proc(
    cmd: list[str],
    *,
    cwd: Path = ROOT,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != expected:
        print(result.stdout)
        raise RuntimeError(
            f"expected exit {expected}, got {result.returncode}: {' '.join(cmd)}"
        )
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="narness-seal-selftest-") as tmp:
        root = Path(tmp)

        # Build a tiny frozen definition repository so the real sealer can
        # verify the task manifest, treatment manifest, and exact prompt bytes.
        definition = root / "definition"
        manifest_dir = (
            definition
            / "docs/topics/agent-native-repository-architecture/research/experiments"
            / EXPERIMENT_ID
            / "runner/manifests"
        )
        manifest_dir.mkdir(parents=True)
        runner_dir = manifest_dir.parent

        task = {
            "schema_version": 1,
            "task_id": "T01",
            "prompt": "Do the synthetic task.",
            "fixtures": {"A": {}, "B": {}, "C": {}},
            "acceptance_commands": ["true"],
            "verification_commands": ["true"],
        }
        treatments = {
            "schema_version": 1,
            "treatments": {
                "A": {"name": "A", "sha": "subject-a", "agent_instruction": None},
                "B": {"name": "B", "sha": "subject-b", "agent_instruction": None},
                "C": {"name": "C", "sha": "subject-c", "agent_instruction": None},
            },
        }
        task_path = manifest_dir / "T01.json"
        treatments_path = runner_dir / "treatments.json"
        task_path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        treatments_path.write_text(
            json.dumps(treatments, indent=2) + "\n",
            encoding="utf-8",
        )

        proc(["git", "init"], cwd=definition)
        proc(["git", "config", "user.email", "seal-selftest@example.invalid"], cwd=definition)
        proc(["git", "config", "user.name", "Narness Seal Selftest"], cwd=definition)
        proc(["git", "add", "."], cwd=definition)
        proc(["git", "commit", "-m", "frozen definition"], cwd=definition)
        definition_sha = proc(["git", "rev-parse", "HEAD"], cwd=definition).stdout.strip()

        benchmark_lock = {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "benchmark_revision": 1,
            "status": "frozen",
            "definition_sha": definition_sha,
            "treatments": {
                "A": "subject-a",
                "B": "subject-b",
                "C": "subject-c",
            },
        }
        lock_path = root / "BENCHMARK-LOCK.json"
        lock_path.write_text(
            json.dumps(benchmark_lock, indent=2) + "\n",
            encoding="utf-8",
        )

        profile_id = "seal-selftest-profile"
        profile = {
            "schema_version": 1,
            "profile_id": profile_id,
            "status": "frozen",
            "agent": {},
            "environment": {},
            "agent_timeout_seconds": 60,
            "setup_commands": [],
            "tooling": {},
            "required_metrics": [],
        }
        profile_path = root / "execution-profile.json"
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

        schedule = {
            "schema_version": 1,
            "status": "pre-registered",
            "profile_id": profile_id,
            "replications": 1,
            "run_count": 1,
            "design": "selftest",
            "entries": [{
                "sequence": 1,
                "replication": 1,
                "task_id": "T01",
                "treatment": "A",
                "attempt": 1,
                "within_task_position": 1,
            }],
        }
        schedule_path = root / "schedule.json"
        schedule_path.write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
        analysis_lock = {
            "schema_version": 1,
            "analysis_revision": 2,
            "status": "frozen",
            "definition_sha": "analysis-definition-sha",
        }
        analysis_path = root / "ANALYSIS-LOCK.json"
        analysis_path.write_text(
            json.dumps(analysis_lock, indent=2) + "\n",
            encoding="utf-8",
        )
        formal_plan_path = root / "formal-plan.lock.json"
        formal_plan = {
            "schema_version": 1,
            "plan_id": "selftest-plan",
            "status": "frozen",
            "experiment_id": EXPERIMENT_ID,
            "benchmark_revision": 1,
            "benchmark_definition_sha": definition_sha,
            "analysis_revision": analysis_lock["analysis_revision"],
            "analysis_definition_sha": analysis_lock["definition_sha"],
            "execution_profile_id": profile_id,
            "execution_profile_sha256": sha(profile_path),
            "schedule_sha256": sha(schedule_path),
            "run_count": 1,
            "replications": 1,
            "design": "selftest",
        }
        formal_plan_path.write_text(
            json.dumps(formal_plan, indent=2) + "\n",
            encoding="utf-8",
        )
        formal_plan_sha256 = sha(formal_plan_path)

        runs = root / "runs"
        run_dir = runs / "T01-A-01"
        run_dir.mkdir(parents=True)

        prompt = "Do the synthetic task.\n"
        (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        (run_dir / "trace.jsonl").write_text(
            '{"type":"agent-config"}\n',
            encoding="utf-8",
        )
        (run_dir / "final.diff").write_text("diff --git synthetic\n", encoding="utf-8")
        (run_dir / "git-status.txt").write_text(" M synthetic\n", encoding="utf-8")
        (run_dir / "agent.stdout.log").write_text("", encoding="utf-8")
        (run_dir / "agent.stderr.log").write_text("", encoding="utf-8")

        score = {
            "schema_version": 1,
            "run_id": "T01-A-01",
            "task_id": "T01",
            "treatment": "A",
            "metrics": {},
        }
        (run_dir / "score.json").write_text(
            json.dumps(score, indent=2) + "\n",
            encoding="utf-8",
        )

        run_json = {
            "schema_version": 1,
            "run_id": "T01-A-01",
            "task_id": "T01",
            "treatment": "A",
            "attempt": 1,
            "treatment_sha": "subject-a",
            "task_manifest_sha256": sha(task_path),
            "treatments_manifest_sha256": sha(treatments_path),
            "prompt_sha256": sha_bytes(prompt.encode("utf-8")),
            "trace_present": True,
            "trace_complete": True,
            "agent_exit_ok": True,
            "task_success": True,
            "acceptance_ok": True,
            "verification_ok": True,
            "mutation_checks_ok": True,
            "admissible_for_final_analysis": False,
            "environment": {
                "harness_repository_sha": "selftest-harness-sha",
            },
            "commands": {
                "setup": [],
                "fixture_preflight": [],
                "agent": {
                    "command": "synthetic-agent",
                    "exit_code": 0,
                    "started_at_unix": 100.0,
                    "duration_ms": 1000,
                    "timeout_seconds": 60,
                },
                "oracle_install": [],
                "acceptance": [{"command": "true", "exit_code": 0}],
                "verification": [{"command": "true", "exit_code": 0}],
                "mutation_checks": [],
            },
        }
        (run_dir / "run.json").write_text(
            json.dumps(run_json, indent=2) + "\n",
            encoding="utf-8",
        )

        sealer = ROOT / "scripts" / "seal-ai-native-run.py"
        verifier = ROOT / "scripts" / "verify-ai-native-run-seal.py"

        proc([
            sys.executable,
            str(sealer),
            "--run-dir",
            str(run_dir),
            "--benchmark-lock",
            str(lock_path),
            "--analysis-lock",
            str(analysis_path),
            "--definition-repo",
            str(definition),
            "--execution-profile",
            str(profile_path),
            "--formal-plan-lock",
            str(formal_plan_path),
        ])
        assert (run_dir / "seal.json").exists()

        proc([
            sys.executable,
            str(verifier),
            "--run-dir",
            str(run_dir),
            "--expected-profile-id",
            profile_id,
            "--expected-benchmark-sha",
            definition_sha,
            "--expected-formal-plan-sha256",
            formal_plan_sha256,
            "--expected-analysis-sha",
            analysis_lock["definition_sha"],
        ])

        # Tampering after seal creation must be detectable.
        original_score = (run_dir / "score.json").read_text(encoding="utf-8")
        (run_dir / "score.json").write_text(
            '{"metrics":{"tampered":true}}\n',
            encoding="utf-8",
        )
        proc([
            sys.executable,
            str(verifier),
            "--run-dir",
            str(run_dir),
            "--expected-profile-id",
            profile_id,
            "--expected-benchmark-sha",
            definition_sha,
            "--expected-formal-plan-sha256",
            formal_plan_sha256,
            "--expected-analysis-sha",
            analysis_lock["definition_sha"],
        ], expected=1)
        (run_dir / "score.json").write_text(original_score, encoding="utf-8")

        # The complete scheduled collection should also verify and obtain one
        # deterministic collection digest.
        collection_start = runs / "_collection" / "collection-start.json"
        collection_start.parent.mkdir(parents=True, exist_ok=True)
        collection_start.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "frozen-at-first-formal-run",
                    "created_at": "selftest",
                    "critical": {
                        "formal_plan_sha256": formal_plan_sha256,
                        "execution_profile_sha256": sha(profile_path),
                        "schedule_sha256": sha(schedule_path),
                        "benchmark_definition_sha": definition_sha,
                        "analysis_definition_sha": analysis_lock["definition_sha"],
                        "narness_repository_sha": "selftest-harness-sha",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        collection = ROOT / "scripts" / "verify-ai-native-collection.py"
        manifest = root / "collection-manifest.json"
        proc([
            sys.executable,
            str(collection),
            "--runs-root",
            str(runs),
            "--schedule",
            str(schedule_path),
            "--execution-profile",
            str(profile_path),
            "--benchmark-lock",
            str(lock_path),
            "--analysis-lock",
            str(analysis_path),
            "--formal-plan-lock",
            str(formal_plan_path),
            "--output",
            str(manifest),
        ])

        value = json.loads(manifest.read_text(encoding="utf-8"))
        assert value["complete"] is True
        assert value["verified_run_count"] == 1
        assert len(value["collection_digest_sha256"]) == 64

        archiver = ROOT / "scripts" / "archive-ai-native-raw-runs.py"
        archive_a = root / "raw-a.zip"
        archive_b = root / "raw-b.zip"
        for archive in (archive_a, archive_b):
            proc([
                sys.executable,
                str(archiver),
                "--runs-root",
                str(runs),
                "--collection-manifest",
                str(manifest),
                "--output",
                str(archive),
            ])
        assert sha(archive_a) == sha(archive_b)
        archive_manifest = json.loads(
            (root / "raw-a.zip.manifest.json").read_text(encoding="utf-8")
        )
        assert archive_manifest["collection_digest_sha256"] == value["collection_digest_sha256"]
        assert archive_manifest["archive_sha256"] == sha(archive_a)

    print("Run sealer / tamper verification / collection seal / archive selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
