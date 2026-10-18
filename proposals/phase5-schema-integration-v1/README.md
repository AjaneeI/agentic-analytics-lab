# Development schema integration — implemented-lane payload parity verified

This isolated branch starts from the inactive adapter/candidate-bank commit
`1cc6fd9`. It adds only the exact approved `phase2-runtime-schema-v1` query
description to the adapter runtime's `_QUERY_TOOL`, plus offline capture tests
and artifacts. The approved description was extracted from local activation
commit `644a68d75cf6743d3daaace51f42a0571747417c`; its source file SHA-256 is
`b0e9c39dbcc868fd6a346778a2a9c6b3418aa828d7b57e8852026623a3b8f289`.
`approved-tool-contract.json` preserves the independently extracted tool JSON
and system prompt, rather than deriving the expected values from this branch's
runtime under test.

Local captures inspect the actual `respond(messages, tools)` inputs for four
implemented paths: strong-single, oracle-routed, natural-language route function
and simple heuristic route function. Each is probed with structured, document,
multi-source and no-source requests. These 16 captures compare the complete
delivered tool JSON and existing system prompt with the approved source.
They execute a fixed final response without calling any evidence tool or live
model. The author captures are implementation checks. A separately authored reviewer
subsequently verified all 16 actual input payloads directly against AST-extracted
activation source at reviewed code commit `ce56556`; its report and reproducer
are preserved as `independent-review.json` and
`scripts/verify_schema_parity_independent.py`. It also blocked network, live
clients/evidence tools and held-out source reads, tested hidden-metadata canaries,
and independently verified the H pre-tool boundary. All 320 tests pass. This
closes only metadata delivery parity for the explicitly captured implementations.

The strong-single tool affordance remains both safe tools for every request.
Actual execution is separately gated by task permissions, including G denial,
H response boundaries and bounded tool/model steps. Routed tool exposure remains
the existing capability/task intersection. No task/reference metadata is added
to the user message, and no model anchor or runtime default changes. The current
development bank remains seven cases; the 24-case proposal is inactive.

The deterministic/simple adapter has no model-facing schema to compare. It
uses its unchanged approved fixed SQL against the same delivery table through
the dataset-scoped read-only tool, with task/tool/disposition/budget gates.
Its data/tool contract is recorded separately. No live ClickHouse equivalence
or model capability is qualified here. Hermes delegated Treatment B and every
architecture not explicitly captured remain unverified.

The branch also contains two separately cherry-pickable review fixes:
`6f40eda` makes the candidate reproduction test preserve any preexisting local
CSV; `4b1f411` makes simple execution decline H and disallowed-answer tasks before
tools. These do not alter frozen fixture/scoring/model controls.

Reproduce from the integration worktree:

```sh
python3 -m unittest tests.system_benchmark.test_schema_metadata_parity tests.system_benchmark.test_baseline_adapters tests.system_benchmark.test_local_worker -v
python3 scripts/audit_baseline_schema_parity.py --check
```

The audit returns 2 when local checks match but independent review/qualification
gates remain open. A mismatch returns 1. The historical schema-less configuration
remains on `sprint/phase5-readiness-20261017` at `1cc6fd9` and is not overwritten.
The report's explicit preparation-input fingerprint is a local version record,
not the approved Phase 2 benchmark-contract fingerprint. The author snapshot retains its historical pending-review field; the separate
independent report supplies the subsequent review evidence. All reviewed source
hashes match this evidence branch. Comparative evaluation
remains blocked by Phase 3/4 acceptance and exact
runtime/provenance configuration approval. This work does not enter or exit
Phase 5 and does not gate standalone Treatment A acceptance.

The original reviewed code commit `ce56556` remains an ancestor of this branch.
Evidence-only files and a local synchronization of identical reviewed PR99 fixes
do not replace that pin or change delivered metadata. To reproduce the exact
review, use a clean detached checkout at the full reviewed commit recorded in
`independent-review.json`, then run the versioned independent script against that
checkout with `--expected-head`, an external `--output`, and `--run-tests`.
Uncaptured architectures, including delegated Hermes Treatment B, remain unverified.
