# Raw Data Retention Policy

> Status: defined before reportable formal collection.

The research needs two different storage layers:

```text
Git repository
  compact, reviewable, permanent research record

Raw run archive
  complete sealed traces/diffs/logs needed for deep audit/reanalysis
```

Committing every raw run directly into Git is intentionally avoided. A 216-run
collection can contain large JSONL traces and logs that are poor Git history
material.

## What is committed to Narness

The publication bundle contains:

```text
research-report.md
raw-runs.csv
summary.*
paired-effects.*
failure-summary.*
reviewed conclusion
collection-start.json
collection-manifest.json
research-completeness.json
research-artifact-manifest.json
raw-archive-manifest.json
frozen benchmark / analysis / execution-plan inputs
publication-manifest.json
```

This is sufficient to identify the study, inspect all aggregate/task-level
measurements, understand every conclusion, and verify the content identity of the
full raw dataset.

## What stays in the raw archive

The deterministic raw archive contains only files represented by the sealed
formal collection:

```text
_collection/collection-start.json
_collection/collection-manifest.json

for each scheduled run:
  seal.json
  every artifact named by seal.json
  review.json when represented by collection-manifest.json
```

It excludes:

```text
_incomplete/ quarantined runs
unsealed scratch files
dependency caches
unrepresented local files
```

Create it only after collection verification:

```bash
python3 scripts/archive-ai-native-raw-runs.py \
  --runs-root /path/to/formal-runs \
  --collection-manifest /path/to/research-results/collection-manifest.json \
  --output /path/to/archives/nession-ai-native-r2.zip
```

The command also writes:

```text
nession-ai-native-r2.zip.manifest.json
```

The manifest records the deterministic archive SHA-256, archive size, file count,
per-file hashes, collection digest, formal-plan identity, and benchmark/analysis
revisions.

## Retention rule

Keep at least one durable copy of the raw archive outside the mutable local
working directory.

Suitable destinations include a GitHub Release asset or durable object storage.
The archive itself does not need to live in Git if its published manifest and
SHA-256 identity do.

Do not replace an archive in place. If raw data must legitimately change, the
collection is no longer the same content-addressed research artifact and must be
published under a new identity.

## Incomplete runs

Quarantined/interrupted runs under `_incomplete/` are forensic execution records,
not formal observations.

Keep them during the study when practical, but they are deliberately excluded
from formal aggregation and the canonical raw archive.

## Privacy / secret hygiene

Before moving raw archives to shared storage, verify that agent logs/traces contain
no credentials, private tokens, or unrelated local environment secrets.

The coding-agent subprocess scrubs harness-internal `NARNESS_*` variables, agent
network access is disabled, and the formal sealer rejects known hidden-evaluation
access. These controls reduce leakage risk but do not replace archive review.
