# Approved expression-JIT-off runtime activation — no live experiment authorization

The owner approved `runtime-clickhouse-expression-jit-off-v1` as a separately versioned Phase2 runtime configuration on October17,2026 America/New_York. The approval permits applying only `compile_expressions=0` and preparing/verifying an immutable execution configuration. **It explicitly does not authorize another live TreatmentA.** PR111/112 evidence justifies testing the configuration; it does not establish original timeout resolution.

## Exact runtime change and immutable configuration

The approved historical patch SHA256 is `2a8bb4c3c6c8794a1414ab3c51f279e8f7b1a2d74e03326c9df840336c1b6aca`. The transport file now exactly matches candidate SHA256 `aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c`: one added HTTP request parameter `compile_expressions=0`, with no other transport AST difference from executed `bd717bb844aba39fd2edba69aa6094d8fe926340`. Existing SQL validation, table scope, semantic guards, authentication, timeout and failure behavior are unchanged.

New configuration: `configurations/phase2-runtime-schema-v1-scope-observation-v1-response-format-v1-expression-jit-off-v1.activated.json`. Config SHA256 `5da27c405734b48cb64dd731180c3d6db447d72073166ea8f2329697d2f42df9`; complete benchmark contract `6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4`. The model-facing query-tool contract remains `0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9`; schema `delivery-work-items-schema-v1`, scope observation `runtime-sql-scope-v1`, response prompt `phase2-response-format-v1` SHA256 `56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce` stay unchanged.

The configuration records activation approval separately from `live_treatment_a_authorization: not_granted` and `authorized_live_attempts: 0`. No live experiment is scheduled or launched. The runtime source is activated only in this isolated versioned checkout; PR111/112 are not merged and existing historical configurations are unchanged.

## Preserved model and resource contract

Ollama model `hermes-local:qwen3.5-9b`, digest `0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c`, local URL `http://127.0.0.1:11434`, temperature0, num_predict512, num_ctx65536, timeout120s, keep_alive30m. Task SB-D01 uses its existing development data/route and frozen scorer; no dataset, fixture, expected response, task reference, corpus or evaluator method changes.

ClickHouse HTTP timeout15s, readonly1, server execution10s, result rows1000, result overflow break, input rows10000, read bytes10485760, memory134217728 and threads2 remain fixed. The two allowed evidence tools remain query_clickhouse/retrieve_policy; six model steps, two evidence calls, zero retries and zero re-prompts remain fixed. No provider, output format mode, warm-up, SQL rewrite, permission or global server setting change.

## Activation guards and offline validation

The qualification adapter recognizes the new exact configuration ID and verifies its approved transport version, activation approval, transport hash, one-parameter amendment, complete fixed request settings and15s client wait. It retains all existing schema, scope, standalone, source/config/contract, prompt approval/hash, model, budget and capture guards. Only source_preflight changes among existing runner functions. Its activation status and execution status are separate.

Default source-only preflight must report `activation_ready: true`, `activation_blockers: []`, `execution_ready: false`, and `execution_blockers: [live_treatment_a_not_authorized]`. Its exit2 is the expected fail-closed result. Explicit --run also refuses before task access, services, model construction, worker entry or output reservation while the configuration remains unauthorized. A caller-supplied approval-reference string alone cannot bypass the configuration guard.

Eleven guard regressions first failed on the previous runner and pass after activation wiring. They cover activation-vs-run separation, exact settings/transport pins, unapproved activation, inherited prompt approval, changed resource/client limits, Boolean attempt-count rejection and a future-authorization fixture exercised only offline. Both full suites pass375tests on Python3.11/3.12 with sockets/DNS denied.

The historical inactive-patch reproduction test originally failed because production already contained the approved patch. Its engineering wrapper now obtains the exact historical baseline via git show, verifies its original hash, applies the historical patch only in a disposable copy and runs the same six unchanged candidate checks. Neither the historical proposal/manifest nor scientific criteria were altered. The wrapper accepts only the pinned original or approved candidate transport source. Red and green evidence is preserved.

## Effective settings verification and freshness

No additional SQL or live diagnostic is conducted for this activation-only task. The complete sealed PR112 evidence bundle (`d1dabdad7c4616eb7499e850a84064822060069dc00da1cfe4f3b16aa30dca96`) is reverified. Its candidate settings capture came from the identical approved transport hash and exact request parameters/client timeout. Server query `df181b4e-2ac1-464c-b993-61e81437ca34` returned HTTP200, compile_expressions=false, readonly1 and every fixed resource limit above on server26.8.4.11. The raw response SHA256 is `218d765af65af15ef871b9d00655c333858223a8c08b38560414114a71bf34ab`.

This binds the activated bytes to observed effective settings; it is a preserved observation, **not a fresh server check**. The original transport returned true; declared scalar/aggregate fixtures agreed across15cells with zero observed difference. V1's Boolean-checker stop remains sealed asfailed, and V2 issued only five previously unissued requests. These diagnostic results do not prove all-query equivalence, actual JIT-on compilation, cold/warm independence, speedup, exclusive JIT causation or original timeout resolution. Fresh environment/service preflight remains necessary after any future experiment is separately authorized.

## Proposed invocation and remaining authorization

The review packet records the exact new execution commit, configuration hash, runner/capture hashes, complete source-file fingerprint and proposed commands. The safe preflight command omits --run and contacts no services. The proposed --run invocation is recorded **as text only**, includes the current activation-only pins, and is blocked by this configuration's zero live authorization. No output directory is reserved for it.

Activation approval is resolved and must not be requested again. A future experiment requires separate explicit owner authorization for one new standalone bounded attempt under a reviewed immutable runtime configuration. That authorization must be durably bound to a newly reviewed authorization record/configuration with exactly one authorized attempt, producing a new configuration hash/commit and a final exact invocation. It cannot reuse consumed historical authorizations, silently amend the current immutable configuration, retry an observed failure or infer permission from activation approval.

After that separate approval, final preflight must verify the exact approved local model/digest, existing schema/data, loaded source/configuration/contract pins, unchanged limits and passive evidence capture. No architecture comparison or held-out work is implied. Original failures remain preserved with no score invented; frozen scorer changes, new statistical methods, broader security/provider access and PR merges remain separate decisions.

## Independent model-free preparation

Phase3 follow-up reproduces all nine original evaluator mismatches on Python3.11/3.12. Current observation controls still reject a valid CTE and wrongly accept a fabricated metric under an active filter. Transport activation cannot constitute evaluator acceptance. The eighteen frozen artifacts match; no scorer or expectation is changed.

Phase4 independently verifies3,000 preserved endpoint records and6,000 seeds, with zero numerical summary disagreements and seven tests passing on both Python versions. Fifteen preserved source/evidence files match. The task-delta documentation versus task-plus-independent-arm-repeat resampling mismatch remains open; raw matrices/draw arrays are absent, so endpoints were not independently regenerated. All twelve P4 decisions remain open and freeze is deferred. No new simulation or decision threshold is introduced.

Phase2 remains unqualified, Phase3/4 remain unaccepted, comparisons/held-out work remain blocked and October23 Phase5 entry remains at risk. No new live TreatmentA, diagnostic SQL/model call, automatic Codex review, merge or unrelated activation occurs under this approval.
