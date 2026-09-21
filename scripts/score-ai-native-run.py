#!/usr/bin/env python3
"""Score one AI-native repository experiment run from a structured JSONL trace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_trace(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            event = json.loads(raw)
            if not isinstance(event, dict) or "type" not in event:
                raise ValueError(f"invalid trace event on line {line_no}")
            event["_line"] = line_no
            events.append(event)
    return events


def matches(path: str, patterns: list[str]) -> bool:
    normalized = path.lstrip("./")
    for pattern in patterns:
        p = pattern.lstrip("./")
        if p.endswith("/"):
            if normalized.startswith(p):
                return True
        elif normalized == p or normalized.startswith(p + "/"):
            return True
    return False


def classify(path: str, gold: dict[str, Any]) -> str:
    if matches(path, gold.get("primary", [])):
        return "primary"
    if matches(path, gold.get("relevant", [])):
        return "relevant"
    if matches(path, gold.get("adjacent", [])):
        return "adjacent"
    return "irrelevant"


def timestamp(event: dict[str, Any]) -> float | None:
    value = event.get("ts_ms")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def delta_ms(first: dict[str, Any] | None, origin: float | None) -> float | None:
    if first is None or origin is None:
        return None
    t = timestamp(first)
    return None if t is None else max(0.0, t - origin)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--treatment", required=True, choices=["A", "B", "C"])
    ap.add_argument("--trace", type=Path)
    ap.add_argument("--update-run-json", action="store_true")
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    trace_path = (args.trace or (run_dir / "trace.jsonl")).resolve()
    trace = load_trace(trace_path)
    all_gold = load_json(args.gold.resolve())
    run_record = load_json(run_dir / "run.json")
    task_id = run_record["task_id"]

    task_gold = all_gold["tasks"][task_id]
    gold = task_gold["treatments"].get(args.treatment, task_gold["treatments"].get("default", {}))

    reads = [e for e in trace if e["type"] == "read" and isinstance(e.get("path"), str)]
    edits = [e for e in trace if e["type"] == "edit"]
    searches = [e for e in trace if e["type"] == "search"]
    globs = [e for e in trace if e["type"] == "glob"]
    resolvers = [e for e in trace if e["type"] == "resolver"]
    validations = [e for e in trace if e["type"] == "validation"]
    usage = [e for e in trace if e["type"] == "usage"]

    classified_reads = [
        {"path": e["path"], "class": classify(e["path"], gold), "line": e["_line"]}
        for e in reads
    ]
    counts = {k: 0 for k in ("primary", "relevant", "adjacent", "irrelevant")}
    for item in classified_reads:
        counts[item["class"]] += 1

    useful_reads = counts["primary"] + counts["relevant"]
    all_reads = len(reads)
    first_artifact = reads[0] if reads else None
    first_relevant = next(
        (e for e in reads if classify(e["path"], gold) in {"primary", "relevant"}),
        None,
    )
    first_edit = edits[0] if edits else None
    timed_events = [timestamp(e) for e in trace if timestamp(e) is not None]
    origin = min(timed_events) if timed_events else None

    required = gold.get("required_artifacts", gold.get("primary", []))
    hit_required: list[str] = []
    missed_required: list[str] = []
    read_paths = [e["path"] for e in reads]
    for item in required:
        if any(matches(p, [item]) for p in read_paths):
            hit_required.append(item)
        else:
            missed_required.append(item)

    search_result_total = 0
    search_result_irrelevant = 0
    for event in searches:
        results = event.get("results")
        if not isinstance(results, list):
            continue
        for result in results:
            path = result if isinstance(result, str) else result.get("path") if isinstance(result, dict) else None
            if isinstance(path, str):
                search_result_total += 1
                if classify(path, gold) == "irrelevant":
                    search_result_irrelevant += 1

    edited_paths: list[str] = []
    for event in edits:
        paths = event.get("paths")
        if isinstance(paths, list):
            edited_paths.extend(p for p in paths if isinstance(p, str))
        elif isinstance(event.get("path"), str):
            edited_paths.append(event["path"])
    allowed_edits = gold.get("allowed_edit_prefixes", gold.get("primary", []) + gold.get("relevant", []))
    out_of_scope_edits = sorted({p for p in edited_paths if not matches(p, allowed_edits)})

    input_tokens = sum(int(e.get("input_tokens", 0) or 0) for e in usage)
    output_tokens = sum(int(e.get("output_tokens", 0) or 0) for e in usage)
    reasoning_tokens = sum(int(e.get("reasoning_tokens", 0) or 0) for e in usage)
    cached_tokens = sum(int(e.get("cached_tokens", 0) or 0) for e in usage)

    failed_validations = [e for e in validations if int(e.get("exit_code", 0) or 0) != 0]
    repair_loops = 0
    for failed in failed_validations:
        failed_line = failed["_line"]
        if any(edit["_line"] > failed_line for edit in edits):
            repair_loops += 1

    metrics = {
        "trace_events": len(trace),
        "search_calls": len(searches),
        "glob_calls": len(globs),
        "resolver_calls": len(resolvers),
        "files_read": all_reads,
        "unique_files_read": len(set(read_paths)),
        "primary_reads": counts["primary"],
        "relevant_reads": counts["relevant"],
        "adjacent_reads": counts["adjacent"],
        "irrelevant_files_read": counts["irrelevant"],
        "navigation_precision": (useful_reads / all_reads) if all_reads else None,
        "navigation_recall": (len(hit_required) / len(required)) if required else None,
        "search_noise": (counts["irrelevant"] / all_reads) if all_reads else None,
        "search_result_false_positive_rate": (
            search_result_irrelevant / search_result_total
        ) if search_result_total else None,
        "first_hit_correct": (
            classify(first_artifact["path"], gold) in {"primary", "relevant"}
        ) if first_artifact else None,
        "time_to_first_relevant_artifact_ms": delta_ms(first_relevant, origin),
        "time_to_first_edit_ms": delta_ms(first_edit, origin),
        "important_artifacts_missed": missed_required,
        "patch_count": len(edits),
        "out_of_scope_edits": out_of_scope_edits,
        "validation_failures": len(failed_validations),
        "repair_loops": repair_loops,
        "input_tokens": input_tokens or None,
        "output_tokens": output_tokens or None,
        "reasoning_tokens": reasoning_tokens or None,
        "cached_tokens": cached_tokens or None,
    }

    scored = {
        "schema_version": 1,
        "run_id": run_record["run_id"],
        "task_id": task_id,
        "treatment": args.treatment,
        "metrics": metrics,
        "read_classification": classified_reads,
    }
    (run_dir / "score.json").write_text(
        json.dumps(scored, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if args.update_run_json:
        run_record["metrics"] = metrics
        run_record["trace_complete"] = True
        (run_dir / "run.json").write_text(
            json.dumps(run_record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(scored, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
