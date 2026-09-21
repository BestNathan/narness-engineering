#!/usr/bin/env python3
"""Preflight the local machine before spending model budget on Codex pilots."""

from __future__ import annotations

import argparse
import json
import os
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
PILOTS = (("T05", "A"), ("T08", "B"), ("T20", "C"))


def capture(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-repo", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--codex-bin", default="codex")
    ap.add_argument(
        "--skip-codex",
        action="store_true",
        help="CI/selftest mode: validate everything except local Codex availability.",
    )
    args = ap.parse_args()

    source = args.source_repo.resolve()
    output = args.output_dir.resolve()
    errors: list[str] = []

    if not (source / ".git").exists():
        fail(errors, f"source repository is not a normal Git checkout: {source}")

    code, status = capture(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
    )
    if code != 0:
        fail(errors, "cannot inspect narness-engineering Git status")
    elif status:
        fail(
            errors,
            "narness-engineering has tracked local changes; commit/stash them before pilots",
        )

    code, source_status = capture(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=source,
    )
    if code != 0:
        fail(errors, "cannot inspect Nession Git status")
    elif source_status:
        fail(
            errors,
            "Nession source checkout has tracked local changes; pilots use worktrees but a clean source checkout is required",
        )

    treatments = load(EXPERIMENT / "runner" / "treatments.json")
    oracle = load(EXPERIMENT / "runner" / "oracle.json")
    refs = {
        "oracle": oracle["sha"],
        **{
            f"treatment-{name}": data["sha"]
            for name, data in treatments["treatments"].items()
        },
    }
    for label, sha in refs.items():
        code, _ = capture(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=source)
        if code != 0:
            fail(
                errors,
                f"Nession checkout is missing frozen {label} commit {sha}; run git fetch origin first",
            )

    code, integrity = capture(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-native-benchmark.py"),
            "--source-repo",
            str(source),
        ],
        cwd=ROOT,
    )
    if code != 0:
        fail(errors, "benchmark integrity preflight failed:\n" + integrity)

    for tool in ("git", "node", "npm"):
        path = shutil.which(tool)
        if path is None:
            fail(errors, f"required executable not found: {tool}")

    versions: dict[str, str | None] = {}
    for name, cmd in {
        "python": [sys.executable, "--version"],
        "git": ["git", "--version"],
        "node": ["node", "--version"],
        "npm": ["npm", "--version"],
    }.items():
        code, value = capture(cmd)
        versions[name] = value if code == 0 else None

    codex_version = None
    codex_auth_status = None
    if not args.skip_codex:
        exposed_auth_env = [
            key
            for key in ("OPENAI_API_KEY", "CODEX_ACCESS_TOKEN")
            if os.environ.get(key)
        ]
        if exposed_auth_env:
            fail(
                errors,
                "refusing pilot execution with authentication secrets exported "
                "in the process environment: "
                + ", ".join(exposed_auth_env)
                + ". Authenticate Codex into its credential store first and unset "
                "these variables for the experiment.",
            )

        codex_path = shutil.which(args.codex_bin)
        if codex_path is None:
            fail(
                errors,
                f"Codex CLI not found: {args.codex_bin!r}. Install/authenticate it before pilots.",
            )
        else:
            code, value = capture([args.codex_bin, "--version"])
            if code != 0:
                fail(errors, "Codex CLI exists but --version failed")
            else:
                codex_version = value

            auth_code, _auth_value = capture(
                [args.codex_bin, "login", "status"]
            )
            if auth_code != 0:
                fail(
                    errors,
                    "Codex CLI is installed but has no usable authenticated "
                    "session (codex login status failed).",
                )
            else:
                codex_auth_status = "authenticated"

    for task, treatment in PILOTS:
        run_dir = output / f"{task}-{treatment}-01"
        if run_dir.exists():
            fail(
                errors,
                f"pilot output already exists and would violate fresh-run semantics: {run_dir}",
            )

    if errors:
        print("Codex pilot preflight FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Codex pilot preflight OK")
    print(f"  source: {source}")
    print(f"  output: {output}")
    for key, value in versions.items():
        print(f"  {key}: {value}")
    if args.skip_codex:
        print("  codex: skipped")
    else:
        print(f"  codex: {codex_version}")
        print(f"  codex auth: {codex_auth_status}")
        print("  exported auth secrets: none")
    print("  benchmark integrity: PASS")
    print("  planned pilots: T05/A, T08/B, T20/C")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
