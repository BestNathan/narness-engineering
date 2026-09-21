#!/usr/bin/env python3
"""Prove the benchmark checkout cannot see hidden sibling/descendant Git objects."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "ai-native-repo-experiment.py"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
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


def commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def main() -> int:
    runner = load_runner()

    with tempfile.TemporaryDirectory(prefix="narness-checkout-isolation-") as tmp:
        root = Path(tmp)
        source = root / "source"
        source.mkdir()
        git(source, "init")
        git(source, "config", "user.email", "checkout-selftest@example.invalid")
        git(source, "config", "user.name", "Checkout Isolation Selftest")

        base = commit_file(source, "base.txt", "base\n", "base")
        treatment = commit_file(
            source,
            "treatment.txt",
            "visible treatment\n",
            "treatment",
        )

        # Research-only descendant exists in the source object database/ref set.
        git(source, "switch", "-c", "research/hidden-oracle")
        hidden = commit_file(
            source,
            "hidden-oracle.txt",
            "must never be visible to the coding agent\n",
            "hidden oracle",
        )

        isolated = root / "isolated"
        runner.create_isolated_checkout(source, isolated, treatment)

        assert git(isolated, "rev-parse", "HEAD").stdout.strip() == treatment
        assert (isolated / "base.txt").exists()
        assert (isolated / "treatment.txt").exists()
        assert not (isolated / "hidden-oracle.txt").exists()

        # Treatment history remains available.
        history = git(isolated, "rev-list", "HEAD").stdout.splitlines()
        assert treatment in history
        assert base in history

        # Hidden descendant object and ref must not have crossed the boundary.
        hidden_probe = git(
            isolated,
            "cat-file",
            "-e",
            f"{hidden}^{{commit}}",
            check=False,
        )
        assert hidden_probe.returncode != 0
        refs = git(isolated, "for-each-ref", "--format=%(refname)").stdout.strip()
        assert "hidden-oracle" not in refs
        assert git(isolated, "remote").stdout.strip() == ""

        config = (isolated / ".git" / "config").read_text(encoding="utf-8")
        assert str(source) not in config
        assert not (isolated / ".git" / "FETCH_HEAD").exists()
        assert not (isolated / ".git" / "objects" / "info" / "alternates").exists()

    print("Standalone single-ref checkout isolation selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
