#!/usr/bin/env python3
"""
Isolated runner for the AI-native repository experiment.

The runner deliberately knows nothing about a specific coding agent. It creates
an isolated Git worktree, applies a frozen task fixture, invokes an operator-
supplied agent command, runs hidden acceptance/verification commands, and writes
an auditable JSON record.

Python stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


def run(
    cmd: str | list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    shell: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = {
        "command": cmd if isinstance(cmd, str) else shlex.join(cmd),
        "exit_code": proc.returncode,
        "started_at_unix": started,
        "duration_ms": round((time.time() - started) * 1000),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {result['command']}\n{proc.stderr}"
        )
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def render(value: str, values: dict[str, str]) -> str:
    for key, replacement in values.items():
        value = value.replace("{" + key + "}", replacement)
    return value


def git(repo: Path, *args: str, check: bool = True) -> dict[str, Any]:
    return run(["git", *args], cwd=repo, check=check)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", required=True, type=Path)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--treatments", required=True, type=Path)
    parser.add_argument("--treatment", required=True, choices=["A", "B", "C"])
    parser.add_argument("--agent-cmd", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument(
        "--keep-worktree",
        action="store_true",
        help="Keep the isolated worktree for debugging after the run.",
    )
    args = parser.parse_args()

    source_repo = args.source_repo.resolve()
    task_path = args.task.resolve()
    treatments_path = args.treatments.resolve()
    output_root = args.output_dir.resolve()

    task = load_json(task_path)
    treatments = load_json(treatments_path)
    treatment = treatments["treatments"][args.treatment]

    task_id = task["task_id"]
    run_id = f"{task_id}-{args.treatment}-{args.attempt:02d}"
    run_dir = output_root / run_id
    if run_dir.exists():
        raise RuntimeError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)

    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task_id,
        "treatment": args.treatment,
        "attempt": args.attempt,
        "admissible_for_final_analysis": False,
        "treatment_sha": treatment["sha"],
        "task_manifest": str(task_path),
        "started_at_unix": time.time(),
        "commands": {
            "fixture_preflight": [],
            "agent": None,
            "oracle_install": [],
            "acceptance": [],
            "verification": [],
            "mutation_checks": [],
        },
    }

    tmp_root = Path(tempfile.mkdtemp(prefix=f"narness-{run_id}-"))
    worktree = tmp_root / "worktree"
    values = {
        "source_repo": str(source_repo),
        "worktree": str(worktree),
        "run_dir": str(run_dir),
        "task_id": task_id,
        "treatment": args.treatment,
    }

    try:
        # Never reuse an existing checkout or branch: each run gets detached HEAD.
        git(source_repo, "worktree", "add", "--detach", str(worktree), treatment["sha"])

        # Apply the treatment-specific fixture, if one exists.
        fixture = task.get("fixtures", {}).get(args.treatment, {})
        patch = fixture.get("patch")
        if patch:
            patch_path = (task_path.parent / patch).resolve()
            values["fixture_patch"] = str(patch_path)
            record["fixture_patch"] = str(patch_path)
            applied = run(
                ["git", "apply", "--whitespace=nowarn", str(patch_path)],
                cwd=worktree,
            )
            record["commands"]["fixture_preflight"].append(applied)
            if applied["exit_code"] != 0:
                raise RuntimeError("fixture patch failed")

        for command in fixture.get("preflight_commands", []):
            result = run(render(command, values), cwd=worktree, shell=True)
            record["commands"]["fixture_preflight"].append(result)
            if result["exit_code"] != 0:
                raise RuntimeError("fixture preflight failed")

        prompt = task["prompt"].strip() + "\n"
        prompt_path = run_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        values["prompt_file"] = str(prompt_path)

        # The operator chooses the agent/harness. The exact command is recorded.
        # Treatment-specific generic capability exposure is appended by the runner.
        extra_instruction = treatment.get("agent_instruction")
        if extra_instruction:
            prompt_path.write_text(
                prompt + "\n" + extra_instruction.strip() + "\n",
                encoding="utf-8",
            )

        env = os.environ.copy()
        trace_path = run_dir / "trace.jsonl"
        env.update(
            {
                "NARNESS_RUN_ID": run_id,
                "NARNESS_TASK_ID": task_id,
                "NARNESS_TREATMENT": args.treatment,
                "NARNESS_WORKTREE": str(worktree),
                "NARNESS_RUN_DIR": str(run_dir),
                "NARNESS_PROMPT_FILE": str(prompt_path),
                "NARNESS_TRACE_FILE": str(trace_path),
            }
        )

        agent_cmd = render(args.agent_cmd, values)
        agent = run(agent_cmd, cwd=worktree, env=env, shell=True)
        record["commands"]["agent"] = agent
        (run_dir / "agent.stdout.log").write_text(agent["stdout"], encoding="utf-8")
        (run_dir / "agent.stderr.log").write_text(agent["stderr"], encoding="utf-8")

        # Hidden oracles are materialized only after the coding agent exits.
        # This keeps the oracle out of the agent's discoverable worktree while
        # still making local/reproducible acceptance possible.
        installed_oracles: list[Path] = []
        oracle = task.get("oracle", {})
        oracle_ref = oracle.get("ref")
        for item in oracle.get("files", []):
            if not oracle_ref:
                raise RuntimeError("oracle.files requires oracle.ref")
            source = item["source"]
            destination = worktree / item["destination"]
            shown = git(source_repo, "show", f"{oracle_ref}:{source}", check=False)
            record["commands"]["oracle_install"].append({
                "source": source,
                "destination": str(destination),
                "git_show_exit_code": shown["exit_code"],
            })
            if shown["exit_code"] != 0:
                raise RuntimeError(f"failed to materialize hidden oracle: {source}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(shown["stdout"], encoding="utf-8")
            installed_oracles.append(destination)

        # Hidden acceptance is deliberately outside the agent prompt.
        acceptance_ok = True
        for command in task.get("acceptance_commands", []):
            result = run(render(command, values), cwd=worktree, shell=True)
            record["commands"]["acceptance"].append(result)
            acceptance_ok = acceptance_ok and result["exit_code"] == 0

        # Remove hidden oracle files before repository verification/diff capture.
        # They are experiment infrastructure, not part of the agent's change.
        for oracle_path in installed_oracles:
            oracle_path.unlink(missing_ok=True)

        verification_ok = True
        for command in task.get("verification_commands", []):
            result = run(render(command, values), cwd=worktree, shell=True)
            record["commands"]["verification"].append(result)
            verification_ok = verification_ok and result["exit_code"] == 0

        mutation_checks_ok = True
        mutation_checks = list(task.get("mutation_checks", []))
        mutation_checks.extend(
            task.get("mutation_checks_by_treatment", {}).get(args.treatment, [])
        )
        for index, mutation in enumerate(mutation_checks, start=1):
            patch_path = run_dir / f"mutation-{index:02d}.patch"
            mutation_ref = mutation.get("ref")
            patch_source = mutation.get("patch_source")
            local_patch = mutation.get("patch")
            if local_patch:
                source_path = (task_path.parent / local_patch).resolve()
                patch_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
            elif mutation_ref and patch_source:
                shown = git(source_repo, "show", f"{mutation_ref}:{patch_source}", check=False)
                if shown["exit_code"] != 0:
                    raise RuntimeError(f"failed to materialize mutation patch: {patch_source}")
                patch_path.write_text(shown["stdout"], encoding="utf-8")
            else:
                raise RuntimeError("mutation check requires patch or ref + patch_source")

            applied = run(
                ["git", "apply", "--whitespace=nowarn", str(patch_path)],
                cwd=worktree,
            )
            mutation_record: dict[str, Any] = {
                "name": mutation.get("name", f"mutation-{index}"),
                "ref": mutation_ref,
                "patch_source": patch_source,
                "patch": local_patch,
                "apply_exit_code": applied["exit_code"],
                "commands": [],
                "killed": False,
            }
            record["commands"]["mutation_checks"].append(mutation_record)
            if applied["exit_code"] != 0:
                mutation_checks_ok = False
                continue

            expected = mutation.get("expected", "failure")
            observed_failure = False
            observed_success = True
            for command in mutation.get("commands", []):
                result = run(render(command, values), cwd=worktree, shell=True)
                mutation_record["commands"].append(result)
                observed_failure = observed_failure or result["exit_code"] != 0
                observed_success = observed_success and result["exit_code"] == 0

            mutation_record["killed"] = (
                observed_failure if expected == "failure" else observed_success
            )
            mutation_checks_ok = mutation_checks_ok and mutation_record["killed"]

            reverted = run(
                ["git", "apply", "-R", "--whitespace=nowarn", str(patch_path)],
                cwd=worktree,
            )
            mutation_record["revert_exit_code"] = reverted["exit_code"]
            if reverted["exit_code"] != 0:
                raise RuntimeError(f"failed to revert mutation: {patch_source}")

        diff = git(worktree, "diff", "--binary", check=False)
        (run_dir / "final.diff").write_text(diff["stdout"], encoding="utf-8")
        status = git(worktree, "status", "--porcelain=v1", check=False)
        (run_dir / "git-status.txt").write_text(status["stdout"], encoding="utf-8")

        record["trace_path"] = str(trace_path)
        record["trace_present"] = trace_path.exists() and trace_path.stat().st_size > 0
        record["agent_exit_ok"] = agent["exit_code"] == 0
        record["acceptance_ok"] = acceptance_ok
        record["verification_ok"] = verification_ok
        record["mutation_checks_ok"] = mutation_checks_ok
        record["task_success"] = acceptance_ok and verification_ok and mutation_checks_ok
        record["finished_at_unix"] = time.time()
        record["wall_time_ms"] = round(
            (record["finished_at_unix"] - record["started_at_unix"]) * 1000
        )

        # Formal admissibility is set by post-run review after trace/relevance scoring.
        record["admissible_for_final_analysis"] = False

        (run_dir / "run.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return 0 if record["task_success"] else 2

    except Exception as exc:
        record["runner_error"] = repr(exc)
        record["finished_at_unix"] = time.time()
        (run_dir / "run.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"runner error: {exc}", file=sys.stderr)
        return 3
    finally:
        if args.keep_worktree:
            print(f"kept worktree: {worktree}", file=sys.stderr)
        else:
            # Remove through git first so source-repo worktree metadata is cleaned.
            if worktree.exists():
                run(
                    ["git", "worktree", "remove", "--force", str(worktree)],
                    cwd=source_repo,
                )
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
