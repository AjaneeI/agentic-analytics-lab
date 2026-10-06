# M0.5 Capability Reliability implementation plan

Spec: `experiments/m0-5-capability-reliability/README.md`

1. Add deterministic study evaluators and tests using RED then GREEN.
2. Add a no-retry runner and frozen manifest; test the runner without model calls.
3. Run focused and full tests, validate hashes and installed enforcement state.
4. Commit, tag, publish, and create the preregistration GitHub issue.
5. Execute the seven frozen cases once, preserve raw evidence, and classify results.
6. Commit and publish evidence, update the GitHub issue, and stop.

Global constraints: no model call before step 4; no prompt or threshold changes
after step 4; no paid fallback; no rerun; do not execute M0.6.
