#!/usr/bin/env python3
"""Validate isolated checkouts against the real frozen Nession object graph."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)
RUNNER_PATH = ROOT / "scripts" / "ai-native-repo-experiment.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git(
    repo: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def load_runner():
    spec = importlib.util.spec_from_file_location("narness_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load benchmark runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def history(repo: Path, ref: str) -> list[str]:
    return [
        line
        for line in git(repo, "rev-list", ref).stdout.splitlines()
        if line
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-repo", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    source = args.source_repo.resolve()
    runner = load_runner()
    treatment_cfg = load(EXPERIMENT / "runner" / "treatments.json")
    oracle = load(EXPERIMENT / "runner" / "oracle.json")
    treatments = {
        name: item["sha"]
        for name, item in treatment_cfg["treatments"].items()
    }
    oracle_sha = oracle["sha"]
    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(
        prefix="narness-real-checkout-isolation-"
    ) as tmp:
        root = Path(tmp)

        for treatment, sha in sorted(treatments.items()):
            source_history = history(source, sha)
            if oracle_sha in source_history:
                errors.append(
                    f"{treatment}: hidden oracle is an ancestor of treatment SHA"
                )

            isolated = root / treatment
            try:
                runner.create_isolated_checkout(source, isolated, sha)
            except Exception as exc:
                errors.append(f"{treatment}: isolated checkout failed: {exc!r}")
                continue

            isolated_history = history(isolated, "HEAD")
            if isolated_history != source_history:
                errors.append(
                    f"{treatment}: isolated history differs from source ancestry"
                )

            hidden_probe = git(
                isolated,
                "cat-file",
                "-e",
                f"{oracle_sha}^{{commit}}",
                check=False,
            )
            if hidden_probe.returncode == 0:
                errors.append(
                    f"{treatment}: hidden oracle object leaked into isolated repo"
                )

            leaked_non_ancestors: list[str] = []
            for other_name, other_sha in sorted(treatments.items()):
                if other_name == treatment:
                    continue
                ancestor = git(
                    source,
                    "merge-base",
                    "--is-ancestor",
                    other_sha,
                    sha,
                    check=False,
                ).returncode == 0
                probe = git(
                    isolated,
                    "cat-file",
                    "-e",
                    f"{other_sha}^{{commit}}",
                    check=False,
                )
                if not ancestor and probe.returncode == 0:
                    leaked_non_ancestors.append(other_name)
            if leaked_non_ancestors:
                errors.append(
                    f"{treatment}: non-ancestor treatment objects leaked: "
                    + ", ".join(leaked_non_ancestors)
                )

            refs = [
                line
                for line in git(
                    isolated,
                    "for-each-ref",
                    "--format=%(refname)",
                ).stdout.splitlines()
                if line
            ]
            remotes = git(isolated, "remote").stdout.strip()
            config = (isolated / ".git" / "config").read_text(
                encoding="utf-8"
            )
            alternates = (
                isolated / ".git" / "objects" / "info" / "alternates"
            )

            if refs:
                errors.append(
                    f"{treatment}: isolated repo unexpectedly exposes refs: {refs}"
                )
            if remotes:
                errors.append(
                    f"{treatment}: isolated repo unexpectedly exposes remotes: "
                    f"{remotes}"
                )
            if str(source) in config:
                errors.append(
                    f"{treatment}: source checkout path leaked into Git config"
                )
            if alternates.exists():
                errors.append(
                    f"{treatment}: isolated repo uses source object alternates"
                )
            if (isolated / ".git" / "FETCH_HEAD").exists():
                errors.append(
                    f"{treatment}: FETCH_HEAD retained after isolation"
                )

            rows.append({
                "treatment": treatment,
                "sha": sha,
                "history_commit_count": len(source_history),
                "history_preserved": isolated_history == source_history,
                "hidden_oracle_absent": hidden_probe.returncode != 0,
                "refs_exposed": refs,
                "remote_exposed": bool(remotes),
                "source_path_in_config": str(source) in config,
                "object_alternates_present": alternates.exists(),
            })

    result = {
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
        "checkout_isolation": "single-ref-standalone-git-no-remote",
        "oracle_sha": oracle_sha,
        "treatments": rows,
        "errors": errors,
        "interpretation": (
            "Each coding-agent checkout preserves exactly the ancestry reachable "
            "from its frozen treatment commit while excluding hidden-oracle and "
            "non-ancestor treatment objects, refs, remotes, source paths, and "
            "object alternates."
        ),
    }

    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if errors:
        print("Real subject checkout isolation FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Real subject checkout isolation OK")
    for row in rows:
        print(
            f"  {row['treatment']}: "
            f"{row['history_commit_count']} reachable commits; "
            "oracle/non-ancestor objects absent"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
