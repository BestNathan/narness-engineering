#!/usr/bin/env python3
"""Validate a completed revision-1 conclusion decision file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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
