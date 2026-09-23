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


def scrub_secrets(env: dict[str, str]) -> dict[str, str]:
    """Remove credentials from controller-side setup/preflight subprocesses."""
    result = dict(env)
    secret_names = {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "OPENAI_API_KEY",
        "CODEX_ACCESS_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
    }
    for name in secret_names:
        result.pop(name, None)
    return result


def collect_dependency_mounts(worktree: Path) -> list[tuple[Path, Path]]:
    """Find setup-produced dependency trees that remain read-only after setup."""
    mounts: list[tuple[Path, Path]] = []
    for root, dirs, _ in os.walk(worktree):
        if ".git" in dirs:
            dirs.remove(".git")
        if "node_modules" in dirs:
            source = Path(root) / "node_modules"
            if source.is_dir() and not source.is_symlink():
                mounts.append((source, source.relative_to(worktree)))
            dirs.remove("node_modules")
    return mounts


def safe_write_beneath(root: Path, relative: str, content: str) -> Path:
    """Write a controller-owned file without following agent-created symlinks."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
        raise RuntimeError(f"unsafe workspace-relative path: {relative!r}")
    flags = os.O_RDONLY | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(root, flags)
    try:
        for part in rel.parts[:-1]:
            try:
                os.mkdir(part, 0o755, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, flags | nofollow, dir_fd=fd)
            os.close(fd)
            fd = child
        out = os.open(
            rel.parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | nofollow,
            0o600,
            dir_fd=fd,
        )
        try:
            os.write(out, content.encode("utf-8"))
        finally:
            os.close(out)
    finally:
        os.close(fd)
    return root / rel


def ensure_directory_beneath(root: Path, relative: Path) -> None:
    """Create a mount target while refusing symlink traversal."""
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise RuntimeError(f"unsafe dependency path: {relative}")
    flags = os.O_RDONLY | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(root, flags)
    try:
        for part in relative.parts:
            try:
                os.mkdir(part, 0o755, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, flags | nofollow, dir_fd=fd)
            os.close(fd)
            fd = child
    finally:
        os.close(fd)


def validation_sandbox_command(
    workspace: Path,
    command: str,
    dependency_mounts: list[tuple[Path, Path]],
) -> tuple[list[str], dict[str, str]]:
    """Run post-agent code with no host filesystem, secrets, or network."""
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        raise RuntimeError("bubblewrap is required for post-agent validation")
    workspace = workspace.resolve(strict=True)
    if not (workspace / ".git").is_dir() or (workspace / ".git").is_symlink():
        raise RuntimeError("validation workspace must be a standalone Git checkout")

    argv = [
        bwrap,
        "--unshare-all",
        "--unshare-user",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--disable-userns",
    ]
    for runtime in ("/usr", "/bin", "/sbin", "/lib", "/lib64"):
        path = Path(runtime)
        if path.is_symlink():
            argv += ["--symlink", os.readlink(path), runtime]
        elif path.exists():
            argv += ["--ro-bind", runtime, runtime]

    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node runtime is required for validation")
    node_root = Path(node).resolve().parent.parent
    if node_root != Path("/usr"):
        if not str(node_root).startswith("/opt/hostedtoolcache/node/"):
            raise RuntimeError(
                "Validation requires /usr Node or the GitHub setup-node runtime"
            )
        argv += ["--ro-bind", str(node_root), str(node_root)]

    argv += [
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--tmpfs", "/home",
        "--dir", "/home/validator",
        "--dir", "/home/validator/.cache",
        "--bind", str(workspace), "/workspace",
        "--ro-bind", str(workspace / ".git"), "/workspace/.git",
    ]
    for source, relative in dependency_mounts:
        ensure_directory_beneath(workspace, relative)
        argv += [
            "--ro-bind",
            str(source.resolve(strict=True)),
            "/workspace/" + relative.as_posix(),
        ]
    argv += ["--chdir", "/workspace", "--", "/bin/bash", "-lc", command]
    clean = {
        "HOME": "/home/validator",
        "XDG_CONFIG_HOME": "/home/validator/.config",
        "XDG_CACHE_HOME": "/home/validator/.cache",
        "TMPDIR": "/tmp",
        "TMP": "/tmp",
        "TEMP": "/tmp",
        "PATH": str(node_root / "bin") + ":/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "SHELL": "/bin/bash",
        "USER": "validator",
        "CI": "1",
    }
    return argv, clean


def run_validation_sandbox(
    workspace: Path,
    command: str,
    dependency_mounts: list[tuple[Path, Path]],
) -> dict[str, Any]:
    argv, env = validation_sandbox_command(workspace, command, dependency_mounts)
    result = run(argv, cwd=workspace, env=env)
    result["sandbox_command"] = result["command"]
    result["command"] = command
    result["isolation"] = "bubblewrap-no-network-clean-env-fresh-checkout"
    return result


def prepare_validation_workspace(
    source_repo: Path,
    treatment_sha: str,
    final_diff: Path,
    destination: Path,
) -> Path:
    create_isolated_checkout(source_repo, destination, treatment_sha)
    if final_diff.stat().st_size:
        applied = run(
            ["git", "apply", "--whitespace=nowarn", str(final_diff)],
            cwd=destination,
        )
        if applied["exit_code"] != 0:
            raise RuntimeError(
                "failed to reproduce agent patch in validation workspace: "
                + applied["stderr"]
            )
    return destination


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
            "validation_isolation": "fresh-checkout-bubblewrap-no-network-clean-env",
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
    record["worktree"] = str(worktree)
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

        controller_env = scrub_secrets(os.environ)
        for command in args.setup_cmd:
            result = run(
                render(command, values),
                cwd=worktree,
                env=controller_env,
                shell=True,
            )
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
            result = run(
                render(command, values),
                cwd=worktree,
                env=controller_env,
                shell=True,
            )
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

        # Freeze the agent-produced state before executing any untrusted project
        # code. Agent-visible .git is read-only, so these host-side Git metadata
        # operations cannot be redirected through attacker-controlled config.
        status = git(worktree, "status", "--porcelain=v1", check=False)
        (run_dir / "git-status.txt").write_text(status["stdout"], encoding="utf-8")
        untracked: list[str] = []
        for line in status["stdout"].splitlines():
            if line.startswith("?? "):
                untracked.append(line[3:])
        if untracked:
            git(worktree, "add", "-N", "--", *untracked, check=False)
        diff = git(worktree, "diff", "--binary", check=False)
        final_diff = run_dir / "final.diff"
        final_diff.write_text(diff["stdout"], encoding="utf-8")

        dependency_mounts = collect_dependency_mounts(worktree)
        record["environment"]["validation_dependency_mounts"] = [
            relative.as_posix() for _, relative in dependency_mounts
        ]

        # Fetch hidden oracle bytes only in the trusted controller. They are
        # written into disposable validation checkouts, never the agent checkout.
        oracle = task.get("oracle", {})
        oracle_ref = oracle.get("ref")
        oracle_payloads: list[tuple[str, str, str]] = []
        for item in oracle.get("files", []):
            if not oracle_ref:
                raise RuntimeError("oracle.files requires oracle.ref")
            source = item["source"]
            shown = git(source_repo, "show", f"{oracle_ref}:{source}", check=False)
            record["commands"]["oracle_install"].append({
                "source": source,
                "destination": item["destination"],
                "git_show_exit_code": shown["exit_code"],
                "installed_at_unix": time.time(),
                "workspace": "disposable-validation-only",
            })
            if shown["exit_code"] != 0:
                raise RuntimeError(f"failed to materialize hidden oracle: {source}")
            oracle_payloads.append((source, item["destination"], shown["stdout"]))

        def isolated_result(command: str, *, with_oracle: bool) -> dict[str, Any]:
            with tempfile.TemporaryDirectory(
                prefix=f"validate-{run_id}-", dir=tmp_root
            ) as validation_temp:
                validation = prepare_validation_workspace(
                    source_repo,
                    treatment["sha"],
                    final_diff,
                    Path(validation_temp) / "worktree",
                )
                if with_oracle:
                    for _, destination, content in oracle_payloads:
                        safe_write_beneath(validation, destination, content)
                validation_values = dict(values)
                validation_values["worktree"] = "/workspace"
                validation_values["source_repo"] = "/unavailable-source-repo"
                validation_values["run_dir"] = "/unavailable-run-dir"
                rendered = render(command, validation_values)
                return run_validation_sandbox(
                    validation, rendered, dependency_mounts
                )

        # Every post-agent command executes against a fresh reproduction of the
        # agent patch in a no-network, no-secret sandbox. No agent-controlled
        # source is ever executed directly by the host controller.
        acceptance_ok = True
        for command in task.get("acceptance_commands", []):
            result = isolated_result(command, with_oracle=True)
            record["commands"]["acceptance"].append(result)
            acceptance_ok = acceptance_ok and result["exit_code"] == 0

        verification_ok = True
        for command in task.get("verification_commands", []):
            result = isolated_result(command, with_oracle=False)
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
                patch_path.write_text(
                    source_path.read_text(encoding="utf-8"), encoding="utf-8"
                )
            elif mutation_ref and patch_source:
                shown = git(
                    source_repo,
                    "show",
                    f"{mutation_ref}:{patch_source}",
                    check=False,
                )
                if shown["exit_code"] != 0:
                    raise RuntimeError(
                        f"failed to materialize mutation patch: {patch_source}"
                    )
                patch_path.write_text(shown["stdout"], encoding="utf-8")
            else:
                raise RuntimeError(
                    "mutation check requires patch or ref + patch_source"
                )

            mutation_record: dict[str, Any] = {
                "name": mutation.get("name", f"mutation-{index}"),
                "ref": mutation_ref,
                "patch_source": patch_source,
                "patch": local_patch,
                "apply_exit_code": None,
                "commands": [],
                "killed": False,
                "isolation": "disposable-validation-workspace",
            }
            record["commands"]["mutation_checks"].append(mutation_record)

            with tempfile.TemporaryDirectory(
                prefix=f"mutation-{run_id}-{index:02d}-", dir=tmp_root
            ) as mutation_temp:
                mutation_workspace = prepare_validation_workspace(
                    source_repo,
                    treatment["sha"],
                    final_diff,
                    Path(mutation_temp) / "worktree",
                )
                applied = run(
                    ["git", "apply", "--whitespace=nowarn", str(patch_path)],
                    cwd=mutation_workspace,
                )
                mutation_record["apply_exit_code"] = applied["exit_code"]
                if applied["exit_code"] != 0:
                    mutation_checks_ok = False
                    continue

                expected = mutation.get("expected", "failure")
                observed_failure = False
                observed_success = True
                mutation_values = dict(values)
                mutation_values["worktree"] = "/workspace"
                mutation_values["source_repo"] = "/unavailable-source-repo"
                mutation_values["run_dir"] = "/unavailable-run-dir"
                for command in mutation.get("commands", []):
                    rendered = render(command, mutation_values)
                    result = run_validation_sandbox(
                        mutation_workspace, rendered, dependency_mounts
                    )
                    mutation_record["commands"].append(result)
                    observed_failure = (
                        observed_failure or result["exit_code"] != 0
                    )
                    observed_success = (
                        observed_success and result["exit_code"] == 0
                    )

                mutation_record["killed"] = (
                    observed_failure if expected == "failure" else observed_success
                )
                mutation_checks_ok = (
                    mutation_checks_ok and mutation_record["killed"]
                )

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
