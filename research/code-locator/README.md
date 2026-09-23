# System One Code Locator

> Experimental research project. This is a localization harness, not a code-changing agent and not part of the canonical Narness runtime.

This directory is the complete Code Locator research unit: implementation, fixtures, tests, design notes, pilot analyses, and immutable run records live together here.

## Project layout

```text
research/code-locator/
├── README.md
├── src/
│   └── system_one_code_locator.py
├── tests/
│   └── test_system_one_code_locator.py
├── fixtures/
│   └── repository/
├── docs/
│   ├── design.md
│   └── pilots/
│       └── nession-websocket-2026-09-23.md
└── runs/
    └── <time>-run-<run_id>-attempt-<n>/
```

The `src/`, `tests/`, and `fixtures/` directories define the experiment. `docs/` contains evolving research reasoning. `runs/` is append-only evidence produced by GitHub Actions.

See [design.md](docs/design.md) for the hypotheses and experiment design, and [the first Nession pilot](docs/pilots/nession-websocket-2026-09-23.md) for the first real TypeSafe baseline.

This project explores whether a fast System One model can localize code by repeatedly judging a progressively disclosed search space rather than driving repository browsing through a ReAct loop.

Given a request such as:

> Help me optimize the websocket connection implementation.

and a repository root, the harness performs:

```text
repository
  -> enumerate directory candidates
  -> System One relevance scores
  -> keep directories above threshold
  -> enumerate files under retained directories
  -> System One relevance scores
  -> keep files above threshold
  -> split retained files into source lines with small local context
  -> System One relevance scores
  -> merge adjacent relevant lines into snippets
```

The model never chooses filesystem tools, constructs paths, or controls traversal. The harness owns state expansion, thresholds, IO, provenance, batching, and result assembly.

## Why Noul instead of Choice

Directory, file, and line relevance are independent judgments: several candidates may all be relevant. The TypeSafe System One API's `noul` primitive returns a yes-probability for each question, so the runtime can retain every candidate whose score crosses the stage threshold.

`choice` would instead normalize probability across candidates and force one winner, which is appropriate for the Kubernetes action-frontier demo but not for multi-hit code localization.

## State progression

```text
RepositoryState
  |
  | deterministic enumeration
  v
DirectoryCandidate[]
  |
  | Noul relevance + low threshold
  v
RelevantDirectory[]
  |
  | deterministic enumeration
  v
FileCandidate[]
  |
  | Noul relevance + medium threshold
  v
RelevantFile[]
  |
  | read source + split on newlines
  v
LineCandidate[]
  |
  | Noul relevance + higher threshold
  v
RelevantLine[]
  |
  | deterministic range merge
  v
CodeSnippet[]
```

The defaults intentionally become stricter as the search gets deeper:

```text
directory >= 0.35
file      >= 0.50
line      >= 0.70
```

These are experiment parameters, not claimed optimal values. Early false negatives are especially expensive because pruning a directory removes its entire subtree. A future experiment should compare simple thresholds against threshold-plus-beam retention.

## Run the deterministic fixture

No API key is required:

```bash
python3 research/code-locator/src/system_one_code_locator.py \
  research/code-locator/fixtures/repository \
  "Help me optimize the websocket connection implementation" \
  --offline-decider \
  --line-threshold 0.60
```

The offline scorer is only a deterministic fixture implementation. It is not intended to emulate System One quality.

## Run with TypeSafe System One

```bash
export TYPESAFE_API_KEY=...

python3 research/code-locator/src/system_one_code_locator.py \
  /path/to/repository \
  "Help me optimize the websocket connection implementation"
```

Optional environment variables:

```bash
export TYPESAFE_API_URL=https://api.typesafe.ai/v1/systemone
export TYPESAFE_MODEL=jev-latest
```

## Research trace

Use `--trace-file` to create an append-only JSONL trace and `--output-json` to persist the final result:

```bash
python3 research/code-locator/src/system_one_code_locator.py \
  /path/to/repository \
  "Help me optimize the websocket connection implementation" \
  --trace-file evidence/code-locator.trace.jsonl \
  --output-json evidence/code-locator.result.json
```

The trace records:

- the query, model, root, and thresholds;
- every directory/file/line candidate disclosed by the harness;
- every TypeSafe request body without credentials;
- model responses reduced to candidate scores, latency, and token usage;
- every threshold application and retained candidate set;
- the final result and aggregate metrics.

This makes a workflow run useful as research evidence rather than only as a pass/fail CI event.

## Output contract

The final result contains three provenance-preserving layers:

```text
relevant directories
relevant files
relevant snippets { path, start_line, end_line, score, content }
```

It also reports exposed/selected counts, model calls, token usage, and elapsed time.

## Tests

```bash
python3 -m unittest discover \
  -s research/code-locator/tests \
  -p 'test_*.py' \
  -v
```

The tests verify that the deterministic fixture finds the websocket client and that real API requests use independent Noul questions.

## Dedicated research workflow

Code Locator has its own GitHub Actions workflow:

```text
.github/workflows/system-one-code-locator.yml
```

It does not run the Kubernetes experiment.

On relevant pushes and pull requests it runs only the deterministic Code Locator fixture and uploads:

```text
system-one-code-locator-offline-<run>-<attempt>/
  run-manifest.json
  tests.log
  run.log
  result.json
  trace.jsonl
  summary.md
```

A manual `workflow_dispatch` can additionally run the real TypeSafe experiment against a configurable subject repository. That job uses the `typesafe` environment and uploads a separate `system-one-code-locator-typesafe-*` artifact.

After push or manual runs complete, a persist job writes the evidence permanently under `runs/<time>-run-<run_id>-attempt-<n>/`. Pull-request validation never writes back to the repository.

## Research limitations

The current prototype intentionally leaves several questions open:

- whether whole-tree directory enumeration is better than recursive frontier expansion;
- threshold calibration and compounding false-negative risk;
- threshold-only pruning versus keeping a minimum semantic beam;
- line-level scoring versus symbol/block/chunk-level scoring;
- caching repeated judgments across nearby queries;
- comparison against ripgrep, embeddings, language-server indexes, and System Two browsing;
- evaluation against gold relevant-file and relevant-range labels;
- escalation when no candidate survives a stage.

See the [System One Progressive Action Spaces topic](../../docs/topics/system-one-progressive-action-space/README.md) for the shared model behind this demo and the Kubernetes command generator.
