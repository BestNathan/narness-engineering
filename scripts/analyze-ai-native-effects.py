#!/usr/bin/env python3
"""Compute pre-registered paired A/B/C effects from aggregated formal runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
from statistics import median
from typing import Any


TREATMENTS = ("A", "B", "C")
CONTRASTS = {
    "A_vs_B": ("A", "B"),
    "B_vs_C": ("B", "C"),
    "A_vs_C": ("A", "C"),
}
HIGHER_BETTER = {
    "task_success",
    "first_hit_correct",
    "navigation_precision",
    "navigation_recall",
    "acceptance_ok",
    "verification_ok",
    "mutation_checks_ok",
}
LOWER_BETTER = {
    "irrelevant_files_read",
    "files_read",
    "search_calls",
    "search_result_false_positive_rate",
    "navigation_events_before_first_edit",
    "search_calls_before_first_edit",
    "files_read_before_first_edit",
    "resolver_calls_before_first_edit",
    "time_to_first_relevant_artifact_ms",
    "time_to_first_edit_ms",
    "important_artifacts_missed_count",
    "input_tokens",
    "repair_loops",
    "validation_failures",
    "out_of_scope_edit_count",
    "agent_duration_ms",
}
BOOLEAN_METRICS = {
    "task_success",
    "first_hit_correct",
    "acceptance_ok",
    "verification_ok",
    "mutation_checks_ok",
}


def parse_scalar(value: str | None) -> Any:
    if value is None or value == "":
        return None
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        number = float(value)
    except ValueError:
        return value
    if math.isfinite(number):
        return number
    return None


def clean_numeric(values: list[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            out.append(1.0 if value else 0.0)
            continue
        try:
            f = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def reduce_repetitions(metric: str, values: list[Any]) -> float | None:
    clean = clean_numeric(values)
    if not clean:
        return None
    if metric in BOOLEAN_METRICS:
        return sum(clean) / len(clean)
    return float(median(clean))


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    weight = pos - lo
    return xs[lo] * (1 - weight) + xs[hi] * weight


def oriented_delta(metric: str, control: float, treatment: float) -> float:
    if metric in HIGHER_BETTER:
        return treatment - control
    if metric in LOWER_BETTER:
        return control - treatment
    raise KeyError(metric)


def relative_improvement(metric: str, control: float, treatment: float) -> float | None:
    denominator = abs(control)
    if denominator == 0:
        return None
    return oriented_delta(metric, control, treatment) / denominator


def bootstrap_paired_median(
    task_effects: list[tuple[str, float]],
    *,
    samples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not task_effects:
        return None, None
    rng = random.Random(seed)
    values = [effect for _, effect in task_effects]
    boot: list[float] = []
    n = len(values)
    for _ in range(samples):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        boot.append(float(median(draw)))
    return quantile(boot, 0.025), quantile(boot, 0.975)


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-runs", required=True, type=Path)
    ap.add_argument("--strata", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--bootstrap-samples", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=20_260_921)
    args = ap.parse_args()

    strata = json.loads(args.strata.read_text(encoding="utf-8"))
    task_to_class = {
        task: klass
        for klass, tasks in strata["task_classes"].items()
        for task in tasks
    }

    with args.raw_runs.open(newline="", encoding="utf-8") as fh:
        rows = [
            {key: parse_scalar(value) for key, value in row.items()}
            for row in csv.DictReader(fh)
        ]

    metrics = sorted(HIGHER_BETTER | LOWER_BETTER)
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        task = str(row.get("task_id"))
        treatment = str(row.get("treatment"))
        if task not in task_to_class or treatment not in TREATMENTS:
            continue
        by_cell.setdefault((task, treatment), []).append(row)

    task_values: dict[str, dict[str, dict[str, float | None]]] = {}
    for task in sorted(task_to_class):
        task_values[task] = {}
        for treatment in TREATMENTS:
            cell = by_cell.get((task, treatment), [])
            task_values[task][treatment] = {
                metric: reduce_repetitions(
                    metric,
                    [row.get(metric) for row in cell],
                )
                for metric in metrics
            }

    effects: dict[str, Any] = {
        "schema_version": 1,
        "bootstrap_samples": args.bootstrap_samples,
        "bootstrap_seed": args.seed,
        "task_level_reduction": {
            "numeric": "median across repetitions",
            "boolean": "success proportion across repetitions",
        },
        "contrasts": {},
    }

    md = [
        "# Paired Treatment Effects — Generated",
        "",
        "Positive oriented effects mean the second treatment is better.",
        "",
    ]

    for contrast_name, (control_name, treatment_name) in CONTRASTS.items():
        contrast_result: dict[str, Any] = {}
        md.extend([
            f"## {contrast_name.replace('_', ' ')}",
            "",
            "| Metric | Matched tasks | Median improvement | 95% task-bootstrap CI | Improved / Same / Worse | Median relative improvement |",
            "|---|---:|---:|---:|---:|---:|",
        ])

        for metric in metrics:
            task_effects: list[tuple[str, float]] = []
            relative_effects: list[float] = []
            improved = same = worse = 0
            task_rows: list[dict[str, Any]] = []

            for task in sorted(task_to_class):
                control = task_values[task][control_name][metric]
                treatment = task_values[task][treatment_name][metric]
                if control is None or treatment is None:
                    continue
                effect = oriented_delta(metric, control, treatment)
                rel = relative_improvement(metric, control, treatment)
                task_effects.append((task, effect))
                if rel is not None:
                    relative_effects.append(rel)
                if effect > 0:
                    improved += 1
                elif effect < 0:
                    worse += 1
                else:
                    same += 1
                task_rows.append({
                    "task_id": task,
                    "task_class": task_to_class[task],
                    "control": control,
                    "treatment": treatment,
                    "oriented_improvement": effect,
                    "relative_improvement": rel,
                })

            median_effect = (
                float(median([effect for _, effect in task_effects]))
                if task_effects else None
            )
            lo, hi = bootstrap_paired_median(
                task_effects,
                samples=args.bootstrap_samples,
                seed=args.seed + sum(ord(c) for c in contrast_name + metric),
            )
            median_relative = (
                float(median(relative_effects)) if relative_effects else None
            )

            strata_result: dict[str, Any] = {}
            for klass, tasks in strata["task_classes"].items():
                vals = [
                    row["oriented_improvement"]
                    for row in task_rows
                    if row["task_id"] in tasks
                ]
                strata_result[klass] = {
                    "n": len(vals),
                    "median_oriented_improvement": (
                        float(median(vals)) if vals else None
                    ),
                }

            contrast_result[metric] = {
                "direction": "higher_is_better" if metric in HIGHER_BETTER else "lower_is_better",
                "matched_tasks": len(task_effects),
                "median_oriented_improvement": median_effect,
                "bootstrap_ci95": [lo, hi],
                "tasks_improved": improved,
                "tasks_unchanged": same,
                "tasks_worsened": worse,
                "median_relative_improvement": median_relative,
                "task_effects": task_rows,
                "strata": strata_result,
            }

            md.append(
                f"| {metric} | {len(task_effects)} | {fmt(median_effect)} | "
                f"[{fmt(lo)}, {fmt(hi)}] | {improved} / {same} / {worse} | "
                f"{fmt(median_relative)} |"
            )

        effects["contrasts"][contrast_name] = contrast_result
        md.append("")

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "paired-effects.json").write_text(
        json.dumps(effects, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "paired-effects.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Analyzed {len(rows)} admissible run rows")
    print(f"Wrote {out / 'paired-effects.json'}")
    print(f"Wrote {out / 'paired-effects.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
