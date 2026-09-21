#!/usr/bin/env python3
"""Validate a completed revision-1 conclusion decision file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)

ALLOWED = {
    "Supported",
    "Partially supported",
    "Not supported",
    "Inconclusive",
}
HYPOTHESES = ("H1", "H2", "H3", "H4", "H5")
DECISIONS = {"graduate", "keep-experimental", "reject"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conclusions", required=True, type=Path)
    args = ap.parse_args()

    value = json.loads(args.conclusions.read_text(encoding="utf-8"))
    errors: list[str] = []

    benchmark = json.loads((EXPERIMENT / "BENCHMARK-LOCK.json").read_text(encoding="utf-8"))
    analysis = json.loads((EXPERIMENT / "ANALYSIS-LOCK.json").read_text(encoding="utf-8"))
    if value.get("experiment_id") != benchmark.get("experiment_id"):
        errors.append("experiment_id does not match frozen benchmark")
    if value.get("benchmark_revision") != benchmark.get("benchmark_revision"):
        errors.append("benchmark_revision does not match frozen benchmark")
    if value.get("analysis_revision") != analysis.get("analysis_revision"):
        errors.append("analysis_revision does not match active frozen analysis")

    hypotheses = value.get("hypotheses", {})
    if set(hypotheses) != set(HYPOTHESES):
        errors.append("hypotheses must contain exactly H1-H5")

    for key in HYPOTHESES:
        item = hypotheses.get(key, {})
        if item.get("classification") not in ALLOWED:
            errors.append(f"{key}: invalid or missing classification")
        if not str(item.get("rationale", "")).strip():
            errors.append(f"{key}: rationale is required")

    if not str(value.get("overall_summary", "")).strip():
        errors.append("overall_summary is required")

    decisions = value.get("architecture_decisions")
    if not isinstance(decisions, list) or not decisions:
        errors.append("at least one architecture_decision is required")
    else:
        for index, item in enumerate(decisions):
            if not str(item.get("idea", "")).strip():
                errors.append(f"architecture_decisions[{index}]: idea is required")
            decision = item.get("decision")
            if decision not in DECISIONS:
                errors.append(
                    f"architecture_decisions[{index}]: decision must be one of {sorted(DECISIONS)}"
                )
            if not str(item.get("rationale", "")).strip():
                errors.append(f"architecture_decisions[{index}]: rationale is required")

    if errors:
        print("Conclusion validation FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Conclusion validation OK")
    for key in HYPOTHESES:
        print(f"  {key}: {hypotheses[key]['classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
