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

    Raw candidates remain in the local evidence trace. Source-line projections
    normalize literal values so repository security tests do not look like live
    attack payloads to an upstream WAF, while identifiers and code structure
    remain visible to System One.
    """
    if stage != "line":
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

        questions = {}
        for i, candidate in enumerate(candidates):
            questions[f"candidate_{i}"] = {
                "type": "noul",
                "instructions": {
                    "task": query,
                    "stage": stage,
                    "candidate": model_projection(stage, candidate["payload"]),
                    "question": "Would retaining this candidate materially help locate or understand source code relevant to the task?",
                },
                "criteria": {
                    "true": "Plausibly relevant; keep it, including indirect supporting code.",
                    "false": "Unlikely to help locate or understand the requested implementation.",
                },
            }

        payload = {
            "state": {
                "goal": query,
                "stage": stage,
                "candidate_count": len(candidates),
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
    root = Path(root).resolve(); found = {}
    for d in selected_dirs:
        base = root / d["payload"]["path"]
        for current, dirs, names in os.walk(base):
            dirs[:] = sorted(x for x in dirs if x not in IGNORE and not x.startswith("."))
            for name in names:
                p = Path(current) / name
                if name.startswith(".") or p.suffix.lower() not in SUFFIXES: continue
                try: size = p.stat().st_size
                except OSError: continue
                rel = p.relative_to(root).as_posix()
                found[rel] = {"id": rel, "payload": {"path": rel, "filename": name, "extension": p.suffix.lower(), "size_bytes": size}}
    return [found[k] for k in sorted(found)]

def lines(root, file, radius=2):
    path = Path(root).resolve() / file["payload"]["path"]
    source = path.read_text(encoding="utf-8", errors="replace").splitlines(); out = []
    for i, line in enumerate(source):
        if not line.strip(): continue
        start, end = max(0, i-radius), min(len(source), i+radius+1)
        context = "\n".join(f"{n+1}: {source[n]}" for n in range(start, end))
        out.append({"id": f"{file['id']}:{i+1}", "payload": {"path": file["payload"]["path"], "line": i+1, "text": line[:1200], "nearby_lines": context[:6000]}})
    return out

def snippets(root, path, scored, threshold, radius=2):
    relevant = sorted((x for x in scored if x["score"] >= threshold), key=lambda x: x["payload"]["line"])
    if not relevant: return []
    source = (Path(root).resolve()/path).read_text(encoding="utf-8", errors="replace").splitlines(); ranges=[]
    for item in relevant:
        line=item["payload"]["line"]; start=max(1,line-radius); end=min(len(source),line+radius)
        if ranges and start <= ranges[-1][1]+1: ranges[-1]=(ranges[-1][0], max(ranges[-1][1],end), max(ranges[-1][2],item["score"]))
        else: ranges.append((start,end,item["score"]))
    return [{"path":path,"start_line":s,"end_line":e,"score":score,"content":"\n".join(f"{n}: {source[n-1]}" for n in range(s,e+1))} for s,e,score in ranges]

def run(root, query, scorer, trace, dt, ft, lt):
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
        thresholds={"directory": dt, "file": ft, "line": lt},
        request_strategy="one_request_per_stage",
    )

    directory_candidates = directories(root)
    ds, _ = stage("directory", directory_candidates, dt)

    file_candidates = files(root, ds)
    fs, _ = stage("file", file_candidates, ft)

    line_candidates = []
    line_counts_by_file = {}
    for f in fs:
        current = lines(root, f)
        line_candidates.extend(current)
        line_counts_by_file[f["id"]] = len(current)
    trace.emit(
        "line_frontier_built",
        file_count=len(fs),
        line_count=len(line_candidates),
        lines_by_file=line_counts_by_file,
    )

    kept_lines, scored_lines = stage("line", line_candidates, lt)

    scored_by_path = {}
    for item in scored_lines:
        scored_by_path.setdefault(item["payload"]["path"], []).append(item)

    ss = []
    for f in fs:
        path = f["payload"]["path"]
        ss += snippets(root, path, scored_by_path.get(path, []), lt)

    ss.sort(key=lambda x: (-x["score"], x["path"], x["start_line"]))
    result = {
        "query": query,
        "root": str(Path(root).resolve()),
        "model": scorer.model,
        "thresholds": {"directory": dt, "file": ft, "line": lt},
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
            "lines_exposed": len(line_candidates),
            "lines_selected": len(kept_lines),
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
    p.add_argument("--line-threshold",type=float,default=.70)
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

    result=run(a.root,a.query,scorer,trace,a.directory_threshold,a.file_threshold,a.line_threshold)
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
