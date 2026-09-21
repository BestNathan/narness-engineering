# Executable Formal Runner

The revision-1 runner is implemented in:

```text
scripts/ai-native-repo-experiment.py
```

It is intentionally agent-agnostic.

The runner owns experimental isolation:

```text
frozen treatment SHA
  ↓
detached Git worktree
  ↓
treatment-specific task fixture
  ↓
fresh operator-supplied agent command
  ↓
hidden acceptance
  ↓
repository verification
  ↓
run.json + logs + final.diff
  ↓
worktree destruction
```

## Example

```bash
python3 scripts/ai-native-repo-experiment.py \
  --source-repo ../nession \
  --task docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/manifests/T07.json \
  --treatments docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/treatments.json \
  --treatment A \
  --agent-cmd 'my-agent --cwd "{worktree}" --prompt-file "{prompt_file}"' \
  --output-dir ./research-runs
```

The exact agent command is part of the recorded run and must remain fixed across A/B/C comparisons.

## Task manifest shape

```json
{
  "task_id": "Txx",
  "prompt": "exact frozen task statement",
  "fixtures": {
    "A": {
      "patch": "relative/path.patch",
      "preflight_commands": []
    },
    "B": {},
    "C": {}
  },
  "oracle": {
    "ref": "<frozen research-ci SHA>",
    "files": [
      {
        "source": ".research/ai-native/acceptance/Txx.test.ts",
        "destination": "web/src/.../__research_Txx.test.ts"
      }
    ]
  },
  "acceptance_commands": [
    "cd web && npm test -- src/.../__research_Txx.test.ts"
  ],
  "verification_commands": [
    "cd web && npm run build",
    "cd web && npm run lint"
  ]
}
```

Fixture patches and hidden acceptance material must live outside the coding agent's discoverable worktree until the runner applies or executes them.

## Trace integration

The runner captures the agent process stdout/stderr generically.

A harness that exposes structured tool/model traces should additionally write them into `$NARNESS_RUN_DIR`. The post-run scorer can then compute search/read/resolver/context metrics without coupling the core runner to one model vendor or coding harness.

## Admissibility

`run.json` intentionally starts with:

```json
"admissible_for_final_analysis": false
```

A separate post-run review marks a run admissible only after:

- hidden acceptance validity;
- trace completeness;
- artifact relevance scoring;
- no cross-treatment/session contamination;
- correct frozen treatment and fixture identities.


## Hidden-oracle timing

The runner materializes `oracle.files` only **after the agent process exits**. After acceptance completes, those files are removed before repository verification and final diff capture.

Therefore the coding agent cannot discover the hidden acceptance implementation through filesystem search, while the run remains locally reproducible from the frozen oracle Git SHA.
