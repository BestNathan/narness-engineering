#!/usr/bin/env python3
"""
Isolated runner for the AI-native repository experiment.

The runner deliberately knows nothing about a specific coding agent. It creates
an isolated single-ref Git repository, applies a frozen task fixture, invokes an
operator-supplied agent command, runs hidden acceptance/verification commands,
and writes an auditable JSON record.

Python stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shlex
import signal
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
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=timeout_seconds is not None,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = proc.communicate()
        else:
            proc.kill()
            stdout, stderr = proc.communicate()

    result = {
        "command": cmd if isinstance(cmd, str) else shlex.join(cmd),
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "started_at_unix": started,
        "duration_ms": round((time.time() - started) * 1000),
        "stdout": stdout,
        "stderr": stderr,
    }
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {result['command']}\n{stderr}"
        )
    return result


def probe_command(cmd: list[str], *, cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def render(value: str, values: dict[str, str]) -> str:
    for key, replacement in values.items():
        value = value.replace("{" + key + "}", replacement)
    return value


def git(repo: Path, *args: str, check: bool = True) -> dict[str, Any]:
    return run(["git", *args], cwd=repo, check=check)


def create_isolated_checkout(
    source_repo: Path,
    destination: Path,
    commit_sha: str,
) -> None:
    """Fetch only one frozen ref and its ancestry into a standalone repository.

    A linked Git worktree shares the source repository object database and refs,
    which would let a coding agent inspect research-only descendant/sibling
    commits such as treatment construction or hidden-oracle history. This
    checkout intentionally has its own object database and no remote.
    """
    destination.mkdir(parents=True)
    git(destination, "init", "--quiet")
    source_url = source_repo.resolve().as_uri()

    fetched = run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "fetch",
            "--no-tags",
            "--force",
            source_url,
            commit_sha,
        ],
        cwd=destination,
    )
    if fetched["exit_code"] != 0:
        raise RuntimeError(
            "isolated treatment fetch failed: " + fetched["stderr"]
        )

    git(destination, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    actual = probe_command(["git", "rev-parse", "HEAD"], cwd=destination)
    if actual != commit_sha:
        raise RuntimeError(
            f"isolated checkout resolved unexpected HEAD: {actual} != {commit_sha}"
        )

    # Do not leave the source checkout path or fetch ref as agent-visible Git
    # metadata. There is intentionally no configured remote.
    for name in ("FETCH_HEAD", "ORIG_HEAD"):
        candidate = destination / ".git" / name
        if candidate.exists():
            candidate.unlink()

    alternates = destination / ".git" / "objects" / "info" / "alternates"
    if alternates.exists():
        raise RuntimeError(
            "isolated checkout unexpectedly shares an object database"
        )
    remotes = probe_command(["git", "remote"], cwd=destination)
    if remotes:
        raise RuntimeError(
            f"isolated checkout unexpectedly has remotes: {remotes}"
        )


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
        "--agent-timeout-seconds",
        type=float,
        default=1800,
        help="Wall-clock limit for the coding agent process. Default: 1800 seconds.",
    )
    parser.add_argument(
        "--setup-cmd",
        action="append",
        default=[],
        help="Repeatable environment-setup command run before the agent (for example npm ci).",
    )
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

    harness_root = Path(__file__).resolve().parents[1]
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task_id,
        "treatment": args.treatment,
        "attempt": args.attempt,
        "admissible_for_final_analysis": False,
        "treatment_sha": treatment["sha"],
        "task_manifest": str(task_path),
        "task_manifest_sha256": sha256_file(task_path),
        "treatments_manifest": str(treatments_path),
        "treatments_manifest_sha256": sha256_file(treatments_path),
        "started_at_unix": time.time(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "git": probe_command(["git", "--version"], cwd=source_repo),
            "node": probe_command(["node", "--version"], cwd=source_repo),
            "npm": probe_command(["npm", "--version"], cwd=source_repo),
            "harness_repository_sha": probe_command(["git", "rev-parse", "HEAD"], cwd=harness_root),
            "runner_file_sha256": sha256_file(Path(__file__).resolve()),
            "checkout_isolation": "single-ref-standalone-git-no-remote",
            "harness_repository_dirty": bool(
                probe_command(["git", "status", "--porcelain"], cwd=harness_root)
            ),
        },
        "commands": {
            "setup": [],
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
        # Never expose the source repository's refs/object database to the agent.
        create_isolated_checkout(source_repo, worktree, treatment["sha"])

        for command in args.setup_cmd:
            result = run(render(command, values), cwd=worktree, shell=True)
            record["commands"]["setup"].append(result)
            if result["exit_code"] != 0:
                raise RuntimeError("environment setup failed")

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
        record["prompt_sha256"] = sha256_file(prompt_path)

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
        agent = run(
            agent_cmd,
            cwd=worktree,
            env=env,
            shell=True,
            timeout_seconds=args.agent_timeout_seconds,
        )
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
                "installed_at_unix": time.time(),
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

        status = git(worktree, "status", "--porcelain=v1", check=False)
        (run_dir / "git-status.txt").write_text(status["stdout"], encoding="utf-8")

        # `git diff` omits untracked files. Mark them intent-to-add in this
        # disposable worktree so final.diff captures newly created source/tests
        # without staging their contents as a real commit.
        untracked: list[str] = []
        for line in status["stdout"].splitlines():
            if line.startswith("?? "):
                untracked.append(line[3:])
        if untracked:
            git(worktree, "add", "-N", "--", *untracked, check=False)

        diff = git(worktree, "diff", "--binary", check=False)
        (run_dir / "final.diff").write_text(diff["stdout"], encoding="utf-8")

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
            # Standalone checkout has no source-repository worktree metadata.
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
