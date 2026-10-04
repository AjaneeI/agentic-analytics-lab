# Verified Project Status

_Last reviewed against the model-free dry-run candidate on 2026-10-04._

## Current verified state

PR A (#63), PR B (#65) and PR C (#68 / #66) are merged. Main at the start
of this milestone was `6982f67`; the original 230-test suite passed there.
The frozen Q1–Q6 historical comparison and route-inference/execution distinction
remain unchanged. The current candidate is issue #71's execution-contract and
scripted dry-run rehearsal, not a model or held-out evaluation.

## Candidate verification

- 278 full tests pass on sandbox Python 3.11.16, 3.12.14 and 3.13.13.
- 130 focused System Benchmark tests pass.
- Seven real-evidence scripted controls pass; fourteen deliberate defects are
  detected through their intended reason codes.
- Full canonical reports are byte-identical across all three Python versions;
  hash-seed/process repeatability and offline/no-model-import tests pass.
- Compilation, context-protocol and whitespace checks pass.

Evidence/reproduction: `experiments/system-benchmark-dry-run-v1/README.md` and
`rehearsal.json`. Hosted Python/CodeQL results must match the published candidate
revision; see its PR/issue checkpoint. This status is not a merge declaration.

## Corrections and boundaries

SB-D01's development-only oracle now explicitly uses active work (Data 8/45,
17.8% rounded), rather than silently pairing all-item 20.9% with an active-work
policy. The seven-case bank is still development-only. Three bounded PR C scorer
regressions were fixed; frozen Q1–Q6 and its original scorer are unchanged.

Actual local policy retrieval is executed. Structured data uses labelled
`sqlite_seed42_replay`, not a live ClickHouse connection. Case-ID scripts are
oracle scaffolding, not route inference. No performance/generalization claim,
new framework, paid inference, held-out fixture, or chain-of-thought scoring.

## Cost and integration gate

NO Codex credits, tasks or reviews. PR #68's ready transition did trigger an
automatic Codex review; the earlier absence-of-comment check was insufficient.
Do not repeat a ready/open-review event without a verified no-Codex trigger path.
Keep the tested candidate isolated/draft. Existing protections remain required.

## Next bounded step

Review and integrate this verified rehearsal without a Codex trigger; only then
scope live development execution. Do not reopen PR C or merge stale repair
branches blindly. The 24-case/eight-family roadmap target has not been completed
by this seven-case integration rehearsal.

## Staleness rule

GitHub commits, PRs, test artifacts and workflow runs take precedence over this
summary. Distinguish a tested candidate from code accepted on main.
