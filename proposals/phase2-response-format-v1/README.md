# Response-format v1 — inactive offline proposal

**Only offline preparation is approved. No activation or new live attempt is authorized.** Both completed failed experiments and their execution configurations remain unchanged. The scope-observation approval is resolved; this separate response-format proposal requires its own review before any activation.

The existing system prompt names final-response fields without their types. The existing parser correctly accepts object/null clarification and handoff values and rejects strings or other scalar/container types. The observed scope-v1 attempt failed on a string clarification value before scoring. This proposal appends explicit type guidance, with no response repair, parser change or scoring change.

## Candidate and interfaces

`candidate.patch` adds nine lines only to `_SYSTEM_PROMPT`. The exact existing prompt is retained as a prefix. `candidate-system-prompt.txt` contains the exact candidate runtime string, without a trailing newline. Guidance enumerates existing dispositions, nonempty string answer_text, string/null uncertainty, object/null clarification and handoff, and unquoted null when those fields are inapplicable. No task answer, numerical truth, reference metadata or task-specific example is added.

No provider API, structured-output mode, model setting, tool contract, runtime-generated evidence field, budget, security restriction or public response type changes. Optional fields omitted from a response retain existing parser behavior. Parser acceptance does not assert task-specific disposition or handoff validity; those remain existing scorer responsibilities.

The proposal branch preserves all production source and historical configurations at parent execution commit `57c3007a25af4ff21bec42138aa1df7268ee7d95`. The patch is applied only in a separate detached offline-validation checkout. Its local candidate commit is recorded in validation evidence; it is not published as an activated branch.

| Pin | Value |
|---|---|
| Baseline prompt SHA-256 | `e9e29e0ed6ce4e98698ddf328e611ad6ba207c98451e2bd63869b6373914b623` |
| Candidate prompt SHA-256 | `56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce` |
| Candidate patch SHA-256 | `cb494c47cdcb38fe41b0f30b0718ee8d56c9bec25d2a8535d382cd7cba9e62a9` |
| Baseline contract fingerprint | `d136b653e8b4bc2ebabfab403b4aef3c85155174719e7e1c40b290ddf29968f2` |
| Candidate contract fingerprint | `c58b9f0acb2217fca19f0ea199f167e07bf455ad1865fc727e07239249c8d2bc` |
| Inactive candidate config SHA-256 | `7d9640bb187222efd9b866f71a51aa39ea2d7da051a373153e6ac8b6add0ca21` |

`configuration.proposal.json` has a new response-format configuration ID, explicit no-activation authorization and an inactive offline-only runtime gate. It is incompatible with the existing runner's accepted configuration ID and passed-gate requirement. Preserved historical approved configurations do not authorize a repeat of their consumed attempt.

## Offline tests and limitations

The same three candidate regressions fail against the unchanged baseline prompt and pass against the patched checkout. They check explicit guidance, exact preserved prefix/no answer leakage, and actual serialized requests through the real Ollama client with fake HTTP responses. Every new candidate-focused check blocks sockets/DNS and native urlopen except the explicit HTTP fake.

The fake-HTTP sequence returns fabricated SQL/policy tool requests and a fabricated final response. It verifies three model calls, exactly two injected evidence callbacks, unchanged tool JSON/options, and evidence refs/structured values generated from actual fixture callbacks rather than model-supplied observations. No SQL is executed and no scorer is called by these candidate checks. Scripted fixtures are engineering controls, not live-model compliance or quality evidence.

Nine parser regressions preserve object/null, optional omissions, all existing dispositions, runtime-owned evidence refs and strict rejection of strings (including `"null"`), booleans, arrays and numbers. Existing parser and scorer bytes are unchanged.

Both proposal and offline-candidate checkouts pass 359 full tests on Python 3.11 and 3.12 with sockets/DNS denied. Three candidate-focused tests pass on both versions. Counts overlap and are not additive. An initial fake policy fixture used positional fields incorrectly; it was changed to named fields, with the failed test log retained. No runtime or experimental result was changed to address it.

One independent whole-proposal offline review at implementation commit
`1eca40abc6656a37588f812f853cd4001c14c8ac` and candidate commit
`d4922de83113fa5477aaadfca8f110e600770eb5` found no must-fix defect in this
bounded scope. Its report and reproducer are in `validation/independent-review.json`
and `validation/verify_independent.py`. It independently reran nine proposal
parser checks and twelve candidate/parser checks on both Python versions,
verified full-suite log hashes, patch bytes, fail-closed guards, decision coverage
and both sealed experiment hash sets, with no scorer or live service calls.
Subsequent additions record review evidence/status only; candidate source,
prompt, patch, configuration, tests and decision brief are unchanged.
The reproducer is the archived exact review invocation: it requires the recorded
local workspace paths and reviewed commits, and intentionally refuses a later
evidence-only HEAD. It is not a portable installer or activation command.

Standard full suite from either checkout:

```sh
python3 -B -m unittest discover -s tests -q
```

Candidate-only regressions, from the patched offline checkout:

```sh
python3 -B -m unittest discover -s proposals/phase2-response-format-v1 -p test_candidate_prompt.py -v
```

Running the latter against the proposal branch's unchanged runtime is the intentional RED control and must fail for missing prompt guidance. Offline validation artifacts and preservation checks are stored in `validation/`. Do not call the live qualification CLI to validate this proposal.

## Decisions and research gates

The linked [Phase 3–4 brief](../../docs/phase3-phase4-decision-brief-2026-10-17.md) records options and recommendations for owner adjudication. Recommendations are not enacted decisions. Phase 2 remains unqualified; Phase 3 findings, Phase 4 freeze, development-bank acceptance and architecture comparisons remain separate open gates. A changed candidate prompt also requires renewed parity review before any future comparison; earlier schema parity does not cover this candidate automatically.

Deliverable: inactive patch/configuration, offline evidence, independent review and draft PR. No merge, ready transition, automatic review, provider call, activation or further experiment is authorized by this proposal.
