#!/usr/bin/env python3
"""Smoke-test pilot evidence binding in execution-profile freezing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FREEZER = ROOT / "scripts" / "freeze-ai-native-execution-profile.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_pilot(
    root: Path,
    *,
    task: str,
    treatment: str,
    harness_sha: str,
    scorer_sha: str,
) -> Path:
    run_id = f"{task}-{treatment}-01"
    run_dir = root / run_id
    run_dir.mkdir(parents=True)

    cfg = {
        "type": "agent-config",
        "agent": "codex-cli",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "network": "disabled",
        "subagents_enabled": False,
        "web_search": "disabled",
        "harness_environment_scrubbed": True,
        "codex_version": "codex-selftest",
        "adapter_file_sha256": "adapter-selftest-sha",
    }
    (run_dir / "trace.jsonl").write_text(
        json.dumps(cfg) + "\n",
        encoding="utf-8",
    )

    environment = {
        "python": "3.selftest",
        "platform": "selftest-platform",
        "git": "git selftest",
        "node": "node-selftest",
        "npm": "npm-selftest",
        "runner_file_sha256": "runner-selftest-sha",
        "harness_repository_sha": harness_sha,
    }
    run = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task,
        "treatment": treatment,
        "attempt": 1,
        "trace_present": True,
        "trace_complete": True,
        "agent_exit_ok": True,
        "task_success": treatment != "A",
        "environment": environment,
        "commands": {
            "setup": [{"command": "cd web && npm ci", "exit_code": 0}],
            "agent": {
                "command": "synthetic-codex",
                "exit_code": 0,
                "timed_out": False,
                "timeout_seconds": 1800,
            },
        },
    }
    write_json(run_dir / "run.json", run)

    metrics = {
        "search_calls": 1,
        "glob_calls": 1,
        "resolver_calls": 0 if treatment == "A" else 1,
        "files_read": 2,
        "unique_files_read": 2,
        "irrelevant_files_read": 0,
        "navigation_precision": 1.0,
        "navigation_recall": 1.0,
        "first_hit_correct": True,
        "time_to_first_relevant_artifact_ms": 100,
        "time_to_first_edit_ms": 200,
        "navigation_events_before_first_edit": 3,
        "search_calls_before_first_edit": 1,
        "files_read_before_first_edit": 2,
        "important_artifacts_missed_count": 0,
        "out_of_scope_edit_count": 0,
        "validation_failures": 0,
        "patch_count": 1,
        "repair_loops": 0,
        "input_tokens": 1000,
        "output_tokens": 200,
    }
    score = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task,
        "treatment": treatment,
        "scorer_file_sha256": scorer_sha,
        "metrics": metrics,
    }
    write_json(run_dir / "score.json", score)

    for name, content in {
        "codex.raw.jsonl": '{"type":"turn.completed"}\n',
        "final.diff": f"diff --git a/{task} b/{task}\n",
        "prompt.txt": f"synthetic prompt {task}\n",
        "git-status.txt": f" M {task}\n",
        "agent.stdout.log": "",
        "agent.stderr.log": "",
        "codex.stderr.log": "",
    }.items():
        (run_dir / name).write_text(content, encoding="utf-8")

    return run_dir


def freeze(pilots: list[Path], output: Path) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(FREEZER),
    ]
    for pilot in pilots:
        cmd.extend(["--pilot", str(pilot)])
    cmd.extend(
        [
            "--output",
            str(output),
            "--profile-id",
            "selftest-profile",
        ]
    )
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="narness-profile-selftest-") as tmp:
        root = Path(tmp)
        scorer_sha = "same-scorer-sha"
        harness_sha = "same-harness-sha"
        pilots = [
            make_pilot(
                root,
                task="T05",
                treatment="A",
                harness_sha=harness_sha,
                scorer_sha=scorer_sha,
            ),
            make_pilot(
                root,
                task="T08",
                treatment="B",
                harness_sha=harness_sha,
                scorer_sha=scorer_sha,
            ),
            make_pilot(
                root,
                task="T20",
                treatment="C",
                harness_sha=harness_sha,
                scorer_sha=scorer_sha,
            ),
        ]

        profile_a_path = root / "profile-a.json"
        first = freeze(pilots, profile_a_path)
        if first.returncode != 0:
            print(first.stdout)
            raise RuntimeError("valid pilot set did not freeze")

        profile_a = json.loads(profile_a_path.read_text(encoding="utf-8"))
        digest_a = profile_a["pilot_set_digest_sha256"]
        assert len(digest_a) == 64
        assert len(profile_a["source_pilots"]) == 3
        assert {
            row["run_id"] for row in profile_a["source_pilots"]
        } == {"T05-A-01", "T08-B-01", "T20-C-01"}
        for row in profile_a["source_pilots"]:
            assert "trace.jsonl" in row["artifacts"]
            assert "codex.raw.jsonl" in row["artifacts"]
            assert "final.diff" in row["artifacts"]

        # Editing any pilot evidence must change the derived profile identity.
        with (pilots[1] / "agent.stdout.log").open("a", encoding="utf-8") as fh:
            fh.write("changed pilot evidence\n")
        profile_b_path = root / "profile-b.json"
        second = freeze(pilots, profile_b_path)
        if second.returncode != 0:
            print(second.stdout)
            raise RuntimeError("modified but internally valid pilot set did not freeze")
        profile_b = json.loads(profile_b_path.read_text(encoding="utf-8"))
        assert profile_b["pilot_set_digest_sha256"] != digest_a

        # Pilot harness drift must fail instead of being silently averaged away.
        run_c_path = pilots[2] / "run.json"
        run_c = json.loads(run_c_path.read_text(encoding="utf-8"))
        run_c["environment"]["harness_repository_sha"] = "different-harness-sha"
        write_json(run_c_path, run_c)
        profile_c_path = root / "profile-c.json"
        third = freeze(pilots, profile_c_path)
        assert third.returncode != 0
        assert "pilot harness repository SHA differs" in third.stdout

    print("Execution-profile pilot provenance selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
