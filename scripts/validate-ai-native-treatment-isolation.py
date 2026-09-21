#!/usr/bin/env python3
"""Validate that A/B/C isolate the intended repository-architecture variables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)
SEMANTIC_FIELDS = (
    "id",
    "name",
    "description",
    "aliases",
    "dependencies",
    "consumers",
    "state",
    "invariants",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_bytes(repo: Path, ref: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
    return proc.stdout


def git_text(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout.strip()


def semantic_projection(cap: dict[str, Any]) -> dict[str, Any]:
    return {key: cap.get(key) for key in SEMANTIC_FIELDS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-repo", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    source = args.source_repo.resolve()
    lock = load(EXPERIMENT / "BENCHMARK-LOCK.json")
    treatment_cfg = load(EXPERIMENT / "runner" / "treatments.json")["treatments"]

    a = lock["treatments"]["A"]
    b = lock["treatments"]["B"]
    c = lock["treatments"]["C"]
    errors: list[str] = []

    # A -> B must add only the semantic-index surface.
    ab_paths = [
        line
        for line in git_text(source, "diff", "--name-only", a, b).splitlines()
        if line
    ]
    expected_ab_paths = {
        ".ai-native/README.md",
        ".ai-native/capabilities.json",
        ".ai-native/resolve.mjs",
    }
    if set(ab_paths) != expected_ab_paths:
        errors.append(
            "A->B is not isolated to the semantic index: "
            f"{sorted(ab_paths)} != {sorted(expected_ab_paths)}"
        )

    # The resolver algorithm itself must be byte-identical in B and C.
    resolver_b = git_bytes(source, b, ".ai-native/resolve.mjs")
    resolver_c = git_bytes(source, c, ".ai-native/resolve.mjs")
    if resolver_b != resolver_c:
        errors.append("B/C resolver implementation differs")

    caps_b = json.loads(
        git_bytes(source, b, ".ai-native/capabilities.json").decode("utf-8")
    )
    caps_c = json.loads(
        git_bytes(source, c, ".ai-native/capabilities.json").decode("utf-8")
    )

    if caps_b.get("generated_from") != a or caps_c.get("generated_from") != a:
        errors.append("B/C semantic indexes do not share the frozen A ancestor")

    by_id_b = {item["id"]: item for item in caps_b.get("capabilities", [])}
    by_id_c = {item["id"]: item for item in caps_c.get("capabilities", [])}
    if set(by_id_b) != set(by_id_c):
        errors.append("B/C capability identity sets differ")

    semantic_differences: list[str] = []
    physical_projection_changes: list[dict[str, Any]] = []
    for capability_id in sorted(set(by_id_b) & set(by_id_c)):
        left = by_id_b[capability_id]
        right = by_id_c[capability_id]
        if semantic_projection(left) != semantic_projection(right):
            semantic_differences.append(capability_id)
        physical_projection_changes.append({
            "id": capability_id,
            "owners_B": left.get("owners", []),
            "owners_C": right.get("owners", []),
            "evidence_B": left.get("evidence", []),
            "evidence_C": right.get("evidence", []),
        })
    if semantic_differences:
        errors.append(
            "B/C semantic capability meaning differs for: "
            + ", ".join(semantic_differences)
        )

    instruction_b = treatment_cfg["B"].get("agent_instruction")
    instruction_c = treatment_cfg["C"].get("agent_instruction")
    if not instruction_b or instruction_b != instruction_c:
        errors.append("B/C resolver exposure instructions are not identical")

    # Treatment metadata must not contain benchmark task IDs.
    task_hint_pattern = re.compile(r"\bT(?:0[1-9]|1[0-9]|2[0-4])\b")
    hint_hits: dict[str, list[str]] = {}
    for label, ref in (("B", b), ("C", c)):
        hits: list[str] = []
        for path in (
            ".ai-native/README.md",
            ".ai-native/capabilities.json",
            ".ai-native/resolve.mjs",
        ):
            text = git_bytes(source, ref, path).decode("utf-8", errors="replace")
            if task_hint_pattern.search(text):
                hits.append(path)
        if hits:
            hint_hits[label] = hits
    if hint_hits:
        errors.append(f"treatment semantic surface leaks Txx benchmark IDs: {hint_hits}")

    result = {
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
        "benchmark_revision": lock["benchmark_revision"],
        "treatments": {"A": a, "B": b, "C": c},
        "checks": {
            "A_to_B_only_semantic_index_files": set(ab_paths) == expected_ab_paths,
            "B_C_resolver_bytes_identical": resolver_b == resolver_c,
            "B_C_capability_ids_identical": set(by_id_b) == set(by_id_c),
            "B_C_semantic_fields_identical": not semantic_differences,
            "B_C_agent_instruction_identical": bool(
                instruction_b and instruction_b == instruction_c
            ),
            "B_C_no_Txx_benchmark_hints": not hint_hits,
        },
        "A_to_B_changed_paths": sorted(ab_paths),
        "capability_count": len(by_id_b),
        "B_C_physical_projection_changes": physical_projection_changes,
        "errors": errors,
        "interpretation": (
            "A->B isolates the semantic index/resolver surface. B->C keeps the "
            "resolver algorithm, capability IDs, descriptions, aliases, graph "
            "edges, state, and invariants identical; only owner/evidence path "
            "projections change as required by the structural relocation."
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
        print("Treatment isolation FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Treatment isolation OK")
    print(f"  A->B changed paths: {len(ab_paths)} semantic-index files only")
    print(f"  B/C capabilities: {len(by_id_b)} stable semantic identities")
    print("  B/C resolver: byte-identical")
    print("  B/C semantic fields: identical")
    print("  B/C owner/evidence paths: allowed physical projection changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
