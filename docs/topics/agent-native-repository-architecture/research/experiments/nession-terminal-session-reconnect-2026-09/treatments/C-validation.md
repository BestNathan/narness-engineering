# Treatment C Validation

```yaml
treatment: C-agent-native
branch: research/ai-native-repo-c-agent-native
frozen_sha: 3e544761d5b89dc09a631533659dca4862f9e559
validation_pr: BestNathan/nession#892
workflow_run: 35554845228
started_at: 2026-09-21T02:38:26Z
completed_at: 2026-09-21T02:40:23Z
conclusion: success
```

Treatment C localizes the six selected semantic capabilities and their primary evidence under `web/src/units/terminal-session/`, while legacy production paths remain thin compatibility projections.

Final isolated validation passed:

```text
npm ci          PASS
npm test        PASS
npm run build   PASS
npm run lint    PASS
```

No production behavior change is intentionally introduced by the structural conversion.
