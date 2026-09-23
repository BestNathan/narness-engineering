#!/usr/bin/env python3
"""System One progressive code-localization research demo."""
from __future__ import annotations
import argparse, json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
TRANSIENT_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504, 520, 522, 523, 524, 529}
MAX_REQUEST_ATTEMPTS = 5
IGNORE = {".git", ".idea", ".vscode", ".venv", "node_modules", "target", "dist", "build", "__pycache__"}
SUFFIXES = {".py", ".rs", ".go", ".java", ".ts", ".tsx", ".js", ".jsx", ".vue", ".proto", ".sql", ".sh", ".yaml", ".yml", ".toml", ".md"}

class Trace:
    def __init__(self, path):
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("")
    def emit(self, event, **data):
        if self.path:
            record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **data}
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

def model_projection(stage, payload):
    """Project raw candidates into a transport-safe semantic view for the model.

    Raw candidates remain in the local evidence trace. Source projections
    normalize literal values so repository security tests do not look like live
    attack payloads to an upstream WAF, while identifiers and code structure
    remain visible to System One.
    """
    if stage not in {"line", "region", "symbol"}:
        return payload
    projected = dict(payload)
    patterns = [
        (r'"(?:\\.|[^"\\])*"', '"<string>"'),
        (r"'(?:\\.|[^'\\])*'", "'<string>'"),
        (r'`(?:\\.|[^`\\])*`', '`<string>`'),
    ]
    for key in ("text", "nearby_lines"):
        value = projected.get(key)
        if not isinstance(value, str):
            continue
        for pattern, replacement in patterns:
            value = re.sub(pattern, replacement, value)
        projected[key] = value
    declarations = projected.get("declarations")
    if isinstance(declarations, list):
        normalized = []
        for value in declarations:
            if not isinstance(value, str):
                continue
            for pattern, replacement in patterns:
                value = re.sub(pattern, replacement, value)
            normalized.append(value)
        projected["declarations"] = normalized
    signature = projected.get("signature")
    if isinstance(signature, str):
        for pattern, replacement in patterns:
            signature = re.sub(pattern, replacement, signature)
        projected["signature"] = signature
    return projected

class SystemOneScorer:
    def __init__(self, key, trace, endpoint=API_URL, model=MODEL, batch_size=None):
        self.key, self.trace, self.endpoint, self.model = key, trace, endpoint, model
        # batch_size is accepted for backward compatibility only. System One
        # evaluates all independent questions for a stage in one request.
        self.deprecated_batch_size = batch_size

    def _request(self, payload):
        body = json.dumps(payload).encode()
        for attempt in range(MAX_REQUEST_ATTEMPTS):
            req = urllib.request.Request(self.endpoint, data=body, method="POST", headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")
                retryable = exc.code in TRANSIENT_HTTP_STATUS
                if not retryable or attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise RuntimeError(f"TypeSafe HTTP {exc.code}: {detail[:2000]}") from exc
                delay = 2 ** attempt
                self.trace.emit("system_one_retry", status=exc.code, attempt=attempt + 1, delay_seconds=delay)
                time.sleep(delay)
            except urllib.error.URLError as exc:
                if attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise RuntimeError(f"TypeSafe transport error: {exc}") from exc
                delay = 2 ** attempt
                self.trace.emit("system_one_retry", status="transport", attempt=attempt + 1, delay_seconds=delay)
                time.sleep(delay)

    def score(self, query, stage, candidates):
        usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0}
        if not candidates:
            return [], usage

        state_candidates = [
            model_projection(stage, candidate["payload"])
            for candidate in candidates
        ]
        questions = {
            f"candidate_{i}": {
                "type": "noul",
                "instructions": (
                    f"Should `candidates[{i}]` be retained for `goal` "
                    "under `policy`?"
                ),
            }
            for i in range(len(candidates))
        }

        payload = {
            "state": {
                "goal": query,
                "stage": stage,
                "policy": {
                    "retain": (
                        "Plausibly relevant to locating or understanding "
                        "the requested implementation, including indirect "
                        "supporting code."
                    ),
                    "reject": (
                        "Unlikely to help locate or understand the requested "
                        "implementation."
                    ),
                },
                "candidates": state_candidates,
            },
            "model": self.model,
            "questions": questions,
        }
        request_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.trace.emit(
            "system_one_request",
            stage=stage,
            request_index=0,
            candidate_count=len(candidates),
            candidate_ids=[x["id"] for x in candidates],
            request_bytes=request_bytes,
            request=payload,
        )
        started = time.perf_counter()
        response = self._request(payload)
        latency = round((time.perf_counter() - started) * 1000, 3)

        u = response.get("usage", {})
        usage["model_calls"] = 1
        usage["input_tokens"] = int(u.get("input_tokens", 0) or 0)
        usage["output_tokens"] = int(u.get("output_tokens", 0) or 0)

        out, scores = [], []
        answers = response.get("answers", {})
        for i, candidate in enumerate(candidates):
            answer = answers.get(f"candidate_{i}", {})
            if answer.get("type") != "noul":
                raise RuntimeError(f"unexpected answer for candidate_{i}: {answer!r}")
            item = {**candidate, "score": float(answer["noul"])}
            out.append(item)
            scores.append({"id": item["id"], "score": item["score"]})

        self.trace.emit(
            "system_one_response",
            stage=stage,
            request_index=0,
            candidate_count=len(candidates),
            latency_ms=latency,
            model=response.get("model"),
            usage=u,
            scores=scores,
        )
        return sorted(out, key=lambda x: (-x["score"], x["id"])), usage

