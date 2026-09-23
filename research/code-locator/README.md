# System One Code Locator experiment records

This directory contains repository-persisted evidence for Code Locator experiment runs.

Each recorded workflow run uses a time + GitHub run ID directory:

```text
YYYYMMDDTHHMMSS+0800-run-<run_id>-attempt-<attempt>/
```

Example:

```text
20260923T124223+0800-run-35819390521-attempt-1/
├── README.md
├── offline/
│   ├── run-manifest.json
│   ├── tests.log
│   ├── run.log
│   ├── result.json
│   ├── trace.jsonl
│   └── summary.md
└── typesafe/
    ├── run-manifest.json
    ├── run.log
    ├── result.json
    ├── trace.jsonl
    └── summary.md
```

The timestamp is generated in UTC+8.

The workflow persists records after experiment jobs complete. Push and manually dispatched runs are written back to the triggering branch. Pull-request validation does not write to the repository.

The record commit is produced by `github-actions[bot]` and uses:

```text
research: record code locator run <run_id>
```

The records path is intentionally excluded from the Code Locator workflow path filters, so persisting a record does not recursively start another Code Locator experiment.

Artifacts are still uploaded to GitHub Actions for convenient download, but the files here are the durable research history owned by the repository.
