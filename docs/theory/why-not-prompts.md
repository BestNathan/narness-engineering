# Why not just prompts

## 1. Prompts are soft constraints

A prompt is a piece of natural-language text that "requests" or "suggests" an agent do something, rather than "enforcing" it. Whether the constraint takes effect depends on whether the agent:

1. notices the text
2. correctly understands its meaning
3. remembers to comply at the specific decision point
4. judges compliance as more important than other goals

If any link breaks, the constraint fails. All four links depend on the agent's "goodwill", not on any verifiable mechanism.

## 2. Three failure mechanisms

### 2.1 Attention dilution

In a long context, one prompt competes for attention against a mass of information. As the conversation grows, constraints written early (even in the system prompt or CLAUDE.md) get gradually diluted, and at the specific decision point the agent may not even "think of" the constraint.

### 2.2 Probabilistic compliance

An LLM is a probabilistic model, not a rules engine. The same prompt, under different contexts and different sampling, is obeyed to different degrees. Today it remembers to write tests; tomorrow it may forget.

### 2.3 Conceding when goals conflict

When "following the constraint" conflicts with "finishing the current goal" — for example, hurrying to fix a bug, where skipping tests looks "faster" — the agent may rationalize the constraint away.

## 3. Why hard constraints work

Code, hooks, and scripts are hard constraints:

- They don't depend on the agent noticing — a hook fires automatically on an event
- They don't depend on the agent understanding — a script outputs a deterministic pass/fail
- They don't depend on the agent choosing to comply — a compile failure is a failure, no negotiation possible

## 4. Conclusion

Prompts are suited to expressing "intent" and "why", not to bearing the "must-do what". Constraints should sink as far as possible into the hard-constraint layers. This is Narness's core premise; see [the constraint ladder](constraint-ladder.md).
