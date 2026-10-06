# M0.5B Post-success Delegation Retirement Plan

## Scope

Run one B-only successor to issue #85. Preserve Study A and the original M0.5
results. Change only the local Hermes one-shot parent runtime so a completed
single-child delegation removes `delegate_task` from that parent's model-visible
tool surface. Keep the existing benchmark plugin enforcement unchanged.

## Tasks

1. Add failing Hermes runtime tests for post-success retirement, unchanged child
   result, pre-success visibility, failed-child behavior, and non-one-shot control.
2. Implement the smallest runtime change in `tools/delegate_tool.py`; run focused
   Hermes and existing one-worker enforcement tests.
3. Add the B-only frozen manifest, runner, deterministic tests, and exact runtime
   patch/hash evidence to this repository; commit, tag, push, and preregister on
   GitHub before any Hermes model invocation.
4. Execute B1/B2/B3 once, preserve raw requests/events/stdout/stderr/timing/hashes,
   deterministically score 3/3, analyze without tuning, update issue #85 and draft
   PR #83, and stop.

## Global constraints

- No Study A rerun or reinterpretation.
- Same B prompts, goals, markers, Qwen model, context, temperature, hard
  one-worker enforcement, zero retries, and 3/3 threshold.
- Incremental paid spend is $0.
- No prompt, model, validator, SQL tool, architecture, or external enforcement
  change.
- No second model run after any observed result.

## Review focus

Confirm success detection cannot retire on validation failure, failed child, or
background dispatch; the returned child result is byte-for-byte unchanged; and
the external plugin still blocks any attempted extra delegation.
