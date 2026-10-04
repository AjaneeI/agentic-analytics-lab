# Verified Project Status

_Last reviewed against the active System Benchmark v1 PR C development state on 2026-10-04._

## Current verified state
- The frozen Q1–Q6 benchmark remains unchanged historical/bounded evidence.
- The project keeps three distinct evaluation lanes:
  - single-agent baseline;
  - oracle-metadata routed execution;
  - natural-language routing evaluation.
- The accepted GitHub-hosted comparison remains execution-layer evidence only because the intended route came from frozen benchmark metadata.
- System Benchmark v1 is the active architecture-level evidence program.
- PR A (#63) merged the typed task/response contracts, deterministic fixture loader, fingerprint inputs, and model-free validation foundation.
- PR B (#65) merged the repository-local policy corpus and deterministic read-only retrieval on 2026-10-04.
- PR B's squash merge commit `c5accae04908f3fc4e89eee05038f70a84db2df7` is green on post-merge `main` Python and CodeQL workflows.
- PR C (PR #67, tracking issue #66) is the active implementation slice: development-only fixtures plus deterministic reference/scoring contracts.
- The PR C working implementation contains:
  - 24 development tasks, exactly three per family A–H;
  - one known-good observable reference solution per task;
  - deterministic per-dimension scoring with explicit reason codes;
  - coverage for missing/wrong evidence, policy-version mismatch, unsupported-source fabrication, required/unnecessary escalation, policy conflict, historical policy identity, structured values, claims, clarification/handoff state, tool behavior, and validator outcome.
- PR C scoring/reference code remains model-free and does not import runtime agent/router modules.
- Isolated Python 3.13.13 verification currently passes 19 new PR C tests and all 228 repository tests; source compilation and diff whitespace checks pass.
- These are implementation/regression checks, not model-performance or held-out evidence.

## Current merge gate
PR C is not accepted evidence until:
- focused PR C tests are green on the published branch;
- full Python 3.11/3.12 checks are green on the final head;
- CodeQL is green;
- substantive review findings are resolved or technically dispositioned;
- deterministic repeated scoring remains identical;
- reference/fixture validation remains model-free;
- `evals/questions.json` remains byte-for-byte unchanged.

## Next approved implementation slice
After PR C merges, proceed to the routing-treatment / worker-adapter slice described
in the approved System Benchmark v1 implementation plan.

Do not create held-out cases or execute model-performance comparisons in PR C.

## Evidence boundaries
Landing PR B establishes deterministic local policy evidence capability, not model quality.
Landing PR C establishes the deterministic evaluation core, not single-agent or
routed-agent superiority, unseen-task generalization, or publication-ready results.

## Staleness rule
This file is not authoritative when it conflicts with repository evidence. GitHub
issues, PRs, commits, workflow runs, tests, and benchmark artifacts take precedence.
