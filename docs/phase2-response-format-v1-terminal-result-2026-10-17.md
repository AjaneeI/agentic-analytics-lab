# Response-format v1: approved activation and terminal experiment report

The owner-approved single standalone Treatment A ended in **execution_error: ClickHouse query failed: timed out**. It did not produce a final normalized response, TrialExecution or deterministic score. Score absence is not zero. **Phase 2 remains unqualified.** No repair, response normalization, SQL replay, rescore, retry or follow-up model call was performed. This run does not establish response-format compliance because the evidence-tool boundary failed before a final response.

## Exact version and authorization

The owner explicitly approved activation of the reviewed `phase2-response-format-v1` candidate and one new bounded attempt after final validation. That authorization is now consumed; remaining authorized attempts: **0**. The previously resolved scope-observation approval was not requested again.

| Pin | Exact value |
| --- | --- |
| Execution commit | `bd717bb844aba39fd2edba69aa6094d8fe926340` |
| Configuration ID | `phase2-runtime-schema-v1-scope-observation-v1-response-format-v1` |
| Configuration SHA256 | `b215429b8e93a260b13d3f109758b908721d8d2f14b0491388672b135650be92` |
| Contract fingerprint | `c58b9f0acb2217fca19f0ea199f167e07bf455ad1865fc727e07239249c8d2bc` |
| Prompt SHA256 | `56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce` |
| Approved prompt patch SHA256 | `cb494c47cdcb38fe41b0f30b0718ee8d56c9bec25d2a8535d382cd7cba9e62a9` |
| Worker file SHA256 | `6792a09622514a6ee94d3ae461e0cef40dd91a6381a9045fa7dd4f58f78a18aa` |
| Qualification runner SHA256 | `980d6478375fa5a81d7d97b35dd7ea6feac48ba32a6bbbe5d33f7a36396b38b0` |
| Passive capture SHA256 | `28859a2bdbe12d46bfd8e094e033ce96842b5000116f22a7360b5829853224de` |
| Schema version | `delivery-work-items-schema-v1` |
| Observation amendment | `runtime-sql-scope-v1` |
| Query-tool contract SHA256 | `0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9` |

