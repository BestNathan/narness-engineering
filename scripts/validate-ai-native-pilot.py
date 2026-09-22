#!/usr/bin/env python3
"""Validate one non-reportable instrumentation pilot run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


NAV_TYPES = {"search", "glob", "read", "resolver"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: event must be an object")
        events.append(value)
    return events


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--require-resolver", action="store_true")
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    errors: list[str] = []

    for required in ("run.json", "trace.jsonl", "score.json", "final.diff"):
        if not (run_dir / required).exists():
            fail(f"missing artifact: {required}", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    run = load_json(run_dir / "run.json")
    score = load_json(run_dir / "score.json")
    trace = load_jsonl(run_dir / "trace.jsonl")
    config = next((e for e in trace if e.get("type") == "agent-config"), {})
    raw_name = "claude.raw.jsonl" if config.get("agent") == "claude-code" else "codex.raw.jsonl"
    if not (run_dir / raw_name).exists():
        print(f"ERROR: missing artifact: {raw_name}")
        return 1
    raw = load_jsonl(run_dir / raw_name)

    types = [event.get("type") for event in trace]

    if not run.get("trace_present"):
        fail("run.json does not report a present structured trace", errors)
    if not raw:
        fail("raw agent JSONL is empty", errors)
    if not any(t in NAV_TYPES for t in types):
        fail("no navigation event captured", errors)
    if "edit" not in types:
        fail("no edit event captured", errors)
    usage_count = types.count("usage")
    if usage_count == 0:
        fail("no usage event captured", errors)
    elif usage_count != 1:
        fail(
            f"expected exactly one usage event for one fresh agent task; "
            f"captured {usage_count}",
            errors,
        )
    if "agent-exit" not in types:
        fail("no agent-exit event captured", errors)
    if args.require_resolver and "resolver" not in types:
        fail("treatment expected resolver use but no resolver event was captured", errors)

    commands = run.get("commands", {})
    agent = commands.get("agent")
    if not isinstance(agent, dict):
        fail("agent command record missing", errors)
    else:
        agent_end = float(agent.get("started_at_unix", 0)) + float(agent.get("duration_ms", 0)) / 1000.0
        installs = commands.get("oracle_install", [])
        for install in installs:
            installed_at = install.get("installed_at_unix")
            if installed_at is None:
                fail("oracle install has no timestamp; cannot prove post-agent timing", errors)
            elif float(installed_at) < agent_end:
                fail("hidden oracle was materialized before the agent exited", errors)

    if not commands.get("acceptance"):
        fail("acceptance commands were not recorded", errors)
    if not commands.get("verification"):
        fail("verification commands were not recorded", errors)

    metrics = score.get("metrics", {})
    if metrics.get("trace_events", 0) <= 0:
        fail("score contains no trace events", errors)
    if metrics.get("input_tokens") is None:
        fail("input token usage was not captured", errors)
    if metrics.get("output_tokens") is None:
        fail("output token usage was not captured", errors)
    if metrics.get("patch_count", 0) <= 0:
        fail("score contains no edit/patch event", errors)

    required_analysis_metrics = (
        "navigation_events_before_first_edit",
        "search_calls_before_first_edit",
        "files_read_before_first_edit",
        "important_artifacts_missed_count",
        "out_of_scope_edit_count",
        "validation_failures",
    )
    for metric in required_analysis_metrics:
        if metrics.get(metric) is None:
            fail(f"score is missing preregistered analysis metric: {metric}", errors)

    if errors:
        print("Instrumentation pilot FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Instrumentation pilot OK")
    print(f"  run: {run.get('run_id')}")
    print(f"  task_success: {run.get('task_success')}")
    print(f"  trace_events: {metrics.get('trace_events')}")
    print(f"  navigation: search={metrics.get('search_calls')} glob={metrics.get('glob_calls')} resolver={metrics.get('resolver_calls')} reads={metrics.get('files_read')}")
    print(f"  tokens: input={metrics.get('input_tokens')} output={metrics.get('output_tokens')} reasoning={metrics.get('reasoning_tokens')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
