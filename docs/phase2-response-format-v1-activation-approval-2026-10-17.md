# Owner-approved response-format v1 activation

The owner explicitly approved activating `phase2-response-format-v1` and ONE new bounded standalone Phase 2 Treatment A after final validation in the current chat on October 17, 2026 EDT. Both failed experiments and all original evidence remain preserved. This approval supersedes the prior offline-only boundary for this exact prompt candidate; the historical inactive proposal remains unchanged.

Only the already reviewed nine-line prompt guidance patch is activated. Candidate prompt SHA256: `56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce`; patch SHA256: `cb494c47cdcb38fe41b0f30b0718ee8d56c9bec25d2a8535d382cd7cba9e62a9`; contract fingerprint: `c58b9f0acb2217fca19f0ea199f167e07bf455ad1865fc727e07239249c8d2bc`.

The qualification runner adds an exact configuration ID, explicit approval and prompt-hash guard. It preserves all earlier schema, observation, source, model, security and budget guards. Parser, frozen scorer, fixtures, dataset generator, SQL guards, provider API/options, model digest and 6-step/2-evidence/zero-retry limits remain unchanged. No structured-output API or coercion is enabled.

Final offline suites pass 363 tests on Python 3.11 and 3.12 with sockets/DNS denied. Four activation regressions first failed against the old runner. Candidate prompt delivery tests and independent final activation review must also pass before worker entry; fresh local service preflight verifies schema and 500 rows without task SQL or inference. Scripted tests cannot establish live-model compliance.

The single live outcome must be preserved without repair, rescoring or retry. This is standalone runtime qualification only. Phase 3 evaluator acceptance, Phase 4 statistical freeze and architecture comparisons remain separate blocked gates. No held-out evaluation, paid fallback, automatic review, merge or deployment is authorized.
