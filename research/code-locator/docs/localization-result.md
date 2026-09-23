# Canonical Code Localization Result

The code-locator experiments use one result contract independent of the execution strategy.

Both System One and System 2 runs emit:

~~~text
localization-result.json
~~~

Execution traces remain separate artifacts.

## Schema

~~~json
{
  "schema_version": 1,
  "kind": "code-localization-result",
  "task": "Help me optimize the websocket connection implementation",
  "producer": {
    "system": "system_one",
    "model": "jev-latest",
    "confidence_semantics": "..."
  },
  "summary": {},
  "confidence": null,
  "files": [
    {
      "path": "web/src/platform/socket/WebSocketService.ts",
      "role": "relevant",
      "confidence": {
        "score": 0.91,
        "label": "high",
        "type": "derived_max_evidence_relevance",
        "basis": "maximum retained observation relevance for this file"
      },
      "reason": "why this file is considered valuable",
      "evidence": [
        {
          "id": "web/src/platform/socket/WebSocketService.ts#evidence-1",
          "start_line": 1,
          "end_line": 140,
          "confidence": {
            "score": 0.91,
            "label": "high",
            "type": "noul_relevance",
            "basis": "System One observation relevance score"
          },
          "reason": "why this source range is considered valuable",
          "content": "1: ...\n2: ..."
        }
      ],
      "provenance": {}
    }
  ]
}
~~~

## Semantics

### files[]

This list contains the producer's final valuable files, not every file it inspected.

For System One, a file enters the final list when at least one observed range is retained above the observation threshold.

For Claude Code, the list is the model's final localization judgment after its repository investigation.

### role

~~~text
relevant
primary
supporting
context
unknown
~~~

System One currently emits `relevant` because it does not make an additional semantic primary/supporting/context classification.

Claude Code may emit `primary`, `supporting`, or `context`.

Role mismatch is therefore descriptive and should not automatically be treated as an error.

### file confidence

`files[].confidence` answers:

> How strongly does this producer consider this file valuable to the task?

For System One it is currently derived from the maximum retained evidence relevance in the file.

For Claude Code it is the model's explicit self-assessment.

### evidence[]

Each evidence record identifies a source range the producer believes is valuable:

~~~text
path + start_line + end_line
confidence
reason
content
~~~

The canonical result contains the actual source text for the range.

System One already possesses the text from its read observation.

For Claude Code, the normalizer materializes the exact source range from the pinned repository revision after validating the model's path/range output.

### confidence

Confidence is always structured:

~~~json
{
  "score": 0.91,
  "label": "high",
  "type": "noul_relevance",
  "basis": "..."
}
~~~

Labels are presentation helpers:

~~~text
high    >= 0.80
medium  >= 0.60
low     <  0.60
~~~

The important field is `type`.

Current types include:

~~~text
noul_relevance
derived_max_evidence_relevance
model_self_assessment
~~~

These scores are not assumed to be calibrated to each other.

A System One Noul relevance of 0.85 and a Claude self-assessment of 0.85 are two observations with different semantics, not necessarily equal probabilities.

## Producer-specific provenance

The canonical result permits producer-specific provenance without changing the common comparison fields.

System One currently records file provenance such as:

~~~text
phase1_score
last_activation_score
activation_count
read_count
stop_reason
~~~

Evidence provenance includes the probability of the selected read action.

Claude's repository-search trajectory is not embedded in the final result. It remains in:

~~~text
claude.raw.jsonl
execution-path.json
execution-summary.md
~~~

This separation is intentional:

~~~text
ExecutionTrace = how the result was reached
LocalizationResult = what the producer ultimately considers valuable
~~~

## Comparison contract

Future comparisons should consume only two canonical `localization-result.json` files.

The generic comparator records symmetric observations:

~~~text
shared files
left-only files
right-only files
file-set Jaccard
role differences
file confidence pairs
evidence-region overlap in both directions
evidence-line overlap in both directions
missed regions in both directions
~~~

Neither side is treated as ground truth.

Absolute accuracy requires an independently reviewed gold set.
