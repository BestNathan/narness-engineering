#!/usr/bin/env python3
"""Compare System One code-locator evidence with a Claude Code reference run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def unique(items):
    return list(dict.fromkeys(items))


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def claude_files(reference):
    rows = reference.get("relevant_files", [])
    return {
        item["path"]: item
        for item in rows
        if isinstance(item, dict) and item.get("path")
    }


def system_one_phase1_files(result):
    return {
        item["id"]
        for item in result.get("files", [])
        if isinstance(item, dict) and item.get("id")
    }


def system_one_evidence(result):
    by_path = {}
    for item in result.get("snippets", []):
        path = item.get("path")
        if not path:
            continue
        by_path.setdefault(path, []).append(item)
    return by_path


def ranges_overlap(a_start, a_end, b_start, b_end):
    return max(a_start, b_start) <= min(a_end, b_end)


def reference_ranges(item):
    out = []
    for evidence in item.get("evidence", []) or []:
        try:
            start = int(evidence["start_line"])
            end = int(evidence["end_line"])
        except (KeyError, TypeError, ValueError):
            continue
        if start > 0 and end >= start:
            out.append((start, end))
    return out


def evidence_range_overlap(s1_rows, ref_item):
    refs = reference_ranges(ref_item)
    if not refs:
        return None
    for row in s1_rows:
        try:
            s_start = int(row["start_line"])
            s_end = int(row["end_line"])
        except (KeyError, TypeError, ValueError):
            continue
        if any(ranges_overlap(s_start, s_end, r_start, r_end) for r_start, r_end in refs):
            return True
    return False


def ratio(numerator, denominator):
    return None if denominator == 0 else numerator / denominator


def compare(system_one, claude):
    ref = claude_files(claude)
    phase1 = system_one_phase1_files(system_one)
    evidence = system_one_evidence(system_one)

    ref_all = set(ref)
    ref_primary = {
        path
        for path, item in ref.items()
        if item.get("relevance") == "primary"
    }
    ref_supporting = {
        path
        for path, item in ref.items()
        if item.get("relevance") == "supporting"
    }
    evidence_paths = set(evidence)

    phase1_hit = phase1 & ref_all
    evidence_hit = evidence_paths & ref_all
    primary_phase1_hit = phase1 & ref_primary
    primary_evidence_hit = evidence_paths & ref_primary

    shared_range_status = {}
    for path in sorted(evidence_hit):
        shared_range_status[path] = evidence_range_overlap(
            evidence[path],
            ref[path],
        )

    comparable_ranges = {
        path: status
        for path, status in shared_range_status.items()
        if status is not None
    }
    range_hits = sum(status is True for status in comparable_ranges.values())

    missed = sorted(ref_all - evidence_paths)
    phase1_missed = sorted(ref_all - phase1)
    s1_only = sorted(evidence_paths - ref_all)

    return {
        "reference_kind": "claude-code-system2-reference-not-ground-truth",
        "query": system_one.get("query"),
        "counts": {
            "claude_reference_files": len(ref_all),
            "claude_primary_files": len(ref_primary),
            "claude_supporting_files": len(ref_supporting),
            "system_one_phase1_files": len(phase1),
            "system_one_evidence_files": len(evidence_paths),
            "phase1_reference_hits": len(phase1_hit),
            "evidence_reference_hits": len(evidence_hit),
            "primary_phase1_hits": len(primary_phase1_hit),
            "primary_evidence_hits": len(primary_evidence_hit),
            "comparable_shared_files_with_reference_ranges": len(comparable_ranges),
            "shared_files_with_any_range_overlap": range_hits,
        },
        "metrics": {
            "phase1_reference_recall": ratio(len(phase1_hit), len(ref_all)),
            "evidence_reference_recall": ratio(len(evidence_hit), len(ref_all)),
            "primary_phase1_recall": ratio(len(primary_phase1_hit), len(ref_primary)),
            "primary_evidence_recall": ratio(len(primary_evidence_hit), len(ref_primary)),
            "evidence_reference_precision_proxy": ratio(len(evidence_hit), len(evidence_paths)),
            "shared_file_range_overlap_rate": ratio(range_hits, len(comparable_ranges)),
        },
        "agreement": {
            "phase1_and_claude": sorted(phase1_hit),
            "evidence_and_claude": sorted(evidence_hit),
            "claude_missed_by_phase1": phase1_missed,
            "claude_missed_by_evidence": missed,
            "system_one_evidence_not_in_claude_reference": s1_only,
            "shared_file_range_overlap": shared_range_status,
        },
        "claude_reference": {
            path: {
                "relevance": item.get("relevance"),
                "reason": item.get("reason"),
                "evidence": item.get("evidence", []),
            }
            for path, item in sorted(ref.items())
        },
        "system_one_evidence": {
            path: [
                {
                    "start_line": item.get("start_line"),
                    "end_line": item.get("end_line"),
                    "score": item.get("score"),
                }
                for item in rows
            ]
            for path, rows in sorted(evidence.items())
        },
    }


def markdown(report):
    c = report["counts"]
    m = report["metrics"]
    a = report["agreement"]

    def pct(value):
        return "n/a" if value is None else f"{value * 100:.1f}%"

    lines = [
        "# System One vs Claude Code reference",
        "",
        "> Claude Code is used as a System 2 reference baseline, not as ground truth.",
        "",
        "## Metrics",
        "",
        f"- Claude reference files: {c['claude_reference_files']} "
        f"(primary: {c['claude_primary_files']}, supporting: {c['claude_supporting_files']})",
        f"- System One Phase-1 files: {c['system_one_phase1_files']}",
        f"- System One evidence files: {c['system_one_evidence_files']}",
        f"- Phase-1 reference recall: {pct(m['phase1_reference_recall'])}",
        f"- Final-evidence reference recall: {pct(m['evidence_reference_recall'])}",
        f"- Primary-file Phase-1 recall: {pct(m['primary_phase1_recall'])}",
        f"- Primary-file final-evidence recall: {pct(m['primary_evidence_recall'])}",
        f"- Evidence precision proxy vs reference: {pct(m['evidence_reference_precision_proxy'])}",
        f"- Shared-file range overlap rate: {pct(m['shared_file_range_overlap_rate'])}",
        "",
        "## Claude reference files missed by final System One evidence",
        "",
    ]
    lines += [f"- `{path}`" for path in a["claude_missed_by_evidence"]] or ["- None"]
    lines += [
        "",
        "## System One evidence files absent from Claude reference",
        "",
    ]
    lines += [
        f"- `{path}`"
        for path in a["system_one_evidence_not_in_claude_reference"]
    ] or ["- None"]
    lines += [
        "",
        "## Shared files",
        "",
    ]
    lines += [f"- `{path}`" for path in a["evidence_and_claude"]] or ["- None"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-one", required=True)
    parser.add_argument("--claude", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    args = parser.parse_args(argv)

    report = compare(load(args.system_one), load(args.claude))
    Path(args.output_json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(args.output_markdown).write_text(
        markdown(report),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
