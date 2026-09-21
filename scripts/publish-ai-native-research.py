#!/usr/bin/env python3
"""Publish a completed AI-native repository study back into Narness Engineering."""

from __future__ import annotations

import argparse
import hashlib
import json
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
DEFAULT_DESTINATION = EXPERIMENT / "published" / "benchmark-r2-analysis-r2"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_required(source: Path, destination: Path) -> None:
    if not source.exists():
        raise RuntimeError(f"required publication input missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--conclusions", required=True, type=Path)
    ap.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = ap.parse_args()

    runs_root = args.runs_root.resolve()
    results = args.results_dir.resolve()
    conclusions = args.conclusions.resolve()
    destination = args.destination.resolve()

    completeness = load(results / "research-completeness.json")
    collection = load(results / "collection-manifest.json")
    artifact = load(results / "research-artifact-manifest.json")

    required_complete = {
        "run_count_complete": completeness.get("run_count_complete"),
        "all_24_tasks_present_per_treatment": completeness.get(
            "all_24_tasks_present_per_treatment"
        ),
        "hypothesis_classification_complete": completeness.get(
            "hypothesis_classification_complete"
        ),
        "collection_complete": completeness.get("collection_complete"),
    }
    bad = [key for key, value in required_complete.items() if value is not True]
    if bad:
        raise RuntimeError(
            "research is not publication-complete: " + ", ".join(sorted(bad))
        )
    if completeness.get("missing_failure_reviews") != 0:
        raise RuntimeError("research still has missing failure reviews")
    if collection.get("complete") is not True:
        raise RuntimeError("collection manifest is not complete")
    if artifact.get("complete") is not True:
        raise RuntimeError("research artifact manifest is not complete")

    validate = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-native-conclusion.py"),
            "--conclusions",
            str(conclusions),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if validate.returncode != 0:
        raise RuntimeError(
            "conclusion validation failed before publication:\n" + validate.stdout
        )

    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(
            f"publication destination already exists and is non-empty: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=True)

    result_files = (
        "raw-runs.csv",
        "summary.json",
        "summary.md",
        "paired-effects.json",
        "paired-effects.md",
        "failure-summary.json",
        "failure-summary.md",
        "collection-manifest.json",
        "research-completeness.json",
        "research-report.md",
        "research-artifact-manifest.json",
    )
    for name in result_files:
        copy_required(results / name, destination / name)

    copy_required(
        runs_root / "_collection" / "collection-start.json",
        destination / "collection-start.json",
    )
    copy_required(conclusions, destination / "conclusion-r2.json")

    frozen_inputs = {
        "BENCHMARK-LOCK.json": EXPERIMENT / "BENCHMARK-LOCK.json",
        "ANALYSIS-LOCK.json": EXPERIMENT / "ANALYSIS-LOCK.json",
        "construction-cost-r1.json": (
            EXPERIMENT / "treatments" / "construction-cost-r1.json"
        ),
        "execution-profile-r1.json": (
            EXPERIMENT / "runner" / "execution-profile-r1.json"
        ),
        "formal-schedule-r1.json": (
            EXPERIMENT / "runner" / "formal-schedule-r1.json"
        ),
        "formal-plan-r1.lock.json": (
            EXPERIMENT / "runner" / "formal-plan-r1.lock.json"
        ),
    }
    for name, source in frozen_inputs.items():
        copy_required(source, destination / "frozen-inputs" / name)

    published_files = sorted(
        path
        for path in destination.rglob("*")
        if path.is_file() and path.name != "publication-manifest.json"
    )
    hashes = {
        str(path.relative_to(destination)): sha256_file(path)
        for path in published_files
    }
    digest_material = "\n".join(
        f"{name}:{digest}" for name, digest in sorted(hashes.items())
    ).encode("utf-8")

    publication_manifest = {
        "schema_version": 1,
        "experiment_id": artifact["experiment_id"],
        "benchmark_revision": artifact["benchmark_revision"],
        "benchmark_definition_sha": artifact["benchmark_definition_sha"],
        "analysis_revision": artifact["analysis_revision"],
        "analysis_definition_sha": artifact["analysis_definition_sha"],
        "execution_profile_id": artifact.get("execution_profile_id"),
        "collection_digest_sha256": artifact.get("collection_digest_sha256"),
        "research_artifact_set_digest_sha256": artifact.get(
            "artifact_set_digest_sha256"
        ),
        "published_files": hashes,
        "publication_digest_sha256": hashlib.sha256(digest_material).hexdigest(),
        "raw_trace_policy": (
            "Full per-run traces/diffs remain in the sealed formal run collection "
            "and are not duplicated into Git publication output. raw-runs.csv and "
            "collection-manifest.json are published; run seals/content hashes retain "
            "the identity of the complete collection."
        ),
    }
    (destination / "publication-manifest.json").write_text(
        json.dumps(publication_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    readme = f"""# Published AI-Native Repository Experiment

This directory is a publication projection of the completed
nession-terminal-session-reconnect-2026-09 study.

Benchmark Revision: {artifact['benchmark_revision']}
Benchmark definition: {artifact['benchmark_definition_sha']}

Analysis Revision: {artifact['analysis_revision']}
Analysis definition: {artifact['analysis_definition_sha']}

Collection digest:
{artifact.get('collection_digest_sha256')}

Research artifact digest:
{artifact.get('artifact_set_digest_sha256')}

Publication digest:
{publication_manifest['publication_digest_sha256']}

Start with research-report.md.

The package includes aggregate/raw tabular measurements, paired effects, failure
taxonomy, reviewed H1-H5 conclusion, collection identity, execution/profile/order
locks, and the final research artifact manifest.

Full per-run traces and diffs are intentionally not duplicated into Git. Their
content identity is preserved by the formal run seals and collection-manifest.json.
"""
    (destination / "README.md").write_text(readme, encoding="utf-8")

    # Recompute publication identity with README included.
    hashes["README.md"] = sha256_file(destination / "README.md")
    digest_material = "\n".join(
        f"{name}:{digest}" for name, digest in sorted(hashes.items())
    ).encode("utf-8")
    publication_manifest["published_files"] = dict(sorted(hashes.items()))
    publication_manifest["publication_digest_sha256"] = hashlib.sha256(
        digest_material
    ).hexdigest()
    (destination / "publication-manifest.json").write_text(
        json.dumps(publication_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Research publication bundle ready")
    print(f"  destination: {destination}")
    print(
        "  publication digest: "
        f"{publication_manifest['publication_digest_sha256']}"
    )
    print("  next: review the generated bundle and commit it to narness-engineering")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
