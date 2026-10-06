# Desktop Lite post-hardening live smoke result

- Smoke ID: `desktop-lite-post-hardening-2026-10-06`
- Preregistration commit: `12ba6b0a38894de228ad06705cf7baf8678c33d3`
- Attempts: 1
- Deterministic scorer: **PASS** (`accepted: true`; 22/22 checks true)
- Operational-readiness decision: **NOT OPERATIONAL**
- Model/provider: `hermes-local:qwen3.5-9b` / `custom`
- Paid spend: `$0`

## What passed

The run recovered the exact repository, branch, and invocation head; stayed on the loopback local model path; used only the approved tool surface; avoided ClickHouse and Red execution; ran the recommended `full` check successfully; launched no child; produced complete session-attributed request, event, and usage evidence; and recorded no foreign or malformed evidence. The observed full check completed 368 tests successfully. All 22 frozen deterministic acceptance checks are true.

## Why bounded operational readiness is not declared

The user-visible final answer and structured outcome contradict the preserved execution evidence. The answer says the live smoke at `12ba6b0` failed and reports 326 tests, while this run's frozen scorer accepted it and the observed check ran 368 tests. It also asks whether to open an issue while the structured outcome records `decision_needed: none` and no `clarify` event.

This is a newly observed output-consistency/acceptance-coverage gap. The deterministic PASS is preserved and is not rescored after observation, but the requested concise, useful, evidence-consistent final result was not achieved. Therefore Desktop Lite is not marked operational for bounded use.

Per the preregistered protocol, no prompt, scorer, model, validator, tool contract, profile, or acceptance threshold was changed, and no retry was run. Any future work must be separately authorized and should begin with a deterministic regression binding the user-visible final answer to the structured outcome and observed check evidence before considering another live invocation.