class OfflineScorer:
    model = "offline-lexical-fixture"
    def __init__(self, trace): self.trace = trace
    def score(self, query, stage, candidates):
        tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", query.lower()))
        if "websocket" in tokens: tokens |= {"ws", "socket", "connect", "connection", "reconnect"}
        out = []
        for c in candidates:
            text = json.dumps(c["payload"]).lower(); hits = sum(t in text for t in tokens if len(t) >= 2)
            score = 0.05 if hits == 0 else 0.62 if hits == 1 else 0.84 if hits == 2 else 0.96
            out.append({**c, "score": score})
        out.sort(key=lambda x: (-x["score"], x["id"])); self.trace.emit("offline_scores", stage=stage, scores=[{"id":x["id"],"score":x["score"]} for x in out])
        return out, {"model_calls":0,"input_tokens":0,"output_tokens":0}

def directories(root):
    root = Path(root).resolve(); out = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE and not d.startswith("."))
        p = Path(current)
        if p == root: continue
        rel = p.relative_to(root).as_posix()
        out.append({"id": rel, "payload": {"path": rel, "name": p.name, "child_directories": dirs[:24], "direct_files": sorted(f for f in files if not f.startswith("."))[:40]}})
    return out

def files(root, selected_dirs):
    """Expose only direct source files from directories retained by stage one.

    The directory stage already enumerates the full repository tree. Walking a
    retained directory recursively here would re-introduce files that live
    under child directories rejected by the directory stage and would make the
    second frontier much larger than the semantic selection implies.
    """
    root = Path(root).resolve()
    found = {}
    for d in selected_dirs:
        base = root / d["payload"]["path"]
        try:
            entries = sorted(base.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for p in entries:
            if not p.is_file():
                continue
            name = p.name
            if name.startswith(".") or p.suffix.lower() not in SUFFIXES:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            rel = p.relative_to(root).as_posix()
            found[rel] = {
                "id": rel,
                "payload": {
                    "path": rel,
                    "directory": d["payload"]["path"],
                    "filename": name,
                    "extension": p.suffix.lower(),
                    "size_bytes": size,
                },
            }
    return [found[k] for k in sorted(found)]

CONTROL_NAMES = {
    "if", "for", "while", "switch", "catch", "match", "loop", "return",
}

def _detect_symbol(line, suffix):
    stripped = line.strip()
    if not stripped:
        return None

    patterns = []
    if suffix == ".py":
        patterns = [
            ("class", r"^(?:@[^ ]+\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("function", r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        ]
    elif suffix == ".rs":
        patterns = [
            ("function", r"^(?:(?:pub(?:\([^)]*\))?|unsafe|async|const|extern(?:\s+\"[^\"]+\")?)\s+)*fn\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("struct", r"^(?:(?:pub(?:\([^)]*\))?)\s+)?struct\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("enum", r"^(?:(?:pub(?:\([^)]*\))?)\s+)?enum\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("trait", r"^(?:(?:pub(?:\([^)]*\))?)\s+)?trait\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("impl", r"^impl(?:<[^>]+>)?\s+(.+?)(?:\s+where\b|\s*\{)"),
        ]
    elif suffix == ".go":
        patterns = [
            ("function", r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\("),
            ("type", r"^type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b"),
        ]
    elif suffix in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
        patterns = [
            ("class", r"^(?:(?:export|default|declare|abstract)\s+)*class\s+([A-Za-z_$][A-Za-z0-9_$]*)"),
            ("interface", r"^(?:(?:export|default|declare)\s+)*interface\s+([A-Za-z_$][A-Za-z0-9_$]*)"),
            ("type", r"^(?:(?:export|declare)\s+)*type\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"),
            ("function", r"^(?:(?:export|default)\s+)*(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("),
            ("function", r"^(?:(?:export|declare)\s+)*(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=.*=>"),
            ("method", r"^(?:(?:public|private|protected|static|async|readonly|override|abstract|get|set)\s+)*([A-Za-z_$][A-Za-z0-9_$]*)\s*(?:<[^>{}]+>)?\s*\([^;{}]*\)"),
        ]
    elif suffix == ".java":
        patterns = [
            ("class", r"^(?:(?:public|private|protected|abstract|final|static)\s+)*(?:class|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("method", r"^(?:(?:public|private|protected|static|final|abstract|synchronized|native|default)\s+)*(?:<[^>]+>\s*)?(?:[A-Za-z_$][A-Za-z0-9_$.<>?, \[\]]+\s+)?([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^;{}]*\)"),
        ]
    elif suffix == ".proto":
        patterns = [
            ("service", r"^service\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("message", r"^message\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("enum", r"^enum\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("rpc", r"^rpc\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        ]
    elif suffix == ".sh":
        patterns = [
            ("function", r"^(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{?"),
        ]
    elif suffix == ".md":
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", stripped)
        if match:
            return {
                "kind": "section",
                "name": match.group(2)[:120],
                "heading_level": len(match.group(1)),
            }
        return None

    for kind, pattern in patterns:
        match = re.match(pattern, stripped)
        if not match:
            continue
        name = match.group(1).strip()
        if name.lower() in CONTROL_NAMES:
            continue
        return {"kind": kind, "name": name[:120]}
    return None

def _normalized_code(line):
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    line = re.sub(r"'(?:\\.|[^'\\])*'", "''", line)
    line = re.sub(r"`(?:\\.|[^`\\])*`", "``", line)
    line = line.split("//", 1)[0]
    return line

def _brace_symbol_end(source, start0):
    depth = 0
    opened = False
    scan_end = min(len(source), start0 + 800)
    for index in range(start0, scan_end):
        code = _normalized_code(source[index])
        for ch in code:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}" and opened:
                depth -= 1
                if depth <= 0:
                    return index + 1
        if not opened and index > start0 + 12:
            break
    return start0 + 1

def _python_symbol_end(source, start0):
    line = source[start0]
    indent = len(line) - len(line.lstrip())
    end = start0 + 1
    for index in range(start0 + 1, len(source)):
        stripped = source[index].strip()
        if not stripped or stripped.startswith("#"):
            end = index + 1
            continue
        current_indent = len(source[index]) - len(source[index].lstrip())
        if current_indent <= indent:
            break
        end = index + 1
    return end

def _markdown_symbol_end(source, start0, level):
    end = len(source)
    for index in range(start0 + 1, len(source)):
        match = re.match(r"^\\s*(#{1,6})\\s+", source[index])
        if match and len(match.group(1)) <= level:
            return index
    return end

def _symbol_signature(source, start0, max_lines=6):
    parts = []
    for index in range(start0, min(len(source), start0 + max_lines)):
        stripped = source[index].strip()
        if stripped:
            parts.append(stripped)
        joined = " ".join(parts)
        if (
            "{" in stripped
            or stripped.endswith(":")
            or stripped.endswith(";")
            or "=>" in stripped
        ):
            break
    return " ".join(parts)[:420]

def symbols(root, file):
    """Expose semantic source structure without disclosing function bodies.

    Selected files are scanned locally to build an outline. System One sees
    only symbol kind/name/signature and source ranges; full source is read into
    the final result only for symbols retained by the third-stage decision.
    """
    path = Path(root).resolve() / file["payload"]["path"]
    source = path.read_text(encoding="utf-8", errors="replace").splitlines()
    suffix = path.suffix.lower()
    out = []

    for start0, line in enumerate(source):
        detected = _detect_symbol(line, suffix)
        if detected is None:
            continue

        if suffix == ".py":
            end_line = _python_symbol_end(source, start0)
        elif suffix == ".md":
            end_line = _markdown_symbol_end(
                source,
                start0,
                detected.get("heading_level", 6),
            )
        else:
            end_line = _brace_symbol_end(source, start0)

        start_line = start0 + 1
        if end_line < start_line:
            end_line = start_line

        payload = {
            "path": file["payload"]["path"],
            "kind": detected["kind"],
            "name": detected["name"],
            "start_line": start_line,
            "end_line": end_line,
            "signature": _symbol_signature(source, start0),
        }
        out.append({
            "id": (
                f"{file['id']}::{payload['kind']}::{payload['name']}"
                f"@{start_line}"
            ),
            "payload": payload,
        })

    if out:
        return out

    # Unsupported or declaration-free files still get a structural fallback.
    # The model sees metadata only, not the body.
    return [{
        "id": f"{file['id']}::file",
        "payload": {
            "path": file["payload"]["path"],
            "kind": "file",
            "name": file["payload"]["filename"],
            "start_line": 1,
            "end_line": max(1, len(source)),
            "signature": (
                f"{file['payload']['filename']} "
                f"({len(source)} lines, {file['payload']['extension']})"
            ),
        },
    }]

OUTLINE_SYMBOL_LIMIT = 30
SCOPE_KINDS = {"class", "impl", "trait", "interface", "service"}

def _contains_symbol(container, item):
    c = container["payload"]
    s = item["payload"]
    return (
        c["path"] == s["path"]
        and c["start_line"] <= s["start_line"]
        and s["end_line"] <= c["end_line"]
        and container["id"] != item["id"]
    )

def outlines(root, selected_files):
    """Build semantic scope outlines from retained files.

    A scope outline is a class/impl/trait/interface/service with its direct
    members. Remaining file-level symbols are grouped into one module scope.
    System One judges these scopes before individual symbols are disclosed.
    """
    candidates = []
    symbols_by_outline = {}

    for file in selected_files:
        path = file["payload"]["path"]
        file_symbols = symbols(root, file)
        containers = [
            item for item in file_symbols
            if item["payload"]["kind"] in SCOPE_KINDS
            and item["payload"]["end_line"] > item["payload"]["start_line"]
        ]
        assigned = set()

        for container in containers:
            nested_containers = [
                other for other in containers
                if other["id"] != container["id"]
                and _contains_symbol(container, other)
            ]
            direct_members = []
            for item in file_symbols:
                if not _contains_symbol(container, item):
                    continue
                if any(_contains_symbol(nested, item) for nested in nested_containers):
                    continue
                direct_members.append(item)

            members = [container, *direct_members]
            outline_id = f"{container['id']}::outline"
            preview = [
                {
                    "kind": item["payload"]["kind"],
                    "name": item["payload"]["name"],
                }
                for item in members[:OUTLINE_SYMBOL_LIMIT]
            ]
            candidates.append({
                "id": outline_id,
                "payload": {
                    "path": path,
                    "filename": file["payload"]["filename"],
                    "extension": file["payload"]["extension"],
                    "scope_kind": container["payload"]["kind"],
                    "scope_name": container["payload"]["name"],
                    "start_line": container["payload"]["start_line"],
                    "end_line": container["payload"]["end_line"],
                    "member_count": len(members),
                    "members": preview,
                    "truncated": len(members) > OUTLINE_SYMBOL_LIMIT,
                },
            })
            symbols_by_outline[outline_id] = members
            assigned.update(item["id"] for item in members)

        module_members = [
            item for item in file_symbols
            if item["id"] not in assigned
        ]
        if module_members:
            outline_id = f"{file['id']}::module::outline"
            preview = [
                {
                    "kind": item["payload"]["kind"],
                    "name": item["payload"]["name"],
                }
                for item in module_members[:OUTLINE_SYMBOL_LIMIT]
            ]
            candidates.append({
                "id": outline_id,
                "payload": {
                    "path": path,
                    "filename": file["payload"]["filename"],
                    "extension": file["payload"]["extension"],
                    "scope_kind": "module",
                    "scope_name": file["payload"]["filename"],
                    "start_line": min(
                        item["payload"]["start_line"]
                        for item in module_members
                    ),
                    "end_line": max(
                        item["payload"]["end_line"]
                        for item in module_members
                    ),
                    "member_count": len(module_members),
                    "members": preview,
                    "truncated": len(module_members) > OUTLINE_SYMBOL_LIMIT,
                },
            })
            symbols_by_outline[outline_id] = module_members

    return candidates, symbols_by_outline


def symbol_snippets(root, path, scored, threshold):
    relevant = sorted(
        (x for x in scored if x["score"] >= threshold),
        key=lambda x: x["payload"]["start_line"],
    )
    if not relevant:
        return []

    source = (Path(root).resolve() / path).read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    ranges = []

    for item in relevant:
        start = item["payload"]["start_line"]
        end = min(item["payload"]["end_line"], len(source))
        score = item["score"]
        names = [item["payload"]["name"]]
        if ranges and start <= ranges[-1]["end_line"] + 1:
            ranges[-1]["end_line"] = max(ranges[-1]["end_line"], end)
            ranges[-1]["score"] = max(ranges[-1]["score"], score)
            ranges[-1]["symbols"].extend(names)
        else:
            ranges.append({
                "start_line": start,
                "end_line": end,
                "score": score,
                "symbols": names,
            })

    return [
        {
            "path": path,
            "start_line": item["start_line"],
            "end_line": item["end_line"],
            "score": item["score"],
            "symbols": item["symbols"],
            "content": "\\n".join(
                f"{line_number}: {source[line_number - 1]}"
                for line_number in range(
                    item["start_line"],
                    item["end_line"] + 1,
                )
            ),
        }
        for item in ranges
    ]

def run(root, query, scorer, trace, dt, ft, ot, st):
    started = time.perf_counter()
    usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0}

    def stage(name, candidates, threshold):
        trace.emit("candidates_exposed", stage=name, count=len(candidates), candidates=candidates)
        scored, u = scorer.score(query, name, candidates)
        for k in usage:
            usage[k] += u[k]
        selected = [x for x in scored if x["score"] >= threshold]
        trace.emit(
            "threshold_applied",
            stage=name,
            threshold=threshold,
            input_count=len(scored),
            selected_count=len(selected),
            selected=selected,
        )
        return selected, scored

    trace.emit(
        "search_started",
        root=str(Path(root).resolve()),
        query=query,
        model=scorer.model,
        thresholds={"directory": dt, "file": ft, "outline": ot, "symbol": st},
        request_strategy="one_request_per_stage",
    )

    directory_candidates = directories(root)
    ds, _ = stage("directory", directory_candidates, dt)

    file_candidates = files(root, ds)
    fs, _ = stage("file", file_candidates, ft)

    outline_candidates, symbols_by_outline = outlines(root, fs)
    os_, _ = stage("outline", outline_candidates, ot)

    symbol_candidates = []
    symbol_counts_by_outline = {}
    seen_symbol_ids = set()
    for outline in os_:
        current = symbols_by_outline.get(outline["id"], [])
        symbol_counts_by_outline[outline["id"]] = len(current)
        for item in current:
            if item["id"] in seen_symbol_ids:
                continue
            seen_symbol_ids.add(item["id"])
            symbol_candidates.append(item)

    trace.emit(
        "symbol_frontier_built",
        outline_count=len(os_),
        symbol_count=len(symbol_candidates),
        symbols_by_outline=symbol_counts_by_outline,
    )

    kept_symbols, scored_symbols = stage("symbol", symbol_candidates, st)

    scored_by_path = {}
    for item in scored_symbols:
        scored_by_path.setdefault(item["payload"]["path"], []).append(item)

    ss = []
    for f in fs:
        path = f["payload"]["path"]
        ss += symbol_snippets(root, path, scored_by_path.get(path, []), st)

    ss.sort(key=lambda x: (-x["score"], x["path"], x["start_line"]))
    result = {
        "query": query,
        "root": str(Path(root).resolve()),
        "model": scorer.model,
        "thresholds": {"directory": dt, "file": ft, "outline": ot, "symbol": st},
        "directories": ds,
        "files": fs,
        "snippets": ss,
        "metrics": {
            **usage,
            "request_strategy": "one_request_per_stage",
            "directories_exposed": len(directory_candidates),
            "directories_selected": len(ds),
            "files_exposed": len(file_candidates),
            "files_selected": len(fs),
            "outlines_exposed": len(outline_candidates),
            "outlines_selected": len(os_),
            "symbols_exposed": len(symbol_candidates),
            "symbols_selected": len(kept_symbols),
            "files_scanned_for_outline": len(fs),
            "outline_symbol_limit": OUTLINE_SYMBOL_LIMIT,
            "snippets": len(ss),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        },
    }
    trace.emit("search_completed", result=result)
    return result

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("query")
    p.add_argument("--directory-threshold",type=float,default=.35)
    p.add_argument("--file-threshold",type=float,default=.50)
    p.add_argument("--outline-threshold",type=float,default=.50)
    p.add_argument("--symbol-threshold",type=float,default=.70)
    p.add_argument("--line-threshold",dest="symbol_threshold",type=float,help=argparse.SUPPRESS)
    p.add_argument("--batch-size",type=int,default=None,help=argparse.SUPPRESS)
    p.add_argument("--offline-decider",action="store_true")
    p.add_argument("--trace-file")
    p.add_argument("--output-json")
    p.add_argument("--json",action="store_true")
    p.add_argument("--typesafe-endpoint",default=os.getenv("TYPESAFE_API_URL",API_URL))
    p.add_argument("--model",default=os.getenv("TYPESAFE_MODEL",MODEL))
    a=p.parse_args(argv)

    trace=Trace(a.trace_file)
    if a.offline_decider:
        scorer=OfflineScorer(trace)
    else:
        key=os.getenv("TYPESAFE_API_KEY","")
        if not key:
            print("TYPESAFE_API_KEY is required unless --offline-decider is used.",file=sys.stderr)
            return 2
        scorer=SystemOneScorer(key,trace,a.typesafe_endpoint,a.model,a.batch_size)

    result=run(
        a.root,
        a.query,
        scorer,
        trace,
        a.directory_threshold,
        a.file_threshold,
        a.outline_threshold,
        a.symbol_threshold,
    )
    payload=json.dumps(result,indent=2,ensure_ascii=False)
    if a.output_json:
        Path(a.output_json).write_text(payload+"\n",encoding="utf-8")
    if a.json:
        print(payload)
    else:
        print("relevant directories:")
        [print(f"  {x['score']:.3f} {x['id']}") for x in result["directories"]]
        print("relevant files:")
        [print(f"  {x['score']:.3f} {x['id']}") for x in result["files"]]
        print("relevant snippets:")
        [print(f"  {x['score']:.3f} {x['path']}:{x['start_line']}-{x['end_line']}\n{x['content']}") for x in result["snippets"]]
        print("metrics:",json.dumps(result["metrics"],ensure_ascii=False))
    return 0 if result["files"] and result["snippets"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
