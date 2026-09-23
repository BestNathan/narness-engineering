#!/usr/bin/env python3
"""Extract a normalized Claude Code localization trace from stream-json."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def text_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            item.get("text", "")
            for item in value
            if isinstance(item, dict)
        )
    return json.dumps(value, ensure_ascii=False)


def strip_json_fence(value):
    value = value.strip()
    if value.startswith("~~~") or value.startswith("```"):
        value = re.sub(r"^(?:~~~|```)(?:json)?\s*", "", value)
        value = re.sub(r"\s*(?:~~~|```)$", "", value)
    return value.strip()


def normalize_tool_input(name, payload, subject_root):
    payload = dict(payload or {})
    root = str(subject_root.resolve())

    def rel(value):
        if not isinstance(value, str):
            return value
        if value.startswith(root + "/"):
            return value[len(root) + 1 :]
        return value.removeprefix("./")

    if name == "Read":
        for key in ("file_path", "path"):
            if key in payload:
                payload[key] = rel(payload[key])
    elif name in ("Glob", "Grep"):
        if "path" in payload:
            payload["path"] = rel(payload["path"])
    return payload


def step_label(step):
    tool = step.get("tool")
    args = step.get("input", {})
    if tool == "Read":
        target = args.get("file_path") or args.get("path") or ""
        offset = args.get("offset")
        limit = args.get("limit")
        suffix = ""
        if offset is not None or limit is not None:
            suffix = f" offset={offset} limit={limit}"
        return f"Read {target}{suffix}".strip()
    if tool == "Glob":
        return f"Glob pattern={args.get('pattern')} path={args.get('path', '.')}"
    if tool == "Grep":
        return f"Grep pattern={args.get('pattern')} path={args.get('path', '.')}"
    if tool == "Bash":
        command = str(args.get("command", "")).replace("\n", " ")
        return f"Bash {command[:240]}"
    return str(tool)


def parse_stream(raw_path, subject_root):
    steps = []
    pending = {}
    seen_tool_ids = set()
    assistant_text = []
    terminal = None

    for line_number, line in enumerate(
        Path(raw_path).read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if not line.strip():
            continue
        event = json.loads(line)
        kind = event.get("type")

        if kind == "assistant":
            message = event.get("message", {})
            for block in message.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type == "text":
                    value = block.get("text", "")
                    if value:
                        assistant_text.append(value)
                elif block_type == "tool_use":
                    tool_id = block.get("id")
                    if not tool_id or tool_id in seen_tool_ids:
                        continue
                    seen_tool_ids.add(tool_id)
                    step = {
                        "sequence": len(steps) + 1,
                        "tool_use_id": tool_id,
                        "tool": block.get("name"),
                        "input": normalize_tool_input(
                            block.get("name"),
                            block.get("input") or {},
                            subject_root,
                        ),
                        "stream_line": line_number,
                        "is_error": None,
                        "result_chars": None,
                        "result_lines": None,
                        "result_preview": None,
                    }
                    steps.append(step)
                    pending[tool_id] = step

        elif kind == "user":
            message = event.get("message", {})
            for block in message.get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_id = block.get("tool_use_id")
                step = pending.pop(tool_id, None)
                if step is None:
                    continue
                value = text_content(block.get("content", ""))
                step["is_error"] = bool(block.get("is_error"))
                step["result_chars"] = len(value)
                step["result_lines"] = len(value.splitlines())
                step["result_preview"] = value[:1200]

        elif kind == "result":
            terminal = event

    final_text = None
    if terminal and isinstance(terminal.get("result"), str):
        final_text = terminal["result"]
    elif assistant_text:
        final_text = assistant_text[-1]

    if not final_text:
        raise RuntimeError("Claude stream did not contain a final text result")

    return steps, terminal or {}, final_text


def validate_reference(reference, subject_root):
    if not isinstance(reference.get("relevant_files"), list):
        raise RuntimeError("Claude reference omitted relevant_files")

    seen = set()
    for item in reference["relevant_files"]:
        path = item.get("path")
        if (
            not isinstance(path, str)
            or path.startswith("/")
            or path.startswith("../")
        ):
            raise RuntimeError(f"invalid reference path: {path!r}")
        if path in seen:
            raise RuntimeError(f"duplicate reference path: {path}")
        seen.add(path)
        if item.get("relevance") not in {"primary", "supporting", "context"}:
            raise RuntimeError(f"invalid relevance for {path}")
        if (
            item["relevance"] in {"primary", "supporting"}
            and not item.get("evidence")
        ):
            raise RuntimeError(f"missing evidence for {path}")
        if not (subject_root / path).is_file():
            raise RuntimeError(f"reference file does not exist: {path}")


def markdown_summary(steps, reference, terminal):
    counts = Counter(step["tool"] for step in steps)
    lines = [
        "# Claude Code localization execution path",
        "",
        "This artifact records what Claude Code did. It is not treated as ground truth.",
        "",
        "## Run summary",
        "",
        f"- Tool calls: {len(steps)}",
        f"- Reads: {counts.get('Read', 0)}",
        f"- Greps: {counts.get('Grep', 0)}",
        f"- Globs: {counts.get('Glob', 0)}",
        f"- Bash calls: {counts.get('Bash', 0)}",
        f"- Relevant files in final answer: {len(reference.get('relevant_files', []))}",
        f"- Turns: {terminal.get('num_turns')}",
        f"- Duration ms: {terminal.get('duration_ms')}",
        "",
        "## Ordered tool path",
        "",
    ]
    lines += [
        f"{step['sequence']}. {step_label(step)}"
        + (" [error]" if step.get("is_error") else "")
        for step in steps
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-jsonl", required=True)
    parser.add_argument("--subject-root", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--subject-sha", required=True)
    parser.add_argument("--output-reference", required=True)
    parser.add_argument("--output-trace", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--output-summary", required=True)
    args = parser.parse_args(argv)

    subject_root = Path(args.subject_root).resolve()
    steps, terminal, final_text = parse_stream(
        args.raw_jsonl,
        subject_root,
    )
    reference = json.loads(strip_json_fence(final_text))
    validate_reference(reference, subject_root)

    trace = {
        "schema_version": 1,
        "kind": "claude-code-localization-execution-path",
        "query": args.query,
        "model": args.model,
        "subject_sha": args.subject_sha,
        "steps": steps,
    }
    counts = Counter(step["tool"] for step in steps)
    manifest = {
        "schema_version": 1,
        "query": args.query,
        "model": args.model,
        "subject_sha": args.subject_sha,
        "duration_ms": terminal.get("duration_ms"),
        "duration_api_ms": terminal.get("duration_api_ms"),
        "num_turns": terminal.get("num_turns"),
        "usage": terminal.get("usage"),
        "model_usage": terminal.get("modelUsage"),
        "tool_calls": len(steps),
        "tool_counts": dict(sorted(counts.items())),
    }

    Path(args.output_reference).write_text(
        json.dumps(reference, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(args.output_trace).write_text(
        json.dumps(trace, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(args.output_manifest).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(args.output_summary).write_text(
        markdown_summary(steps, reference, terminal),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
