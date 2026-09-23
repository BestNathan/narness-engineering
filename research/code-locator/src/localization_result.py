#!/usr/bin/env python3
"""Canonical structured output for code-localization experiments."""
from __future__ import annotations

from pathlib import Path


SCHEMA_VERSION = 1
KIND = "code-localization-result"
ROLES = {"relevant", "primary", "supporting", "context", "unknown"}


def confidence_label(score):
    if score is None:
        return "unknown"
    score = float(score)
    if score >= 0.80:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


def confidence(score, kind, basis=None):
    if score is None:
        return None
    value = max(0.0, min(1.0, float(score)))
    out = {
        "score": round(value, 6),
        "label": confidence_label(value),
        "type": kind,
    }
    if basis:
        out["basis"] = basis
    return out


def materialize_range(root, path, start_line, end_line):
    source = (Path(root) / path).read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    start = max(1, int(start_line))
    end = min(len(source), int(end_line))
    if start > end:
        return ""
    return "\n".join(
        f"{line_number}: {source[line_number - 1]}"
        for line_number in range(start, end + 1)
    )


def validate(result):
    if result.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported localization result schema_version")
    if result.get("kind") != KIND:
        raise ValueError("invalid localization result kind")
    if not isinstance(result.get("task"), str) or not result["task"]:
        raise ValueError("localization result requires task")
    producer = result.get("producer")
    if not isinstance(producer, dict) or not producer.get("system"):
        raise ValueError("localization result requires producer.system")
    files = result.get("files")
    if not isinstance(files, list):
        raise ValueError("localization result requires files[]")

    seen = set()
    for item in files:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("localization file requires path")
        if path in seen:
            raise ValueError(f"duplicate localization file: {path}")
        seen.add(path)
        if item.get("role", "unknown") not in ROLES:
            raise ValueError(f"invalid role for {path}: {item.get('role')}")
        if not isinstance(item.get("evidence"), list):
            raise ValueError(f"localization file requires evidence[]: {path}")
        for evidence in item["evidence"]:
            start = evidence.get("start_line")
            end = evidence.get("end_line")
            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError(f"evidence requires integer line range: {path}")
            if start < 1 or end < start:
                raise ValueError(f"invalid evidence range: {path}:{start}-{end}")
    return result


def build_system_one_result(engine_result, model=None):
    state_files = {}
    for state in engine_result.get("reader_states", []):
        for item in state.get("files", []):
            state_files[item["path"]] = item

    by_path = {}
    for snippet in engine_result.get("snippets", []):
        by_path.setdefault(snippet["path"], []).append(snippet)

    files = []
    for path, snippets in by_path.items():
        snippets = sorted(
            snippets,
            key=lambda item: (-float(item["score"]), item["start_line"]),
        )
        file_state = state_files.get(path, {})
        max_score = max(float(item["score"]) for item in snippets)
        evidence = []
        for index, item in enumerate(
            sorted(snippets, key=lambda row: row["start_line"]),
            1,
        ):
            evidence.append({
                "id": f"{path}#evidence-{index}",
                "start_line": int(item["start_line"]),
                "end_line": int(item["end_line"]),
                "confidence": confidence(
                    item["score"],
                    "noul_relevance",
                    "System One observation relevance score",
                ),
                "reason": (
                    "Observed source range retained because its relevance "
                    "score met the evidence threshold."
                ),
                "content": item.get("content", ""),
                "provenance": {
                    "action_probability": item.get("action_probability"),
                },
            })

        files.append({
            "path": path,
            "role": "relevant",
            "confidence": confidence(
                max_score,
                "derived_max_evidence_relevance",
                "maximum retained observation relevance for this file",
            ),
            "reason": (
                "System One retained at least one observed source range "
                "from this file as relevant evidence."
            ),
            "evidence": evidence,
            "provenance": {
                "phase1_score": file_state.get("phase1_score"),
                "last_activation_score": file_state.get(
                    "last_activation_score"
                ),
                "activation_count": file_state.get("activation_count", 0),
                "read_count": file_state.get("read_count", 0),
                "stop_reason": file_state.get("stop_reason"),
            },
        })

    files.sort(
        key=lambda item: (
            -item["confidence"]["score"],
            item["path"],
        )
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "task": engine_result.get("query", ""),
        "producer": {
            "system": "system_one",
            "model": model or engine_result.get("model"),
            "confidence_semantics": (
                "Evidence confidence is System One Noul relevance. "
                "File confidence is the maximum retained evidence relevance."
            ),
        },
        "summary": {
            "valuable_files": len(files),
            "evidence_regions": sum(
                len(item["evidence"]) for item in files
            ),
            "note": (
                "Only retained evidence is listed. Phase-1 candidates and "
                "deferred/stopped files remain available in the execution result."
            ),
        },
        "confidence": None,
        "files": files,
    }
    return validate(result)


def normalize_claude_result(raw, subject_root, model=None):
    """Normalize Claude's canonical-or-legacy JSON into the shared schema."""
    if raw.get("kind") == KIND and raw.get("schema_version") == SCHEMA_VERSION:
        result = raw
    else:
        # Legacy Claude reference format.
        overall = raw.get("confidence")
        overall_score = (
            {"high": 0.90, "medium": 0.70, "low": 0.40}.get(overall)
            if isinstance(overall, str)
            else overall
        )
        files = []
        for item in raw.get("relevant_files", []):
            evidence = []
            for index, region in enumerate(item.get("evidence", []) or [], 1):
                evidence.append({
                    "id": f"{item['path']}#evidence-{index}",
                    "start_line": int(region["start_line"]),
                    "end_line": int(region["end_line"]),
                    "confidence": None,
                    "reason": region.get("description", ""),
                })
            files.append({
                "path": item["path"],
                "role": item.get("relevance", "unknown"),
                "confidence": None,
                "reason": item.get("reason", ""),
                "evidence": evidence,
            })
        result = {
            "schema_version": SCHEMA_VERSION,
            "kind": KIND,
            "task": raw.get("task", ""),
            "producer": {
                "system": "claude_code",
                "model": model,
                "confidence_semantics": "Claude model self-assessment",
            },
            "summary": raw.get("summary", ""),
            "confidence": confidence(
                overall_score,
                "model_self_assessment",
                "Claude overall localization confidence",
            ),
            "files": files,
        }

    producer = result.setdefault("producer", {})
    producer["system"] = "claude_code"
    if model:
        producer["model"] = model
    producer.setdefault(
        "confidence_semantics",
        "Claude model self-assessment; not calibrated against System One Noul scores.",
    )

    for file_item in result.get("files", []):
        file_item.setdefault("role", "unknown")
        file_conf = file_item.get("confidence")
        if isinstance(file_conf, (int, float)):
            file_item["confidence"] = confidence(
                file_conf,
                "model_self_assessment",
                "Claude file-value self-assessment",
            )
        for index, evidence in enumerate(file_item.get("evidence", []), 1):
            evidence.setdefault(
                "id",
                f"{file_item['path']}#evidence-{index}",
            )
            ev_conf = evidence.get("confidence")
            if isinstance(ev_conf, (int, float)):
                evidence["confidence"] = confidence(
                    ev_conf,
                    "model_self_assessment",
                    "Claude evidence-value self-assessment",
                )
            evidence["content"] = materialize_range(
                subject_root,
                file_item["path"],
                evidence["start_line"],
                evidence["end_line"],
            )

    return validate(result)