Activation is reviewable in [draft PR 109](https://github.com/AjaneeI/agentic-analytics-lab/pull/109). The prior inactive proposal and decision brief remain preserved in [draft PR 108](https://github.com/AjaneeI/agentic-analytics-lab/pull/108). Separate evidence-only branch records this terminal outcome; the execution checkout remains clean at its original pin.

## Frozen configuration and validation

The only runtime method difference from the previous scope-v1 execution is the exact approved nine-line response-type prompt guidance. The qualification runner adds an exact new configuration ID, approval/version gate and prompt-hash checks. Its other guard, execution, capture and CLI functions remain unchanged by independent AST review. Parser, frozen scorer, fixtures, dataset generator, SQL security, provider API and options remain unchanged. No structured-output mode, coercion or increased budget was enabled.

Model `hermes-local:qwen3.5-9b`, digest `0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c`. Local Ollama at `http://127.0.0.1:11434`, temperature 0, num_predict 512, num_ctx 65536, model timeout 120 seconds, keep_alive 30m. Existing ClickHouse read-only HTTP timeout remains 15 seconds. Dataset: existing seed-42 development data, 500 rows, 13 schema columns. Task SB-D01 uses the existing metadata-supplied multi-source route. Limits remain six model steps, two evidence-tool calls, zero retries and zero re-prompts. Only query_clickhouse and retrieve_policy are allowed.

Final source preflight reported zero blockers. Four activation regressions first failed on the existing runner, then passed on the new guards. Full suites: **363 tests on Python 3.11 and 363 on Python 3.12**, with sockets/DNS denied. Three focused prompt/delivery tests passed on each version; historical baseline RED evidence remains archived. Object/null and optional-field parsing remain unchanged; invalid strings including quoted null, booleans, arrays and numbers remain rejected. Tests use scripted responses and fake HTTP; they cannot establish live-model compliance.

The legacy wire audit failed offline because it still expected the historical prompt. A separate versioned auditor changed only the approved source commit and worker-hash constants, retaining the full remaining AST and network/evidence guards. Twelve actual-client/fake-HTTP captures then verified exact prompt, schema, tools and options. Exit 2 explicitly retains blocked comparative evaluation. No live call occurred in these audits. Independent final activation review found no must-fix issue and verified its configuration/source pins before launch.

Fresh read-only service preflight confirmed Ollama 0.35.0, exact model digest, exact 13-column schema and 500 rows. Existing local credentials were loaded without logging values or changing permissions. The live runner repeated its source/service checks before reserving the run.

## Exact observed outcome

| Observation | Value |
| --- | --- |
| Start UTC | 2026-10-18T02:26:42.456707+00:00 |
| End UTC | 2026-10-18T02:27:59.120214+00:00 |
| Worker entries | 1 |
| Model attempts / returns | 1 / 1 |
| Tool attempts / returns | 1 / 0 |
| Failure | RuntimeError: ClickHouse query failed: timed out |
| Deterministic score | Absent; worker raised before scoring |
| Worker wall time | 74.782956416 seconds |
| Capture wall time | 76.662519292 seconds |
| Outer launch wall time | 77.225358167 seconds |
| Returned input / output tokens | 839 / 352 |
| Returned model-duration seconds | 58.491868042 |
| Collector | Complete, no collector errors |
| Postflight | Commit, configuration and contract valid/unchanged |
| Retries / re-prompts | 0 / 0 |

The error occurs while awaiting the first ClickHouse HTTP tool response. Passing schema/count setup does not establish the cause of that later timeout. The captured generated SQL was not replayed, edited or substituted. No service or query fix was attempted after observing this outcome. There is no final answer to evaluate for response-format compliance, valid SQL alternatives or fabricated numerical values.

## Resource evidence and limits

The returned model usage is 839 input and 352 output tokens; known model duration is 58.491868042 seconds. The worker-host process lifetime peak RSS after capture is 32,718,848 bytes. Its before/after user CPU delta is 0.011159 seconds and system CPU delta 0.053022 seconds; these are host/capture process observations, not Ollama compute totals. Before capture the approved model was not loaded; after capture the shared Ollama snapshot reports size and size_vram of 7,693,192,396 bytes and context 65,536. This is not per-request GPU/VRAM, energy or peak model-memory measurement. The model-loading state is recorded, without normalizing timing or making cross-run performance comparisons.

Incremental local-provider paid spend is $0; this excludes Codex engineering credit accounting. Human hands-on minutes were not measured and are not inferred. Raw before/after snapshots remain in local sealed evidence.

## Preservation and evidence index

All 20 original failed-run file hashes and all four scope-v1 failed-run file hashes match their sealed inventories. Both prior failed experiments, schema-only configuration, approved scope configuration and inactive response-format proposal remain unchanged. The new four raw files are sealed separately; the independent outcome review verifies them without invoking the model, SQL, parser or scorer. Exact raw hashes are recorded in outcome-summary.json and the raw sha256.json inventory.

- `activation-red.txt`: four activation regression failures before runner implementation.
- `python311-full.txt`, `python312-full.txt`: final 363-test suites.
- `python311-candidate.txt`, `python312-candidate.txt`: exact prompt/fake-HTTP checks.
- `approved-source-preflight.json`, `final-validation-receipt.json`: pins and unchanged boundaries.
- `final-service-preflight.json`: setup-only schema/count/model verification.
- `final-wire-delivery.json`: twelve fake-HTTP captures, no live inference.
- `independent-final-activation-review.json`: pre-entry independent offline review.
- `run-command.json`, `outer-result.json`, `run-stdout.txt`, `run-stderr.txt`: single launch and terminal status.
- `outcome-summary.json`: exact score absence, usage, timing, snapshots and raw hashes.
- `independent-outcome-review.json`: separate sealed-result verification.
- `pinned-source/`: exact configuration, prompt, tools, client, runner and scorer artifacts.
- `response-format-v1-attempt-evidence.zip` and archive-sha256.json: local reproducible evidence package.

Raw evidence directory: `outputs/treatment-a-response-format-v1-20261017`. The bundle retains raw evidence locally; GitHub receives a curated factual summary, without credentials or hidden reasoning. No held-out files were opened.

## Phase 3–5 gates and next actions

[The preserved decision brief](https://github.com/AjaneeI/agentic-analytics-lab/blob/phase2/response-format-v1-proposal-20261017/docs/phase3-phase4-decision-brief-2026-10-17.md) covers all nine Phase 3 mismatch controls, nine runtime-observation limitations and twelve Phase 4 decision IDs with evidence, consequence, options, recommendation and owner decision. None of those recommendations is enacted by this run.

Phase 3 draft PR 98 retains nine known evaluator mismatches, including valid alternative rejection and fabricated numerical values that can pass. The prior model-free evidence reports 7/7 references, 17/22 bad-control rejection and 5/9 valid alternatives passing. Runtime observation controls do not resolve evaluator validity. No frozen scorer change was made.

Phase 4 draft PR 100 retains model-free simulations, coverage/width/null false-positive/Monte Carlo evidence and all twelve open decisions. The documented task-delta and implemented task-plus-independent-arm resampling mismatch remains unresolved. Existing evidence cannot justify a method freeze; defer freeze until the owner selects an inferential target, pairing and other decisions through a reviewed version. No fresh simulations or data-dependent tuning occurred in this activation.

Phase 5 draft PRs 99 and 104 preserve the inactive 24-case bank and strong-single/schema-delivery adapter preparation. The active bank remains seven cases. Independent acceptance, semantic false-positive controls, exact runtime parity and provenance remain open; the new prompt requires independently verified parity before any future comparison. Standalone qualification does not authorize comparison with schema-less historical configurations. Phase 5 entry by October 23 remains at risk and is not claimed.

Next authorized work is review of this sealed failure and the existing research decision brief. A read-only diagnosis of the timeout may inspect existing logs and captured SQL without replay. Any runtime change, timeout/budget increase, experimental amendment, scorer correction or future live attempt requires its applicable separate reviewed authorization. No experiment authorization remains. No PR was merged; no automatic Codex review, paid provider, Treatment B, architecture comparison, held-out evaluation or deployment was triggered.

GitHub is the technical record. Notion and Asana are reconciled after GitHub evidence exists; reconciliation receipts are included with this report. The two-hour execution window limits new work after 02:30:50 UTC; this attempt began at 02:26:42 UTC, and subsequent actions only seal, review, publish and reconcile its completed evidence.
