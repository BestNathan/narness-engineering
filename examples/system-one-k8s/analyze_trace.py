#!/usr/bin/env python3
"""Summarize a System One Kubernetes experiment trace for CI artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
    return events


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze(events: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    frontiers = [
        event["data"]
        for event in events
        if event.get("event") == "frontier_compiled"
    ]
    selections = [
        event["data"]
        for event in events
        if event.get("event") == "action_selected"
    ]
    observations = [
        event["data"]
        for event in events
        if event.get("event") == "observation_recorded"
    ]
    exchanges = [
        event["data"]
        for event in events
        if event.get("event") == "model_exchange"
    ]

    model_selections = [
        item for item in selections if item.get("source") == "typesafe-system-one"
    ]
    deterministic_selections = [
        item
        for item in selections
        if item.get("source") == "deterministic-single-candidate"
    ]

    latencies = [
        item["latency_ms"]
        for item in model_selections
        if isinstance(item.get("latency_ms"), (int, float))
    ]
    confidences = [
        item["confidence"]
        for item in model_selections
        if isinstance(item.get("confidence"), (int, float))
    ]

    input_tokens = 0
    output_tokens = 0
    for item in model_selections:
        usage = item.get("usage") or {}
        input_tokens += int(usage.get("input_tokens", 0) or 0)
        output_tokens += int(usage.get("output_tokens", 0) or 0)

    return {
        "goal": state.get("goal"),
        "result": state.get("phase"),
        "blocked_reason": state.get("blocked_reason"),
        "selected_namespace": state.get("selected_namespace"),
        "final_command": state.get("final_command"),
        "event_count": len(events),
        "decision_count": len(selections),
        "system_one_call_count": len(model_selections),
        "deterministic_short_circuit_count": len(deterministic_selections),
        "observation_count": len(observations),
        "frontier_count": len(frontiers),
        "frontier_sizes": [item.get("size", 0) for item in frontiers],
        "max_frontier_size": max(
            [item.get("size", 0) for item in frontiers],
            default=0,
        ),
        "selected_actions": [item.get("action_id") for item in selections],
        "system_one": {
            "models": sorted(
                {
                    item["model"]
                    for item in model_selections
                    if item.get("model")
                }
            ),
            "latency_ms": latencies,
            "mean_latency_ms": round(mean(latencies), 2) if latencies else None,
            "confidence": confidences,
            "mean_confidence": round(mean(confidences), 4) if confidences else None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "captured_exchange_count": len(exchanges),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    command = report.get("final_command") or []
    command_text = " ".join(command) if command else "-"
    frontier_sizes = ", ".join(str(item) for item in report["frontier_sizes"]) or "-"
    actions = "\n".join(
        f"{index}. {action}"
        for index, action in enumerate(report["selected_actions"], start=1)
    ) or "None"
    system_one = report["system_one"]

    return f"""# System One Kubernetes experiment

| Metric | Value |
|---|---|
| Result | {report.get("result")} |
| Goal | {report.get("goal") or "-"} |
| Selected namespace | {report.get("selected_namespace") or "-"} |
| Final command | {command_text} |
| Runtime events | {report["event_count"]} |
| Decisions | {report["decision_count"]} |
| Deterministic short-circuits | {report["deterministic_short_circuit_count"]} |
| System One calls | {report["system_one_call_count"]} |
| Observations | {report["observation_count"]} |
| Frontier sizes | {frontier_sizes} |
| Max frontier size | {report["max_frontier_size"]} |
| Mean System One latency | {system_one["mean_latency_ms"] if system_one["mean_latency_ms"] is not None else "-"} ms |
| Mean System One confidence | {system_one["mean_confidence"] if system_one["mean_confidence"] is not None else "-"} |
| System One input tokens | {system_one["input_tokens"]} |
| System One output tokens | {system_one["output_tokens"]} |

## Selected actions

{actions}

## Analysis notes

- A decision whose source is deterministic-single-candidate did not call the model.
- frontier_sizes shows how much of the dynamic environment was disclosed at each step.
- Real TypeSafe runs include model, confidence, probability distribution, token usage, request/response bodies, and latency in the JSONL trace.
- The API key is never written to the trace.
- The final command is deterministic lowering from grounded state, not free-form model text.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    trace_path = Path(args.trace)
    state_path = Path(args.state)
    report = analyze(load_jsonl(trace_path), load_json(state_path))

    json_path = Path(args.json_output)
    markdown_path = Path(args.markdown_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
