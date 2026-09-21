# Structured Trace Protocol

Formal navigation metrics require structured harness traces. The coding harness should append JSON objects to:

```text
$NARNESS_TRACE_FILE
```

one event per line.

Every event SHOULD include monotonic or relative `ts_ms`.

## Event types

### Search

```json
{"ts_ms": 120, "type": "search", "query": "reconnect session", "results": [{"path": "web/src/..."}]}
```

### Glob

```json
{"ts_ms": 180, "type": "glob", "pattern": "**/*Session*"}
```

### Read

```json
{"ts_ms": 240, "type": "read", "path": "web/src/platform/session-runtime/SessionRuntime.ts"}
```

A read event means content was actually loaded into agent context, not merely returned as a search hit.

### Semantic resolver

```json
{"ts_ms": 90, "type": "resolver", "query": "...", "matches": ["capability://terminal/session/route-recovery"]}
```

### Edit

```json
{"ts_ms": 900, "type": "edit", "paths": ["web/src/..."], "operation": "patch"}
```

### Validation

```json
{"ts_ms": 1200, "type": "validation", "command": "npm test -- ...", "exit_code": 1}
```

### Usage

```json
{
  "ts_ms": 1300,
  "type": "usage",
  "input_tokens": 10000,
  "output_tokens": 1200,
  "reasoning_tokens": 800,
  "cached_tokens": 4000
}
```

Token fields are optional when the model/harness does not expose them.

## Scoring

`scripts/score-ai-native-run.py` combines the trace with hidden machine-readable gold data and calculates:

- search/glob/resolver calls;
- files and unique files read;
- primary/relevant/adjacent/irrelevant reads;
- navigation precision and recall;
- search noise;
- false-positive search-result rate when result paths are available;
- first-hit correctness;
- time to first relevant artifact;
- time to first edit;
- important artifacts missed;
- patch count and out-of-scope edits;
- validation failures and repair loops;
- available model token usage.

A formal run without a sufficiently complete structured trace may still provide correctness data, but it is not admissible for retrieval/context-efficiency metrics.
