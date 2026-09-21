#!/usr/bin/env python3
"""Execute a pre-registered formal AI-native benchmark schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], *, cwd: Path = ROOT, check: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", shlex.join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, text=True, check=check)


def capture(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def ensure_clean(repo: Path) -> None:
    tracked = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo,
        text=True,
    ).strip()
    if tracked:
        raise RuntimeError(f"tracked working tree is not clean: {repo}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-repo", required=True, type=Path)
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--execution-profile", required=True, type=Path)
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--start-sequence", type=int)
    ap.add_argument("--end-sequence", type=int)
    args = ap.parse_args()

    source = args.source_repo.resolve()
    schedule = load(args.schedule.resolve())
    profile = load(args.execution_profile.resolve())
    runs_root = args.runs_root.resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    if profile.get("status") != "frozen":
        raise RuntimeError("execution profile is not frozen")
    if schedule.get("status") != "pre-registered":
        raise RuntimeError("formal schedule is not pre-registered")
    if schedule.get("profile_id") != profile.get("profile_id"):
        raise RuntimeError("schedule/profile ID mismatch")

    ensure_clean(ROOT)
    tooling = profile.get("tooling", {})
    tool_paths = {
        "runner_file_sha256": ROOT / "scripts" / "ai-native-repo-experiment.py",
        "adapter_file_sha256": ROOT / "scripts" / "ai-native-codex-adapter.py",
        "scorer_file_sha256": ROOT / "scripts" / "score-ai-native-run.py",
    }
    for key, tool_path in tool_paths.items():
        expected = tooling.get(key)
        actual = file_sha256(tool_path)
        if expected and actual != expected:
            raise RuntimeError(
                f"formal tooling mismatch for {tool_path.name}: {actual} != {expected}"
            )

    # Refresh only references; every actual run still checks out immutable SHAs.
    run(
        [
            "git",
            "fetch",
            "origin",
            "research/ai-native-repo-a-baseline",
            "research/ai-native-repo-b-semantic-index",
            "research/ai-native-repo-c-agent-native",
            "research/ai-native-ci-base",
        ],
        cwd=source,
        check=True,
    )

    # Gate semantic drift and treatment/fixture/oracle integrity before spending
    # any model budget.
    run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-native-benchmark.py"),
            "--source-repo",
            str(source),
        ],
        check=True,
    )

    lock_path = EXPERIMENT / "BENCHMARK-LOCK.json"
    gold_path = EXPERIMENT / "runner" / "gold.json"
    treatments_path = EXPERIMENT / "runner" / "treatments.json"

    model = profile["agent"]["model"]
    effort = profile["agent"]["reasoning_effort"]
    timeout = profile["agent_timeout_seconds"]
    adapter = ROOT / "scripts" / "ai-native-codex-adapter.py"
    agent_cmd = (
        f"{shlex.quote(sys.executable)} {shlex.quote(str(adapter))} "
        f"--model {shlex.quote(str(model))} --effort {shlex.quote(str(effort))}"
    )

    entries = schedule["entries"]
    selected = []
    for entry in entries:
        seq = int(entry["sequence"])
        if args.start_sequence is not None and seq < args.start_sequence:
            continue
        if args.end_sequence is not None and seq > args.end_sequence:
            continue
        selected.append(entry)

    print(
        f"Formal schedule: {len(selected)} selected / {len(entries)} total entries",
        flush=True,
    )

    for entry in selected:
        task = entry["task_id"]
        treatment = entry["treatment"]
        attempt = int(entry["attempt"])
        run_id = f"{task}-{treatment}-{attempt:02d}"
        run_dir = runs_root / run_id

        if run_dir.exists():
            run_json = run_dir / "run.json"
            if run_json.exists() and load(run_json).get("admissible_for_final_analysis"):
                print(f"SKIP sealed run {run_id}", flush=True)
                continue
            raise RuntimeError(
                f"run directory already exists but is not sealed: {run_dir}"
            )

        runner_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "ai-native-repo-experiment.py"),
            "--source-repo",
            str(source),
            "--task",
            str(EXPERIMENT / "runner" / "manifests" / f"{task}.json"),
            "--treatments",
            str(treatments_path),
            "--treatment",
            treatment,
            "--attempt",
            str(attempt),
            "--agent-timeout-seconds",
            str(timeout),
            "--agent-cmd",
            agent_cmd,
            "--output-dir",
            str(runs_root),
        ]
        for setup in profile.get("setup_commands", []):
            runner_cmd.extend(["--setup-cmd", setup])

        print(
            f"\n=== sequence {entry['sequence']}: {task}/{treatment} rep={attempt} ===",
            flush=True,
        )
        runner = run(runner_cmd)
        if runner.returncode == 3:
            raise RuntimeError(f"runner infrastructure failure: {run_id}")
        if runner.returncode not in (0, 2):
            raise RuntimeError(f"unexpected runner exit {runner.returncode}: {run_id}")

        run(
            [
                sys.executable,
                str(ROOT / "scripts" / "score-ai-native-run.py"),
                "--run-dir",
                str(run_dir),
                "--gold",
                str(gold_path),
                "--treatment",
                treatment,
                "--update-run-json",
            ],
            check=True,
        )

        sealed = run(
            [
                sys.executable,
                str(ROOT / "scripts" / "seal-ai-native-run.py"),
                "--run-dir",
                str(run_dir),
                "--benchmark-lock",
                str(lock_path),
                "--definition-repo",
                str(ROOT),
                "--execution-profile",
                str(args.execution_profile.resolve()),
            ],
        )
        if sealed.returncode != 0:
            raise RuntimeError(
                f"run completed but failed formal admissibility seal: {run_id}"
            )

    print("Selected formal schedule entries completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
