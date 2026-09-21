#!/usr/bin/env python3
"""Run Codex non-interactively and convert its JSONL event stream to Narness trace events.

This adapter is pilot instrumentation. It does not define benchmark semantics.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any, Iterable


READ_TOOLS = {"cat", "bat", "head", "tail", "nl"}
SEARCH_TOOLS = {"rg", "grep", "egrep", "fgrep"}
GLOB_TOOLS = {"find", "fd"}
VALIDATION_PATTERNS = (
    r"\bnpm\s+test\b",
    r"\bnpm\s+run\s+(?:build|lint|test)\b",
    r"\bnpx\s+(?:vitest|tsc|eslint)\b",
    r"\bpnpm\s+(?:test|build|lint)\b",
    r"\byarn\s+(?:test|build|lint)\b",
    r"\bcargo\s+(?:test|check|clippy)\b",
    r"\bgo\s+test\b",
)


def now_ms(origin: float) -> int:
    return round((time.monotonic() - origin) * 1000)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def unwrap_shell(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        return command
    if len(parts) >= 3 and parts[0] in {"bash", "sh", "zsh"} and parts[1] in {"-lc", "-c"}:
        return parts[2]
    return command


def first_simple_command(command: str) -> tuple[str | None, list[str]]:
    inner = unwrap_shell(command)
    # Classification only: use the first shell segment and avoid executing/parsing shell grammar.
    segment = re.split(r"\s*(?:&&|\|\||;|\|)\s*", inner, maxsplit=1)[0]
    try:
        parts = shlex.split(segment)
    except ValueError:
        return None, []
    if not parts:
        return None, []
    return Path(parts[0]).name, parts[1:]


def non_option_args(args: Iterable[str]) -> list[str]:
    out: list[str] = []
    skip_next = False
    for value in args:
        if skip_next:
            skip_next = False
            continue
        if value in {"-n", "--lines", "-c", "--bytes", "-m", "--max-count", "-A", "-B", "-C"}:
            skip_next = True
            continue
        if value.startswith("-"):
            continue
        out.append(value)
    return out


def infer_read_paths(command: str) -> list[str]:
    tool, args = first_simple_command(command)
    if not tool:
        return []
    if tool in READ_TOOLS:
        return non_option_args(args)
    if tool == "sed":
        vals = non_option_args(args)
        # sed's first non-option is normally the script; remaining values are files.
        return vals[1:] if len(vals) > 1 else []
    if tool == "git" and len(args) >= 2 and args[0] == "show":
        candidate = args[-1]
        if ":" in candidate and not candidate.startswith(":"):
            return [candidate.split(":", 1)[1]]
    return []


def classify_command(command: str) -> str | None:
    inner = unwrap_shell(command)
    if ".ai-native/resolve.mjs" in inner:
        return "resolver"
    if any(re.search(pattern, inner) for pattern in VALIDATION_PATTERNS):
        return "validation"

    tool, args = first_simple_command(command)
    if tool in SEARCH_TOOLS:
        if tool == "rg" and "--files" in args:
            return "glob"
        return "search"
    if tool in GLOB_TOOLS:
        return "glob"
    if tool == "git" and args and args[0] in {"grep"}:
        return "search"
    if tool == "git" and args and args[0] in {"ls-files"}:
        return "glob"
    if tool == "ls":
        return "glob"
    return None


def collect_paths(value: Any, *, key: str | None = None) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k in {"path", "file_path", "filename"} and isinstance(v, str):
                result.append(v)
            else:
                result.extend(collect_paths(v, key=k))
    elif isinstance(value, list):
        for item in value:
            result.extend(collect_paths(item, key=key))
    return result


def emit_command_trace(
    trace: Path,
    origin: float,
    command: str,
    exit_code: int | None,
) -> None:
    base = {"ts_ms": now_ms(origin), "command": command}
    append_jsonl(trace, {"type": "command", **base, "exit_code": exit_code})

    kind = classify_command(command)
    if kind == "resolver":
        append_jsonl(trace, {"type": "resolver", **base})
    elif kind == "validation":
        append_jsonl(trace, {"type": "validation", **base, "exit_code": exit_code})
    elif kind == "search":
        append_jsonl(trace, {"type": "search", **base, "query": command})
    elif kind == "glob":
        append_jsonl(trace, {"type": "glob", **base, "pattern": command})

    for path in infer_read_paths(command):
        append_jsonl(trace, {"type": "read", "ts_ms": now_ms(origin), "path": path})


def process_codex_event(
    event: dict[str, Any],
    trace: Path,
    origin: float,
) -> None:
    event_type = event.get("type")
    if event_type == "turn.completed":
        usage = event.get("usage") or {}
        append_jsonl(
            trace,
            {
                "type": "usage",
                "ts_ms": now_ms(origin),
                "input_tokens": usage.get("input_tokens", 0),
                "cached_tokens": usage.get("cached_input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "reasoning_tokens": usage.get("reasoning_output_tokens", 0),
            },
        )
        return

    if event_type not in {"item.completed", "item.failed"}:
        return
    item = event.get("item") or {}
    item_type = item.get("type")

    if item_type == "command_execution":
        command = item.get("command")
        if isinstance(command, str):
            exit_code = item.get("exit_code")
            if not isinstance(exit_code, int):
                exit_code = None
            emit_command_trace(trace, origin, command, exit_code)
        return

    if item_type == "file_change":
        paths = sorted(set(collect_paths(item)))
        append_jsonl(
            trace,
            {
                "type": "edit",
                "ts_ms": now_ms(origin),
                "paths": paths,
                "operation": "codex-file-change",
            },
        )
        return

    if item_type == "web_search":
        append_jsonl(
            trace,
            {
                "type": "external-search",
                "ts_ms": now_ms(origin),
                "query": item.get("query"),
            },
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("NARNESS_CODEX_MODEL", "gpt-5.6-sol"))
    ap.add_argument("--effort", default=os.environ.get("NARNESS_CODEX_EFFORT", "high"))
    ap.add_argument("--codex-bin", default=os.environ.get("NARNESS_CODEX_BIN", "codex"))
    ap.add_argument("--network", action="store_true")
    args = ap.parse_args()

    run_dir = Path(os.environ["NARNESS_RUN_DIR"]).resolve()
    prompt_file = Path(os.environ["NARNESS_PROMPT_FILE"]).resolve()
    trace = Path(os.environ["NARNESS_TRACE_FILE"]).resolve()
    raw = run_dir / "codex.raw.jsonl"
    stderr_path = run_dir / "codex.stderr.log"
    prompt = prompt_file.read_text(encoding="utf-8")

    trace.parent.mkdir(parents=True, exist_ok=True)
    trace.write_text("", encoding="utf-8")
    raw.write_text("", encoding="utf-8")

    cmd = [
        args.codex_bin,
        "exec",
        "--ephemeral",
        "--json",
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "--ignore-user-config",
        "--ignore-rules",
        "--model",
        args.model,
        "--config",
        f'model_reasoning_effort="{args.effort}"',
    ]
    if args.network:
        cmd.extend(["--config", "sandbox_workspace_write.network_access=true"])
    else:
        cmd.extend(["--config", "sandbox_workspace_write.network_access=false"])
    cmd.append(prompt)

    origin = time.monotonic()
    append_jsonl(
        trace,
        {
            "type": "agent-config",
            "ts_ms": 0,
            "agent": "codex-cli",
            "model": args.model,
            "reasoning_effort": args.effort,
            "network": args.network,
            "command": shlex.join(cmd[:-1] + ["<TASK_PROMPT>"]),
        },
    )

    with stderr_path.open("w", encoding="utf-8") as stderr_fh:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=stderr_fh,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            raw_line = line.rstrip("\n")
            with raw.open("a", encoding="utf-8") as raw_fh:
                raw_fh.write(raw_line + "\n")
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                append_jsonl(
                    trace,
                    {
                        "type": "adapter-warning",
                        "ts_ms": now_ms(origin),
                        "message": "non-JSON stdout line from codex",
                    },
                )
                continue
            if isinstance(event, dict):
                process_codex_event(event, trace, origin)

        rc = proc.wait()

    append_jsonl(
        trace,
        {
            "type": "agent-exit",
            "ts_ms": now_ms(origin),
            "exit_code": rc,
        },
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
