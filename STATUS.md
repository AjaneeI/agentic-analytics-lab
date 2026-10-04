# Verified Project Status

_Last reviewed on 2026-10-04 against PR B source `8276df4`; see commit-specific workflow evidence for integration readiness._

## Current verified state
- The frozen Q1–Q6 benchmark remains unchanged historical/bounded evidence.
- The project keeps three distinct evaluation lanes:
  - single-agent baseline;
  - oracle-metadata routed execution;
  - natural-language routing evaluation.
- The accepted GitHub-hosted comparison remains execution-layer evidence only because the intended route came from frozen benchmark metadata.
- System Benchmark v1 is now the active architecture-level evidence program.
- PR A (#63) merged the typed task/response contracts, deterministic fixture loader, fingerprint inputs, and model-free validation foundation.
- PR B (#65) implements a repository-local policy corpus plus deterministic, read-only policy retrieval.
- PR B's current implementation includes:
  - current versus superseded version selection;
  - historical `as_of` lookup;
  - section-level deterministic ranking;
  - bounded `top_k` and excerpts;
  - path-traversal/corpus-root enforcement;
  - auditable document/version/section identity.
- The policy manifest rejects duplicate effective dates for the same `document_id`, avoiding ambiguous historical version precedence.
- The PR B repair adds real-corpus regressions for historical leakage, mixed-source ranking, strict calendar dates, and the same-action P1 authorization conflict.
- The isolated Python 3.13 sandbox suite passed 208 tests after the repair; the unchanged source snapshot passed 195. This is supplementary, not a substitute for the required Python 3.11/3.12 and CodeQL checks.
- Benchmark work is subject to the no-Codex-credit constraint in D-010. Automatic code/security review settings must be verified off before updating a reviewable PR; preserving a tested branch is not the same as merging PR B.

## Current merge gate
PR B is not accepted evidence until:
- fresh Python 3.11/3.12 and CodeQL checks are green on the final head;
- substantive review findings are resolved or technically dispositioned;
- deterministic repeatability remains intact;
- `evals/questions.json` remains byte-for-byte unchanged.

## Next approved implementation slice
GitHub issue #66 defines PR C: development-only fixtures plus deterministic reference/scoring contracts.

PR C must remain:
- model-free;
- development-fixture-only;
- deterministic and inspectable;
- separate from held-out evidence;
- separate from architecture-performance claims.

## Evidence boundaries
Landing PR B establishes a deterministic local evidence capability, not model quality.
Landing PR C will establish the deterministic evaluation core, not single-agent or
routed-agent superiority, unseen-task generalization, or publication-ready results.

## Staleness rule
This file is not authoritative when it conflicts with repository evidence. GitHub
issues, PRs, commits, workflow runs, tests, and benchmark artifacts take precedence.
