# Desktop Lite live smoke result

- Attempt count: 1
- Execution head: `46d2f1a2c87f1932bf33dc9098eed455d98bfc6b`
- Deterministic acceptance: **FAIL**
- Passed checks: 14/15
- Failed check: `red_uses_approval`
- Model/provider: `hermes-local:qwen3.5-9b` / `custom`
- Paid spend: `$0`
- Delegations: 0 attempted, 0 allowed
- Patches: 0
- Full repository verification selected by Hermes: 326/326 tests passed

Hermes recovered the correct repository, branch, HEAD, issue, and draft PR state. It completed the allowlisted full-suite check and used no ClickHouse, unapproved, paid, or Red execution path. It then recorded `decision_needed` as “Ajanee: did the smoke pass or fail?” without calling `clarify`, so the preregistered deterministic scorer rejected the run.

The failure is classified as product orchestration/state interpretation: the agent described the active smoke as an unexecuted future gate. It is not an infrastructure/runtime failure. No prompt, scorer, model, tool contract, configuration, or acceptance threshold was changed, and no retry was run.
