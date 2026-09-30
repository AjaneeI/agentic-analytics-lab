# Verified Project Status

_Last reviewed against the repository default branch and open PR state on 2026-09-29._

## Current verified state
- The public README reports 146 Python tests passing on Python 3.11 and 3.12.
- GitHub Actions and CodeQL are presented as passing on `main`.
- The project has three explicitly separated lanes:
  - single-agent baseline;
  - oracle-metadata routed execution;
  - natural-language routing evaluation.
- The accepted GitHub-hosted comparison reported:
  - single-agent baseline: 12/18 task successes across three runs;
  - oracle-metadata routed execution: 17/18 task successes across three runs.
- That routed comparison is execution-layer evidence only because the intended route came from frozen benchmark metadata.
- Natural-language routing has a development evaluation lane, but the repository explicitly does not treat the current development set as evidence of generalization.
- The next public evidence gates in the README are:
  - establish a reviewed post-hardening single-agent comparison anchor;
  - preserve exact commit/artifact provenance for every published comparison;
  - evaluate natural-language routing on a held-out or novel-request set;
  - compare routing gains against latency, calls, tokens, cost, and maintenance complexity;
  - choose an explicit repository license if reuse is intended.

## Recent default-branch milestones
Recent merged work includes:
- natural-language routing benchmark lane (#47);
- failure diagnostics, provenance, and efficiency metrics (#46);
- System Benchmark v1 design and implementation plan (#52/#54);
- reusable project-health reporting (#53);
- README/architecture refreshes and benchmark visualization.

## Open work / PRs
Open PRs visible on 2026-09-29 include:
- #58 — post-hoc failure diagnostic sidecar refinement;
- #51 — model-sensitivity runner;
- #48 — bounded validated-throughput runner;
- #45 — experiment dependency graph / architecture documentation refresh;
- #2 — historical single-agent benchmark stabilization draft.

These PRs should be treated according to their own scope and evidence boundaries; open implementation does not equal accepted evidence.

## Current next step
Use System Benchmark v1 as the next architecture-level evidence program while keeping the frozen Q1-Q6 comparison intact as historical/bounded evidence.

Before broadening claims, prioritize:
1. held-out or novel natural-language routing evaluation;
2. validated-throughput evidence from a recorded environment;
3. model-sensitivity evidence as a separate study, not a silent baseline replacement;
4. failure attribution that remains observable and non-speculative;
5. architecture decisions recorded in `DECISIONS.md`.

## Staleness rule
This file is not authoritative when it conflicts with the repository itself. If tests, PRs, workflows, or benchmark artifacts disagree with this document, update this file after verifying the repo state.
