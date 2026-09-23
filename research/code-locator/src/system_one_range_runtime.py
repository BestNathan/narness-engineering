#!/usr/bin/env python3
"""Range-only System One Harness Runtime v0.

Phase 1 locates files. Phase 2 never parses source semantics: it only manages
file lengths, covered ranges, raw observations, and a dynamic ReadRange /
StopTask action space. System One is the only semantic decision-maker.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from system_one_code_locator import (
    API_URL,
    MODEL,
    DEFAULT_DIRECTORY_THRESHOLD,
    DEFAULT_FILE_THRESHOLD,
    SystemOneDecider,
    Trace,
    directories,
    empty_usage,
    files,
    merge_ranges,
    merge_usage,
    read_range,
    sanitize_source,
    source_stat,
    unread_gaps,
)

DEFAULT_WINDOW_LINES = 140
DEFAULT_PARALLEL_THRESHOLD = 0.65
DEFAULT_MAX_JUMPS_PER_FILE = 2
DEFAULT_MAX_EPOCHS = 64


def make_action(action_id, path, start, end, navigation, reason, source=None):
    return {
        "id": action_id,
        "kind": "read_range",
        "path": path,
        "start_line": int(start),
        "end_line": int(end),
        "navigation": navigation,
        "reason": reason,
        "source": source,
    }


def range_key(start, end):
    return int(start), int(end)


def fully_uncovered(start, end, coverage):
    for left, right in merge_ranges(coverage):
        if not (end < left or start > right):
            return False
    return True


def bounded_range(start, end, line_count):
    start = max(1, int(start))
    end = min(int(line_count), int(end))
    if start > end:
        return None
    return start, end


def gap_midpoint_window(gap_start, gap_end, window_lines):
    gap_length = gap_end - gap_start + 1
    if gap_length <= window_lines:
        return gap_start, gap_end
    midpoint = (gap_start + gap_end) // 2
    start = max(gap_start, midpoint - (window_lines // 2))
    end = min(gap_end, start + window_lines - 1)
    if end - start + 1 < window_lines:
        start = max(gap_start, end - window_lines + 1)
    return start, end


def generate_file_actions(
    file_state,
    window_lines,
    max_jumps_per_file=DEFAULT_MAX_JUMPS_PER_FILE,
):
    """Generate actions from coverage geometry only; never inspect file text."""
    path = file_state["path"]
    line_count = int(file_state["line_count"])
    coverage = merge_ranges(file_state["coverage"])
    if line_count <= 0:
        return []

    actions = []
    seen = set()

    def add(start, end, navigation, reason, source=None):
        bounded = bounded_range(start, end, line_count)
        if bounded is None:
            return
        start, end = bounded
        key = range_key(start, end)
        if key in seen or not fully_uncovered(start, end, coverage):
            return
        seen.add(key)
        actions.append(
            make_action(
                f"read:{path}:{start}-{end}:{navigation}",
                path,
                start,
                end,
                navigation,
                reason,
                source,
            )
        )

    if not coverage:
        add(
            1,
            min(line_count, window_lines),
            "seed_head",
            "initial probe at the beginning of an unread file",
        )
        if line_count > window_lines:
            middle_start = max(
                1,
                (line_count // 2) - (window_lines // 2),
            )
            add(
                middle_start,
                middle_start + window_lines - 1,
                "seed_middle",
                "initial probe near the middle of an unread file",
            )
        if line_count > window_lines * 2:
            add(
                max(1, line_count - window_lines + 1),
                line_count,
                "seed_tail",
                "initial probe at the end of an unread file",
            )
        return actions

    latest = file_state.get("latest_range")
    if latest:
        start, end = latest
        add(
            start - window_lines,
            start - 1,
            "expand_before",
            "expand immediately before the most recent read range",
            {"start_line": start, "end_line": end},
        )
        add(
            end + 1,
            end + window_lines,
            "expand_after",
            "expand immediately after the most recent read range",
            {"start_line": start, "end_line": end},
        )

    gaps = unread_gaps(line_count, coverage)
    gaps = sorted(
        gaps,
        key=lambda item: (-(item[1] - item[0] + 1), item[0]),
    )[:max_jumps_per_file]
    for index, (gap_start, gap_end) in enumerate(gaps, 1):
        start, end = gap_midpoint_window(
            gap_start,
            gap_end,
            window_lines,
        )
        add(
            start,
            end,
            "jump",
            (
                f"jump to the midpoint of unread gap #{index} "
                f"{gap_start}-{gap_end}"
            ),
            {
                "gap_start": gap_start,
                "gap_end": gap_end,
                "gap_length": gap_end - gap_start + 1,
            },
        )

    return actions


def generate_action_space(
    state,
    window_lines,
    max_jumps_per_file=DEFAULT_MAX_JUMPS_PER_FILE,
):
    actions = []
    for file_state in state["files"]:
        actions.extend(
            generate_file_actions(
                file_state,
                window_lines,
                max_jumps_per_file,
            )
        )
    actions.append({
        "id": "stop_task",
        "kind": "stop_task",
        "reason": (
            "Stop only when the current evidence is sufficient and further "
            "exploration is unlikely to materially improve the result."
        ),
    })
    return actions


def decision_view(state):
    return {
        "goal": state["goal"],
        "phase": "range_runtime_v0",
        "epoch": state["epoch"],
        "files": [
            {
                "path": item["path"],
                "phase1_score": item["phase1_score"],
                "line_count": item["line_count"],
                "coverage": item["coverage"],
                "latest_range": item.get("latest_range"),
                "read_count": item["read_count"],
            }
            for item in state["files"]
        ],
        "observations": [
            {
                "id": item["id"],
                "path": item["path"],
                "start_line": item["start_line"],
                "end_line": item["end_line"],
                "content": sanitize_source(item["content"]),
                "selected_action_score": item["selected_action_score"],
                "navigation": item["navigation"],
            }
            for item in state["observations"]
        ],
        "policy": (
            "The harness does not interpret source content. Score proposed "
            "ReadRange actions by how useful the next read would be for the "
            "task. StopTask means the current evidence is already sufficient."
        ),
    }


class SystemOneRangeDecider(SystemOneDecider):
    def score_actions(self, query, state, actions):
        questions = {}
        for index, action in enumerate(actions):
            question_id = f"action_{index}"
            if action["kind"] == "stop_task":
                questions[question_id] = {
                    "type": "noul",
                    "instructions": {
                        "task": query,
                        "action": action,
                        "question": (
                            "How confident are you that no further exploration "
                            "is necessary and the current evidence is sufficient "
                            "for the localization task? If further reading is "
                            "unlikely to materially improve the result, increase "
                            "the StopTask score. If useful unexplored directions "
                            "remain, keep StopTask low."
                        ),
                    },
                    "criteria": {
                        "true": (
                            "Current evidence is sufficient; important "
                            "uncertainty is resolved; additional reads are "
                            "likely redundant."
                        ),
                        "false": (
                            "Useful unexplored directions remain or additional "
                            "reads could materially improve the result."
                        ),
                    },
                }
            else:
                questions[question_id] = {
                    "type": "noul",
                    "instructions": {
                        "task": query,
                        "action": {
                            "kind": "read_range",
                            "path": action["path"],
                            "start_line": action["start_line"],
                            "end_line": action["end_line"],
                            "navigation": action["navigation"],
                            "reason": action["reason"],
                            "source": action.get("source"),
                        },
                        "question": (
                            "Given the current state and observations, how useful "
                            "would executing this exact ReadRange be as the next "
                            "information-gathering action for the task?"
                        ),
                    },
                    "criteria": {
                        "true": (
                            "This read is a useful next exploration step and is "
                            "likely to add material information."
                        ),
                        "false": (
                            "This read is likely redundant, low-value, or less "
                            "useful than the available alternatives."
                        ),
                    },
                }

        response, usage = self.send(
            "range_runtime_action_score",
            decision_view(state),
            questions,
        )
        answers = response.get("answers", {})
        scored = []
        for index, action in enumerate(actions):
            answer = answers.get(f"action_{index}", {})
            if answer.get("type") != "noul":
                raise RuntimeError(
                    f"unexpected action-score answer: {answer!r}"
                )
            scored.append({
                **action,
                "score": float(answer["noul"]),
            })
        scored.sort(
            key=lambda item: (
                -item["score"],
                item["id"],
            )
        )
        return scored, usage


class OfflineRangeDecider:
    model = "offline-range-fixture"

    def __init__(self, trace):
        self.trace = trace

    def score_candidates(self, query, stage, candidates):
        # Keep the offline fixture deterministic and broad.
        scored = [{**item, "score": 0.9} for item in candidates]
        return scored, empty_usage()

    def score_actions(self, query, state, actions):
        scored = []
        for action in actions:
            if action["kind"] == "stop_task":
                score = 0.9 if state["observations"] else 0.1
            elif action["navigation"] in {"seed_head", "expand_after"}:
                score = 0.8
            else:
                score = 0.4
            scored.append({**action, "score": score})
        scored.sort(key=lambda item: (-item["score"], item["id"]))
        return scored, empty_usage()


def select_actions(scored_actions, parallel_threshold):
    stop = next(
        item for item in scored_actions
        if item["kind"] == "stop_task"
    )
    reads = [
        item for item in scored_actions
        if item["kind"] == "read_range"
    ]
    if not reads:
        return [stop], "action_space_exhausted"

    best_read = reads[0]
    if (
        stop["score"] >= parallel_threshold
        and stop["score"] >= best_read["score"]
    ):
        return [stop], "model_stop"

    parallel = [
        item for item in reads
        if item["score"] >= parallel_threshold
    ]
    if parallel:
        return parallel, "parallel_above_threshold"

    return [best_read], "fallback_top1"


def initial_state(query, selected_files, root):
    state_files = []
    for item in selected_files:
        stat = source_stat(root, item)
        if stat is None:
            continue
        state_files.append({
            "path": item["payload"]["path"],
            "phase1_score": item["score"],
            "line_count": stat["line_count"],
            "size_bytes": stat["size_bytes"],
            "extension": stat["extension"],
            "coverage": [],
            "latest_range": None,
            "read_count": 0,
        })
    return {
        "goal": query,
        "epoch": 0,
        "files": state_files,
        "observations": [],
        "action_history": [],
        "termination": None,
    }


def apply_read(state, root, action):
    observation = read_range(root, action)
    file_state = next(
        item for item in state["files"]
        if item["path"] == action["path"]
    )
    file_state["coverage"] = [
        list(item)
        for item in merge_ranges([
            *file_state["coverage"],
            (
                observation["start_line"],
                observation["end_line"],
            ),
        ])
    ]
    file_state["latest_range"] = [
        observation["start_line"],
        observation["end_line"],
    ]
    file_state["read_count"] += 1

    item = {
        "id": (
            f"{observation['path']}:{observation['start_line']}-"
            f"{observation['end_line']}#{len(state['observations']) + 1}"
        ),
        **observation,
        "navigation": action["navigation"],
        "selected_action_score": action["score"],
    }
    state["observations"].append(item)
    return item


def run_phase1(
    root,
    query,
    decider,
    trace,
    directory_threshold,
    file_threshold,
):
    usage = empty_usage()
    directory_candidates = directories(root)
    scored_directories, current = decider.score_candidates(
        query,
        "directory",
        directory_candidates,
    )
    merge_usage(usage, current)
    selected_directories = [
        item
        for item in scored_directories
        if item["score"] >= directory_threshold
    ]
    trace.emit(
        "phase1_directory_selected",
        exposed=len(directory_candidates),
        selected=len(selected_directories),
        threshold=directory_threshold,
        candidates=selected_directories,
    )

    file_candidates = files(root, selected_directories)
    scored_files, current = decider.score_candidates(
        query,
        "file",
        file_candidates,
    )
    merge_usage(usage, current)
    selected_files = [
        item
        for item in scored_files
        if item["score"] >= file_threshold
    ]
    trace.emit(
        "phase1_completed",
        exposed=len(file_candidates),
        selected=len(selected_files),
        threshold=file_threshold,
        files=selected_files,
    )
    return (
        selected_directories,
        selected_files,
        {
            **usage,
            "directories_exposed": len(directory_candidates),
            "directories_selected": len(selected_directories),
            "files_exposed": len(file_candidates),
            "files_selected": len(selected_files),
        },
    )


def run(
    root,
    query,
    decider,
    trace,
    *,
    directory_threshold=DEFAULT_DIRECTORY_THRESHOLD,
    file_threshold=DEFAULT_FILE_THRESHOLD,
    window_lines=DEFAULT_WINDOW_LINES,
    parallel_threshold=DEFAULT_PARALLEL_THRESHOLD,
    max_jumps_per_file=DEFAULT_MAX_JUMPS_PER_FILE,
    max_epochs=DEFAULT_MAX_EPOCHS,
):
    started = time.perf_counter()
    directories_selected, selected_files, phase1_metrics = run_phase1(
        root,
        query,
        decider,
        trace,
        directory_threshold,
        file_threshold,
    )
    usage = {
        key: phase1_metrics.get(key, 0)
        for key in ("model_calls", "input_tokens", "output_tokens")
    }
    state = initial_state(query, selected_files, root)

    trace.emit(
        "range_runtime_started",
        architecture="range_runtime_v0",
        file_count=len(state["files"]),
        files=state["files"],
        window_lines=window_lines,
        parallel_threshold=parallel_threshold,
        max_jumps_per_file=max_jumps_per_file,
    )

    reads_executed = 0
    selector_modes = {}
    unique_files = set()

    for epoch in range(1, max_epochs + 1):
        state["epoch"] = epoch
        actions = generate_action_space(
            state,
            window_lines,
            max_jumps_per_file,
        )
        trace.emit(
            "range_action_space",
            epoch=epoch,
            action_count=len(actions),
            actions=actions,
        )

        scored, current = decider.score_actions(
            query,
            state,
            actions,
        )
        merge_usage(usage, current)
        selected, mode = select_actions(
            scored,
            parallel_threshold,
        )
        selector_modes[mode] = selector_modes.get(mode, 0) + 1

        trace.emit(
            "range_action_scores",
            epoch=epoch,
            threshold=parallel_threshold,
            scores=[
                {
                    "id": item["id"],
                    "kind": item["kind"],
                    "path": item.get("path"),
                    "start_line": item.get("start_line"),
                    "end_line": item.get("end_line"),
                    "navigation": item.get("navigation"),
                    "score": item["score"],
                }
                for item in scored
            ],
            selected_ids=[item["id"] for item in selected],
            selection_mode=mode,
        )

        state["action_history"].append({
            "epoch": epoch,
            "scores": scored,
            "selected_ids": [item["id"] for item in selected],
            "selection_mode": mode,
        })

        if selected[0]["kind"] == "stop_task":
            state["termination"] = mode
            trace.emit(
                "range_runtime_stopped",
                epoch=epoch,
                reason=mode,
                stop_score=selected[0]["score"],
            )
            break

        observations = []
        for action in selected:
            observation = apply_read(
                state,
                root,
                action,
            )
            observations.append(observation)
            reads_executed += 1
            unique_files.add(action["path"])

        trace.emit(
            "range_actions_executed",
            epoch=epoch,
            action_count=len(selected),
            observations=observations,
        )
    else:
        state["termination"] = "budget_exhausted"
        trace.emit(
            "range_runtime_stopped",
            epoch=max_epochs,
            reason="budget_exhausted",
        )

    metrics = {
        **phase1_metrics,
        **usage,
        "epochs": state["epoch"],
        "reads_executed": reads_executed,
        "unique_files_read": len(unique_files),
        "observations": len(state["observations"]),
        "selector_modes": selector_modes,
        "parallel_threshold": parallel_threshold,
        "window_lines": window_lines,
        "max_jumps_per_file": max_jumps_per_file,
        "termination": state["termination"],
        "elapsed_ms": round(
            (time.perf_counter() - started) * 1000,
            3,
        ),
    }
    result = {
        "query": query,
        "root": str(Path(root).resolve()),
        "model": decider.model,
        "architecture": "range_runtime_v0",
        "thresholds": {
            "directory": directory_threshold,
            "file": file_threshold,
            "parallel_action": parallel_threshold,
        },
        "directories": directories_selected,
        "files": selected_files,
        "state": state,
        "metrics": metrics,
    }
    trace.emit("range_runtime_completed", result=result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("query")
    parser.add_argument(
        "--directory-threshold",
        type=float,
        default=DEFAULT_DIRECTORY_THRESHOLD,
    )
    parser.add_argument(
        "--file-threshold",
        type=float,
        default=DEFAULT_FILE_THRESHOLD,
    )
    parser.add_argument(
        "--window-lines",
        type=int,
        default=DEFAULT_WINDOW_LINES,
    )
    parser.add_argument(
        "--parallel-threshold",
        type=float,
        default=DEFAULT_PARALLEL_THRESHOLD,
    )
    parser.add_argument(
        "--max-jumps-per-file",
        type=int,
        default=DEFAULT_MAX_JUMPS_PER_FILE,
    )
    parser.add_argument(
        "--max-epochs",
        type=int,
        default=DEFAULT_MAX_EPOCHS,
    )
    parser.add_argument("--offline-decider", action="store_true")
    parser.add_argument("--trace-file")
    parser.add_argument("--output-json")
    parser.add_argument(
        "--typesafe-endpoint",
        default=os.getenv("TYPESAFE_API_URL", API_URL),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("TYPESAFE_MODEL", MODEL),
    )
    args = parser.parse_args(argv)

    if args.window_lines < 1:
        parser.error("--window-lines must be >= 1")
    if args.max_jumps_per_file < 0:
        parser.error("--max-jumps-per-file must be >= 0")
    if args.max_epochs < 1:
        parser.error("--max-epochs must be >= 1")
    if not 0 <= args.parallel_threshold <= 1:
        parser.error("--parallel-threshold must be in [0,1]")

    trace = Trace(args.trace_file)
    if args.offline_decider:
        decider = OfflineRangeDecider(trace)
    else:
        key = os.getenv("TYPESAFE_API_KEY", "")
        if not key:
            print(
                "TYPESAFE_API_KEY is required unless "
                "--offline-decider is used.",
                file=sys.stderr,
            )
            return 2
        decider = SystemOneRangeDecider(
            key,
            trace,
            args.typesafe_endpoint,
            args.model,
        )

    result = run(
        args.root,
        args.query,
        decider,
        trace,
        directory_threshold=args.directory_threshold,
        file_threshold=args.file_threshold,
        window_lines=args.window_lines,
        parallel_threshold=args.parallel_threshold,
        max_jumps_per_file=args.max_jumps_per_file,
        max_epochs=args.max_epochs,
    )

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output_json:
        Path(args.output_json).write_text(
            payload + "\n",
            encoding="utf-8",
        )
    print(payload if args.output_json is None else json.dumps(
        result["metrics"],
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
