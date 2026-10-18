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

## Actual HTTP request serialization — schema delivery only

`wire-delivery.json` preserves 16 actual `urllib.request.Request.data` payloads
and their byte hashes from the real `OllamaModelClient.respond` implementation:
four implemented lanes × four capability probes. An HTTP fake returns one fixed
final response; socket/DNS access and evidence callbacks are denied. Private and
held-out Python file opens are blocked during the captures, and hidden task-ID,
reference-ID and truth canaries are absent from complete wire bytes. A synthetic
private response field is not recorded. These are bounded guards, not a general
privacy guarantee. No inference, database/evidence call or held-out access occurs.

The new audit independently extracts tool schemas/descriptions and the system
prompt from AST of approved commit `644a68d`, rather than using proposal JSON or
the client's serialization helpers as expected values. It compares the complete
wire function definitions and system/user messages, fixed local `/api/chat`
destination, POST/content type, timeout and explicitly supplied probe model ID.
Mutation tests that drop wire tools or replace the wire prompt are rejected.

**The runtime configurations differ.** The real development client still emits
temperature 0, `num_predict=128`, `num_ctx=2048` and a 30-minute keep-alive. The
Phase 2 qualification client source emits `512` and `65536`. Neither source was
changed. Schema delivery parity does not establish the same model/runtime
configuration, live model identity, model quality or architecture-comparison
eligibility. The wire report explicitly retains those unverified/blocked states.
Its supplied model ID is an offline forwarding probe, not a qualified model.

Reproduce into a **new** artifact; an existing output is never overwritten:

```sh
python3 -B scripts/audit_schema_wire_delivery.py --output /tmp/schema-wire-delivery-new.json
python3 -m unittest tests.system_benchmark.test_schema_wire_delivery tests.system_benchmark.test_schema_metadata_parity -v
```

Expected audit exit is 2: wire delivery verified, runtime equivalence and
comparative approval absent. The optional `--repository` argument supports a
separate-process audit of an activation checkout; it records only the three
routed lanes when the strong-single adapter is absent. Matching options there
would still not establish runtime equivalence. The approved `644a68d` Git object
must be available: the standalone audit fails closed otherwise; integration
tests explicitly skip when that external approved-source object is missing in a
shallow checkout, without substituting runtime or proposal expectations.

Local verification passed eight focused schema tests and all 325 repository
tests on Python 3.14. The five new wire tests also passed on Python 3.11 and 3.12.
Compilation, context protocol and whitespace checks pass. Runtime/task sources
and the original three metadata JSON reports remain byte-identical to `590fd22`.
These local checks do not substitute for hosted CI/CodeQL or accept any phase.
