# Agent Operating Contract

This repository is evaluation-first. Agents must preserve evidence, benchmark integrity, and claim boundaries.

## Before making changes
1. Read `PROJECT.md`, `STATUS.md`, `DECISIONS.md`, `ARCHITECTURE.md`, and the relevant tests/docs for the task.
2. Inspect the current branch, open PRs, and recent commits before proposing architectural changes.
3. Apply this order: question requirements -> delete unnecessary work -> simplify -> speed up -> automate.
4. Prefer the smallest reversible change that satisfies the stated acceptance criteria.

## Non-negotiable boundaries
- Do not silently change frozen benchmark semantics, Q1-Q6, scorer logic, seed-42 data, model baseline, ClickHouse permissions, prompt/tool contract, or official evidence methodology.
- Do not introduce an LLM judge into the frozen benchmark.
- Do not broaden tool permissions beyond least-privilege/read-only defaults without an explicit recorded decision.
- Do not present development fixtures, oracle metadata, historical results, or smoke tests as evidence of generalization.
- Do not reintroduce rejected approaches merely because they are fashionable or convenient; check `DECISIONS.md` first.
- Do not claim success from implementation alone. Verify with tests, artifacts, or reproducible evidence.

## Benchmark execution budget — no Codex credits
- Do not use Codex credits for benchmark implementation, debugging, testing, execution, or review.
- Do not request Codex code/security review or use Codex as a fallback when deterministic tooling is sufficient.
- Prefer standard-library code, local tests, GitHub Actions, CodeQL, and inspectable source-backed review.
- Before creating or readying a reviewable PR, account for any external automatic-review trigger that could consume Codex credits.
- PR #68 demonstrated that marking a draft ready triggers Codex here. Do not repeat that transition without verifying the applicable automatic review is disabled; absence of an immediate bot comment is not verification.

## Evidence discipline
For any meaningful change:
- state the acceptance criteria;
- run the smallest relevant deterministic verification first;
- run broader tests only when justified;
- preserve provenance for benchmark/evaluation outputs;
- distinguish implementation status from evidence status;
- record uncertainty rather than inventing certainty.

## Architecture changes
Before changing architecture:
1. Identify the problem the change solves.
2. Identify the simpler baseline.
3. Define what evidence would justify added complexity.
4. Check `DECISIONS.md` for prior evaluations.
5. Record the decision if the change materially alters architecture, evaluation semantics, evidence boundaries, or operational policy.

## Closeout
Before declaring work complete:
1. Run relevant tests/verification.
2. Check whether public docs now overclaim or understate the evidence.
3. Update `STATUS.md` when current state or next steps changed.
4. Update `DECISIONS.md` only when an actual durable decision was made.
5. Report exactly what changed, what was verified, what remains unverified, and the next bounded step.

## Nested instructions
A nested `AGENTS.md` may be added only when a subtree genuinely needs rules different from this root contract. Local instructions may narrow these rules, not weaken repository safety or evidence constraints.
