#!/usr/bin/env python3
"""Static and Git-level integrity checks for the AI-native repository benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


EXPECTED_TASKS = [f"T{i:02d}" for i in range(1, 25)]
FORBIDDEN_PROMPT_FRAGMENTS = (
    "web/src/",
    "capability://",
    ".ai-native/",
    "research/ai-native-",
)

SEMANTIC_FREEZE_PATHS = (
    "tasks/README.md",
    "runner/manifests",
    "runner/fixtures",
    "runner/mutations",
    "runner/treatments.json",
    "runner/oracle.json",
    "runner/gold.json",
)


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def resolve_relative(manifest: Path, value: str) -> Path:
    return (manifest.parent / value).resolve()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--experiment-root",
        type=Path,
        default=Path(
            "docs/topics/agent-native-repository-architecture/research/experiments/"
            "nession-terminal-session-reconnect-2026-09"
        ),
    )
    ap.add_argument("--source-repo", type=Path)
    args = ap.parse_args()

    root = args.experiment_root.resolve()
    manifests_dir = root / "runner" / "manifests"
    treatments_path = root / "runner" / "treatments.json"
    oracle_path = root / "runner" / "oracle.json"
    gold_path = root / "runner" / "gold.json"

    errors: list[str] = []

    treatments = load(treatments_path)
    oracle = load(oracle_path)
    gold = load(gold_path)

    # Revision-1 semantics are frozen at the definition SHA recorded in the
    # experiment lock. Main may continue to evolve runner/adapter mechanics,
    # but task/treatment/gold/fixture semantics must remain byte-identical.
    definition_repo = Path(__file__).resolve().parents[1]
    lock_path = root / "BENCHMARK-LOCK.json"
    require(lock_path.exists(), f"missing benchmark lock: {lock_path}", errors)
    if lock_path.exists():
        lock = load(lock_path)
        definition_sha = lock.get("definition_sha")
        require(bool(definition_sha), "benchmark lock has no definition_sha", errors)
        if definition_sha:
            rel_root = root.relative_to(definition_repo)
            semantic_paths = [str(rel_root / item) for item in SEMANTIC_FREEZE_PATHS]
            frozen = git(
                definition_repo,
                "diff",
                "--quiet",
                str(definition_sha),
                "--",
                *semantic_paths,
                check=False,
            )
            require(
                frozen.returncode == 0,
                "benchmark semantic drift detected relative to frozen definition SHA "
                f"{definition_sha}",
                errors,
            )

    require(set(treatments["treatments"]) == {"A", "B", "C"}, "treatments must be exactly A/B/C", errors)
    require(oracle["sha"], "oracle SHA must be non-empty", errors)
    require(set(gold["tasks"]) == set(EXPECTED_TASKS), "gold.json must contain T01-T24 exactly", errors)

    manifests: dict[str, tuple[Path, dict[str, Any]]] = {}
    for task_id in EXPECTED_TASKS:
        path = manifests_dir / f"{task_id}.json"
        require(path.exists(), f"missing manifest: {path}", errors)
        if not path.exists():
            continue
        data = load(path)
        manifests[task_id] = (path, data)
        require(data.get("task_id") == task_id, f"{task_id}: task_id mismatch", errors)
        prompt = data.get("prompt", "")
        require(isinstance(prompt, str) and prompt.strip(), f"{task_id}: empty prompt", errors)
        for fragment in FORBIDDEN_PROMPT_FRAGMENTS:
            require(fragment not in prompt, f"{task_id}: prompt leaks repository/treatment hint {fragment!r}", errors)

        fixtures = data.get("fixtures", {})
        require(set(fixtures) == {"A", "B", "C"}, f"{task_id}: fixtures must declare A/B/C", errors)

        for treatment, fixture in fixtures.items():
            patch = fixture.get("patch") if isinstance(fixture, dict) else None
            if patch:
                patch_path = resolve_relative(path, patch)
                require(patch_path.exists(), f"{task_id}/{treatment}: missing fixture patch {patch_path}", errors)

        task_oracle = data.get("oracle")
        if task_oracle:
            require(task_oracle.get("ref") == oracle["sha"], f"{task_id}: oracle ref is not frozen oracle SHA", errors)
            for item in task_oracle.get("files", []):
                require("source" in item and "destination" in item, f"{task_id}: malformed oracle file entry", errors)

        mutation_groups = data.get("mutation_checks_by_treatment", {})
        for treatment, checks in mutation_groups.items():
            require(treatment in {"A", "B", "C"}, f"{task_id}: unknown mutation treatment {treatment}", errors)
            for mutation in checks:
                local = mutation.get("patch")
                if local:
                    p = resolve_relative(path, local)
                    require(p.exists(), f"{task_id}/{treatment}: missing mutation patch {p}", errors)

    if args.source_repo:
        source = args.source_repo.resolve()
        require((source / ".git").exists() or (source / "HEAD").exists(), f"not a Git repository: {source}", errors)

        # Verify frozen commits and hidden oracle source.
        for treatment, item in treatments["treatments"].items():
            sha = item["sha"]
            result = git(source, "cat-file", "-e", f"{sha}^{{commit}}", check=False)
            require(result.returncode == 0, f"missing treatment commit {treatment}: {sha}", errors)

        oracle_sha = oracle["sha"]
        result = git(source, "cat-file", "-e", f"{oracle_sha}^{{commit}}", check=False)
        require(result.returncode == 0, f"missing oracle commit: {oracle_sha}", errors)

        oracle_sources = sorted({
            item["source"]
            for _, data in manifests.values()
            for item in data.get("oracle", {}).get("files", [])
        })
        for source_path in oracle_sources:
            result = git(source, "cat-file", "-e", f"{oracle_sha}:{source_path}", check=False)
            require(result.returncode == 0, f"oracle source missing at frozen SHA: {source_path}", errors)

        with tempfile.TemporaryDirectory(prefix="narness-benchmark-check-") as tmp:
            tmp_root = Path(tmp)
            for treatment, treatment_cfg in treatments["treatments"].items():
                wt = tmp_root / treatment
                add = git(source, "worktree", "add", "--detach", str(wt), treatment_cfg["sha"], check=False)
                if add.returncode != 0:
                    errors.append(f"cannot create {treatment} worktree: {add.stderr}")
                    continue
                try:
                    for task_id, (manifest_path, data) in manifests.items():
                        fixture = data.get("fixtures", {}).get(treatment, {})
                        patch = fixture.get("patch") if isinstance(fixture, dict) else None
                        if patch:
                            patch_path = resolve_relative(manifest_path, patch)
                            result = git(wt, "apply", "--check", str(patch_path), check=False)
                            require(
                                result.returncode == 0,
                                f"{task_id}/{treatment}: fixture patch does not apply: {result.stderr.strip()}",
                                errors,
                            )

                        task_oracle = data.get("oracle")
                        if task_oracle:
                            for item in task_oracle.get("files", []):
                                destination = wt / item["destination"]
                                parent = destination.parent
                                require(
                                    parent.exists(),
                                    f"{task_id}/{treatment}: oracle destination parent missing: {parent.relative_to(wt)}",
                                    errors,
                                )
                                require(
                                    not destination.exists(),
                                    f"{task_id}/{treatment}: hidden oracle destination already exists: {item['destination']}",
                                    errors,
                                )

                        for mutation in data.get("mutation_checks_by_treatment", {}).get(treatment, []):
                            local = mutation.get("patch")
                            if local:
                                patch_path = resolve_relative(manifest_path, local)
                                result = git(wt, "apply", "--check", str(patch_path), check=False)
                                require(
                                    result.returncode == 0,
                                    f"{task_id}/{treatment}: mutation patch does not apply: {result.stderr.strip()}",
                                    errors,
                                )
                finally:
                    git(source, "worktree", "remove", "--force", str(wt), check=False)

    if errors:
        print("Benchmark integrity FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Benchmark integrity OK")
    print(f"  manifests: {len(manifests)}")
    print(f"  oracle: {oracle['sha']}")
    print("  treatments:")
    for name, cfg in treatments["treatments"].items():
        print(f"    {name}: {cfg['sha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
