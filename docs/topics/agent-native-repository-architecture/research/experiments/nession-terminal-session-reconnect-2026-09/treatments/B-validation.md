# Treatment B Validation

```yaml
treatment: B-semantic-index
branch: research/ai-native-repo-b-semantic-index
head_sha: 8fb6e8707f2dc967a900e227bb899b0c75336d2e
validation_pr: BestNathan/nession#889
workflow_run: 35548498258
started_at: 2026-09-21T00:41:38Z
completed_at: 2026-09-21T00:43:50Z
conclusion: success
```

Treatment B adds only the `.ai-native/` semantic capability index and deterministic resolver.

Validation passed the isolated research gate:

```text
npm ci          PASS
npm test        PASS
npm run build   PASS
npm run lint    PASS
```

This confirms the initial B scaffold does not alter Nession runtime behavior or break the existing Web verification surface.

The validation does **not** yet establish that the semantic index improves agent performance. That requires formal A/B runs with fresh isolated sessions.
