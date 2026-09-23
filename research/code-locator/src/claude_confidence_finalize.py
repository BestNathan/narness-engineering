#!/usr/bin/env python3
"""Finalize a Claude localization draft using a fresh confidence-only session."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from claude_reference_trace import parse_stream, strip_json_fence
from localization_result import (
    build_claude_result,
    claude_stage_cost,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--confidence-raw-jsonl", required=True)
    parser.add_argument("--localization-manifest", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--subject-sha", required=True)
    parser.add_argument("--output-result", required=True)
    parser.add_argument("--output-confidence-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--output-summary", required=True)
    args = parser.parse_args(argv)

    draft = json.loads(
        Path(args.draft).read_text(encoding="utf-8")
    )
    localization_manifest = json.loads(
        Path(args.localization_manifest).read_text(encoding="utf-8")
    )

    steps, terminal, final_text = parse_stream(
        args.confidence_raw_jsonl,
        Path("."),
    )
    if steps:
        raise RuntimeError(
            "confidence session must not use repository tools"
        )

    assessment = json.loads(strip_json_fence(final_text))
    confidence_stage = claude_stage_cost(
        "confidence_assessment",
        terminal,
        0,
    )
    localization_stage = localization_manifest.get("stage_cost")
    if not isinstance(localization_stage, dict):
        raise RuntimeError(
            "localization manifest omitted stage_cost"
        )

    result = build_claude_result(
        draft,
        assessment,
        args.model,
        localization_stage,
        confidence_stage,
    )

    confidence_manifest = {
        "schema_version": 1,
        "kind": "claude-code-confidence-session",
        "query": draft["task"],
        "model": args.model,
        "subject_sha": args.subject_sha,
        "stage_cost": confidence_stage,
        "tool_calls": 0,
    }
    manifest = {
        "schema_version": 1,
        "kind": "claude-code-two-session-localization-run",
        "query": draft["task"],
        "model": args.model,
        "subject_sha": args.subject_sha,
        "localization_session": localization_manifest,
        "confidence_session": confidence_manifest,
        "cost": result["cost"],
    }

    Path(args.output_result).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(args.output_confidence_manifest).write_text(
        json.dumps(
            confidence_manifest,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    Path(args.output_manifest).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    cost = result["cost"]
    tokens = cost["tokens"]
    lines = [
        "# Claude Code two-session localization result",
        "",
        "Localization and confidence are intentionally separate sessions.",
        "",
        "## Final result",
        "",
        f"- Valuable files: {len(result['files'])}",
        f"- Evidence regions: {sum(len(item['evidence']) for item in result['files'])}",
        f"- Overall confidence: {result['confidence']['score']:.3f}",
        "",
        "## Combined cost",
        "",
        f"- Elapsed ms: {cost['elapsed_ms']}",
        f"- Turns: {cost['turns']}",
        f"- Tool calls: {cost['tool_calls']}",
        f"- Input tokens: {tokens['input']}",
        f"- Output tokens: {tokens['output']}",
        f"- Cache-read input tokens: {tokens['cache_read_input']}",
        f"- Cache-creation input tokens: {tokens['cache_creation_input']}",
        f"- Thinking tokens: {tokens['thinking']}",
        f"- Provider cost USD: {cost['provider_cost_usd']}",
        "",
        "## Stage split",
        "",
    ]
    for stage in cost["stages"]:
        lines += [
            f"### {stage['name']}",
            "",
            f"- Elapsed ms: {stage['elapsed_ms']}",
            f"- Turns: {stage['turns']}",
            f"- Tool calls: {stage['tool_calls']}",
            f"- Input tokens: {stage['tokens']['input']}",
            f"- Output tokens: {stage['tokens']['output']}",
            f"- Cache-read input tokens: {stage['tokens']['cache_read_input']}",
            f"- Provider cost USD: {stage['provider_cost_usd']}",
            "",
        ]

    Path(args.output_summary).write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
