#!/usr/bin/env python3
"""Generate a research-report draft from frozen experiment metadata and formal results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    ROOT
    / "docs/topics/agent-native-repository-architecture/research/experiments"
    / "nession-terminal-session-reconnect-2026-09"
)

HYPOTHESES = {
    "H1 Retrieval precision": [
        ("A_vs_B", "navigation_precision"),
        ("A_vs_B", "irrelevant_files_read"),
        ("B_vs_C", "navigation_precision"),
        ("B_vs_C", "irrelevant_files_read"),
    ],
    "H2 Retrieval recall": [
        ("A_vs_B", "navigation_recall"),
        ("A_vs_B", "important_artifacts_missed_count"),
        ("B_vs_C", "navigation_recall"),
        ("B_vs_C", "important_artifacts_missed_count"),
    ],
    "H3 Context efficiency": [
        ("A_vs_B", "input_tokens"),
        ("A_vs_B", "navigation_events_before_first_edit"),
        ("A_vs_B", "time_to_first_edit_ms"),
        ("B_vs_C", "input_tokens"),
        ("B_vs_C", "navigation_events_before_first_edit"),
        ("B_vs_C", "time_to_first_edit_ms"),
    ],
    "H4 Change quality": [
        ("A_vs_B", "task_success"),
        ("A_vs_B", "repair_loops"),
        ("A_vs_B", "validation_failures"),
        ("B_vs_C", "task_success"),
        ("B_vs_C", "repair_loops"),
        ("B_vs_C", "validation_failures"),
    ],
    "H5 End-to-end productivity": [
        ("A_vs_C", "task_success"),
        ("A_vs_C", "agent_duration_ms"),
        ("A_vs_C", "input_tokens"),
    ],
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def effect_cell(effects: dict[str, Any], contrast: str, metric: str) -> str:
    row = effects.get("contrasts", {}).get(contrast, {}).get(metric)
    if not row:
        return "—"
    ci = row.get("bootstrap_ci95") or [None, None]
    return (
        f"{fmt(row.get('median_oriented_improvement'))} "
        f"[{fmt(ci[0])}, {fmt(ci[1])}] "
        f"(n={row.get('matched_tasks', 0)})"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT)
    ap.add_argument("--conclusions", type=Path)
    args = ap.parse_args()

    experiment = args.experiment_root.resolve()
    results = args.results_dir.resolve()

    benchmark = load(experiment / "BENCHMARK-LOCK.json")
    analysis = load(experiment / "ANALYSIS-LOCK.json")
    strata = load(experiment / "analysis-strata.json")
    summary = load(results / "summary.json")
    effects = load(results / "paired-effects.json")
    failure_path = results / "failure-summary.json"
    failures = load(failure_path) if failure_path.exists() else None
    conclusions = load(args.conclusions.resolve()) if args.conclusions else None

    total_runs = sum(int(summary.get(t, {}).get("n", 0) or 0) for t in ("A", "B", "C"))

    lines = [
        "# AI-Native Repository Architecture: Nession Reconnect Experiment",
        "",
        "> Generated research-report draft.",
        "> Hypothesis classifications and architecture graduation decisions require explicit review against ANALYSIS-PLAN.md.",
        "",
        "## Abstract",
        "",
        (
            "This controlled repository experiment compares a baseline codebase (A), "
            "the same codebase with a deterministic semantic capability index (B), and "
            "a behavior-localized agent-native structure using the same semantic layer "
            "(C). The subject is Nession's terminal/session reconnect workflow. "
            f"The current result set contains {total_runs} sealed admissible runs."
        ),
        "",
        "## Frozen design",
        "",
        f"- benchmark revision: {benchmark['benchmark_revision']}",
        f"- benchmark definition SHA: {benchmark['definition_sha']}",
        f"- analysis revision: {analysis['analysis_revision']}",
        f"- analysis definition SHA: {analysis['definition_sha']}",
        f"- Treatment A: {benchmark['treatments']['A']}",
        f"- Treatment B: {benchmark['treatments']['B']}",
        f"- Treatment C: {benchmark['treatments']['C']}",
        f"- hidden oracle: {benchmark['hidden_oracle_sha']}",
        "",
        "The benchmark uses 24 matched tasks and fresh isolated agent runs. Formal treatment order is pre-registered and balanced within each task. Failed but admissible runs remain in the dataset.",
        "",
        "## Treatments",
        "",
        "- **A — baseline:** original repository topology and ordinary repository search/tooling.",
        "- **B — semantic index:** A plus stable capability identities and a deterministic resolver; production topology remains materially unchanged.",
        "- **C — agent-native structure:** the same semantic layer as B plus behavior-oriented canonical ownership and localized evidence for the selected reconnect slice.",
        "",
        "## Task strata",
        "",
    ]

    for klass, tasks in strata["task_classes"].items():
        lines.append(f"- **{klass}:** {', '.join(tasks)}")

    lines.extend([
        "",
        "## Analysis method",
        "",
        "The primary unit of analysis is the task. Numeric repetitions are reduced to per-task/treatment medians; boolean repetitions become per-task proportions. Treatment effects are paired within task. Positive oriented effects mean the second treatment in the contrast is better. Uncertainty uses 10,000 task-cluster bootstrap resamples with seed 20260921.",
        "",
        "## Dataset completeness",
        "",
        "| Treatment | Sealed runs | Distinct tasks | Success rate |",
        "|---|---:|---:|---:|",
    ])

    for treatment in ("A", "B", "C"):
        row = summary.get(treatment, {})
        lines.append(
            f"| {treatment} | {row.get('n', 0)} | {row.get('tasks', 0)} | "
            f"{fmt(row.get('task_success_rate'))} |"
        )

    lines.extend([
        "",
        "## Primary paired effects",
        "",
        "Values are median oriented improvement with 95% task-bootstrap interval.",
        "",
        "| Metric | A→B | B→C | A→C |",
        "|---|---:|---:|---:|",
    ])

    primary_metrics = [
        "task_success",
        "navigation_precision",
        "navigation_recall",
        "irrelevant_files_read",
        "navigation_events_before_first_edit",
        "input_tokens",
        "repair_loops",
        "validation_failures",
        "agent_duration_ms",
    ]
    for metric in primary_metrics:
        lines.append(
            f"| {metric} | {effect_cell(effects, 'A_vs_B', metric)} | "
            f"{effect_cell(effects, 'B_vs_C', metric)} | "
            f"{effect_cell(effects, 'A_vs_C', metric)} |"
        )

    lines.extend([
        "",
        "## Hypothesis evidence",
        "",
        "Classification must be filled as exactly one of Supported, Partially supported, Not supported, or Inconclusive after applying the frozen practical-effect and uncertainty rules.",
        "",
        "| Hypothesis | Evidence snapshot | Classification |",
        "|---|---|---|",
    ])

    for hypothesis, refs in HYPOTHESES.items():
        evidence = "; ".join(
            f"{contrast}:{metric}={effect_cell(effects, contrast, metric)}"
            for contrast, metric in refs
        )
        hypothesis_id = hypothesis.split(" ", 1)[0]
        classification = "**REVIEW REQUIRED**"
        if conclusions is not None:
            classification = conclusions["hypotheses"][hypothesis_id]["classification"]
        lines.append(f"| {hypothesis} | {evidence} | {classification} |")

    lines.extend([
        "",
        "## Treatment attribution",
        "",
        "- A → B: semantic resolution / addressability",
        "- B → C: physical code shape / behavior locality beyond metadata",
        "- A → C: complete treatment effect",
        "",
        "An A→C gain alone is insufficient to attribute the cause when A→B and B→C disagree.",
        "",
        "## Construction cost",
        "",
        "Treatment C migration cost is a real architectural cost and must be reported alongside per-task productivity effects. See treatments/C-construction.md.",
        "",
        "## Failure analysis",
        "",
    ])

    if failures is None:
        lines.extend([
            "Failure taxonomy aggregation is not available yet.",
            "",
        ])
    else:
        lines.extend([
            f"Failed admissible runs: {failures.get('failed_admissible_runs', 0)}.",
            f"Reviewed failed runs: {failures.get('reviewed_failed_runs', 0)}.",
            f"Missing failure reviews: {failures.get('missing_review_count', 0)}.",
            "",
            "| Code | Failure class | Count |",
            "|---|---|---:|",
        ])
        for code, item in failures.get("primary_failures", {}).items():
            lines.append(
                f"| {code} | {item.get('label', '')} | {item.get('count', 0)} |"
            )
        lines.append("")

    lines.extend([
        "## Limitations",
        "",
        "- one repository and one bounded cross-cutting workflow;",
        "- one coding-agent/model execution profile per revision;",
        "- semantic resolver availability is measured as a treatment, not forced usage;",
        "- task fixtures are controlled benchmark instances;",
        "- backend/model drift is mitigated by matched tasks and balanced treatment order, not eliminated;",
        "- Treatment C includes one-time migration/maintenance cost not automatically amortized by per-task run metrics.",
        "",
        "## Conclusion",
        "",
    ])

    if conclusions is None:
        lines.extend([
            "No conclusion is inserted mechanically. Complete H1–H5 classifications against the frozen analysis plan, record negative and mixed findings, then state which repository ideas have enough evidence to graduate into canonical Narness architecture and which remain experimental.",
            "",
        ])
    else:
        lines.extend([
            conclusions.get("overall_summary", ""),
            "",
            "### Hypothesis rationales",
            "",
        ])
        for key in ("H1", "H2", "H3", "H4", "H5"):
            item = conclusions["hypotheses"][key]
            lines.extend([
                f"#### {key} — {item['classification']}",
                "",
                item["rationale"],
                "",
            ])
        lines.extend([
            "### Architecture decisions",
            "",
        ])
        for item in conclusions.get("architecture_decisions", []):
            lines.append(
                f"- **{item['idea']} — {item['decision']}**: {item['rationale']}"
            )
        lines.append("")
        if conclusions.get("limitations"):
            lines.extend(["### Additional limitations", ""])
            for limitation in conclusions["limitations"]:
                lines.append(f"- {limitation}")
            lines.append("")

    lines.extend([
        "## Reproducibility",
        "",
        "The benchmark, treatment SHAs, hidden oracle, analysis definition, raw run data, paired effects, and execution profile together define the reproducible research artifact. Finalization additionally writes `research-artifact-manifest.json`, which content-addresses the research inputs and generated outputs without claiming a cryptographic signature.",
        "",
    ])

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote research report draft: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
