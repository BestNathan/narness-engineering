#!/usr/bin/env python3
"""Aggregate sealed AI-native benchmark runs without imputing missing data."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


TREATMENTS = ("A", "B", "C")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def med(values: list[float]) -> float | None:
    clean = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return median(clean) if clean else None


def mean_bool(values: list[bool]) -> float | None:
    return (sum(1 for x in values if x) / len(values)) if values else None


def mean_num(values: list[float]) -> float | None:
    clean = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return (sum(clean) / len(clean)) if clean else None


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()

    runs_root = args.runs_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for run_path in sorted(runs_root.rglob("run.json")):
        run = load(run_path)
        if not run.get("admissible_for_final_analysis"):
            continue
        score_path = run_path.parent / "score.json"
        if not score_path.exists():
            continue
        score = load(score_path)
        records.append({"run": run, "score": score, "dir": run_path.parent})

    raw_rows: list[dict[str, Any]] = []
    for item in records:
        run = item["run"]
        metrics = item["score"].get("metrics", {})
        raw_rows.append({
            "run_id": run.get("run_id"),
            "task_id": run.get("task_id"),
            "treatment": run.get("treatment"),
            "attempt": run.get("attempt"),
            "task_success": run.get("task_success"),
            "wall_time_ms": run.get("wall_time_ms"),
            **metrics,
        })

    fieldnames = sorted({k for row in raw_rows for k in row}) if raw_rows else []
    with (out / "raw-runs.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(raw_rows)

    summary: dict[str, dict[str, Any]] = {}
    for treatment in TREATMENTS:
        rows = [row for row in raw_rows if row.get("treatment") == treatment]
        summary[treatment] = {
            "n": len(rows),
            "tasks": len({row.get("task_id") for row in rows}),
            "task_success_rate": mean_bool([bool(row.get("task_success")) for row in rows]),
            "first_hit_target_accuracy": mean_bool(
                [bool(row["first_hit_correct"]) for row in rows if row.get("first_hit_correct") is not None]
            ),
            "navigation_precision_mean": mean_num(
                [row["navigation_precision"] for row in rows if row.get("navigation_precision") is not None]
            ),
            "navigation_recall_mean": mean_num(
                [row["navigation_recall"] for row in rows if row.get("navigation_recall") is not None]
            ),
            "irrelevant_files_read_median": med(
                [row["irrelevant_files_read"] for row in rows if row.get("irrelevant_files_read") is not None]
            ),
            "files_read_median": med(
                [row["files_read"] for row in rows if row.get("files_read") is not None]
            ),
            "search_calls_median": med(
                [row["search_calls"] for row in rows if row.get("search_calls") is not None]
            ),
            "input_tokens_median": med(
                [row["input_tokens"] for row in rows if row.get("input_tokens") is not None]
            ),
            "repair_loops_median": med(
                [row["repair_loops"] for row in rows if row.get("repair_loops") is not None]
            ),
            "wall_time_ms_median": med(
                [row["wall_time_ms"] for row in rows if row.get("wall_time_ms") is not None]
            ),
        }

    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    headers = [
        ("Task success rate", "task_success_rate"),
        ("First-hit target accuracy", "first_hit_target_accuracy"),
        ("Navigation precision (mean)", "navigation_precision_mean"),
        ("Navigation recall (mean)", "navigation_recall_mean"),
        ("Median irrelevant files read", "irrelevant_files_read_median"),
        ("Median files read", "files_read_median"),
        ("Median search calls", "search_calls_median"),
        ("Median input tokens", "input_tokens_median"),
        ("Median repair loops", "repair_loops_median"),
        ("Median wall time ms", "wall_time_ms_median"),
    ]
    lines = [
        "# Formal Results — Generated",
        "",
        f"Sealed admissible runs: {len(raw_rows)}",
        "",
        "| Metric | A | B | C |",
        "|---|---:|---:|---:|",
    ]
    for label, key in headers:
        lines.append(
            f"| {label} | {fmt(summary['A'][key])} | "
            f"{fmt(summary['B'][key])} | {fmt(summary['C'][key])} |"
        )
    lines.extend([
        "",
        "No missing metric is imputed. The em dash means no admissible observation is available.",
        "",
        "Per-run values are written to raw-runs.csv; machine-readable aggregates are in summary.json.",
    ])
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Aggregated {len(raw_rows)} admissible runs")
    for treatment in TREATMENTS:
        print(
            f"  {treatment}: n={summary[treatment]['n']} "
            f"tasks={summary[treatment]['tasks']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
