# Independent offline review — inactive D01 tie-order preparation

Decision: accept the exact reviewed commit for **inactive preparation only**. No must-fix correctness or preservation findings in the authorized correction scope. This decision does not authorize activation, integration, merge, historical rescoring, a Treatment A attempt, or Phase 3 scientific acceptance.

Reviewed commit: `069407889c46e0a554f25950e77c667589f3138a`

Reviewed tree: `01ee1ae90edb6aafbe936f08bad5679e73317707`

Base commit: `35ce571c448055aee8a2cbc6f841d17a69108d31`

## Scope and preservation

The immutable diff adds eight files, all under `proposals/phase3-d01-tie-order-v1/`. Independently compared Git mode/type/blob identities for all 304 base paths: all remain identical. There are 312 candidate paths. The working checkout was clean at review and validation. All five `contract.upstream_source_sha256` entries match independently read current file hashes. The unchanged PR122 adapter still selects `phase3-d01-provenance-v1`; active scorer, task, data, runtime, original evidence and original verifier paths are preserved by the all-path comparison.

The configured `source_commit` is `ddbf12b9bef118f0ae74abca436242c859519ad3`, the immutable source commit immediately preceding addition of the synthetic configuration. Its diff to the reviewed commit adds only that configuration. All five configured candidate source/contract SHA-256 values match current reviewed bytes. This avoids a self-referential configuration hash while retaining an exact source pin.

## Correctness reasoning

The interpreter changes only metadata retained after its unchanged sort: the complete pre-LIMIT relation, every declared output key, and the requested limit. It retains whole-input grammar, genuine RATE-first descending restriction for truncation, disallowed limited CTEs, source/population/group/lineage checks and unsupported grammar behavior.

Let K be result cardinality, P the strict prefix before the boundary key tuple, and E all complete-relation rows with the boundary tuple. Correct selection has K distinct rows, includes P, and contains only P union E. The candidate enforces those conditions after exact cardinality/unique-team checks, then checks every projected key and value against the independently computed admissible record. Full key tuples use exact Fraction/string values; primary-only equality, claim tolerance and float reconciliation tolerance cannot create peers. Stable sorting makes each equality class contiguous, so the selected non-boundary rows are precisely the mandatory strict prefix. Nontruncating and unordered full-result reconciliation remains unchanged.

Capture identity, execution/call/config/query/result/snapshot/source/contract commitments, success/completeness/origin, exact global co-max selection, claimant membership in this selected capture and false-uniqueness rejection remain intact. The existing 0.2 percentage-point claim tolerance and 1e-12 numeric reconciliation tolerance are unchanged. The proof authenticates neither a live host nor arbitrary Python callers; that documented boundary remains explicit.

## Independent executions

Both exact required interpreters independently ran the guarded `run_validation.py --configuration synthetic-config.json`:

- Python 3.11.16: 18 new unit methods, 28 reused unit methods, 60 reused named controls and 16 new tie-matrix cases passed; 211 memory SQLite connections; zero blocked-effect attempts.
- Python 3.12.6: the same checks and outcomes passed; 211 memory SQLite connections; zero blocked-effect attempts.

Raw stdout/stderr and full JSON reports are retained as `validation-py311.*` and `validation-py312.*`. Both commands exited 0. Guards load before candidate tests; only new synthetic in-memory SQLite captures were used. Network/socket creation, process launches, file-backed databases and active runtime imports were denied by the inherited policy.

The independently authored `probes.py` ran **688 additional NEW synthetic cases on each interpreter**, with zero outcome mismatches. Its independent mathematical oracle compares selected key multisets to the first K exact mathematical key tuples rather than reconstructing candidate required/admissible sets. It exhausts all distinct K-row subsets over varied populations, mixed-direction secondary/tertiary/quaternary keys, rational and zero co-max classes and limits before/inside/after classes. Additional controls cover numeric secondary differences below 1e-12, too few/many/duplicate rows, missing/extra/colliding projected keys, fabricated/bool/string metrics, uncaptured winners, false uniqueness and exact claim-tolerance boundaries. It tests set selection; inherited captured-row sequence reconciliation is unchanged.

Probe reports separately identify deliberate **direct policy self-checks**: six audit-policy denials (socket, subprocess, system, posix_spawn, fork, external SQLite path) plus active-runtime import denial. These self-checks call policy functions directly and never attempt the prohibited effects. Before those deliberate self-checks, actual probe effect-denial count was zero. They must not be confused with a candidate side-effect attempt. Raw probe stdout/stderr and JSON reports are retained as `probes-py311.*` and `probes-py312.*`; both commands exited 0.

No external database, live SQL, model, service, resource operation, historical failed SQL replay/rescore, held-out input, paid provider, hosted/automatic reviewer, merge, new chat or external message was used by this review. Repository metadata commands were separate read-only evidence inspection, outside guarded test executions.

## Non-blocking limitation

The standalone candidate runner validates its five candidate source/contract fingerprints, but does not itself enforce the contract's upstream dependency SHA-256 values before loading the old runner/control modules. This exact immutable review independently verifies those dependencies through both the 304-path comparison and the five listed upstream hashes, so this is not a must-fix for the reviewed inactive package. Any future standalone redistribution/execution should either preserve equivalent exact-tree verification or extend preflight to check those dependencies before loading them. This review gives no approval to an unverified later checkout.

## Evidence limits

These are deterministic synthetic implementation/regression observations. They cannot establish live-model behavior, ClickHouse/live SQL semantic completeness, live provenance authentication, generalization, scientific Phase 3 acceptance or qualification of any experiment. Original failed/blocked outcomes remain historical evidence. The original PR122 adapter's known tie-order mismatch is not repaired or rescored by this separate candidate.

## Exact reviewed file SHA-256 values

- `proposals/phase3-d01-tie-order-v1/PLAN.md`: `7954ed07f0b384da0dc052b0313a59116ecd428229c56ce5e03a92714dbb63e3`
- `proposals/phase3-d01-tie-order-v1/README.md`: `57214a46fefb4afc59f89424cc99d996786c9e851511c153115e748017eb1751`
- `proposals/phase3-d01-tie-order-v1/contract.json`: `b81c561d5fa35ff0fb889c00e8f7bd77517024a3b81113fbececc0140558248b`
- `proposals/phase3-d01-tie-order-v1/run_validation.py`: `0eb6b2ca36aa693c20403ad89b022bd8db4e43b22ad479f0f277bb2ce878ce1a`
- `proposals/phase3-d01-tie-order-v1/synthetic-config.json`: `f016e9fb827a652e1ebffbb53b899ac1b5580734f4bd6710173bab6ebac8d88b`
- `proposals/phase3-d01-tie-order-v1/test_tie_order.py`: `56cce39c70e36d6404301f2ab6beefbfff34be77f899243d6ac5957dbded464c`
- `proposals/phase3-d01-tie-order-v1/tie_sql_proof.py`: `28b34617f915a454152e72fe24f9239aecde4b2e5bf026df461ff3a5ebe55462`
- `proposals/phase3-d01-tie-order-v1/verifier_candidate.py`: `9908084bdbb7cb315b6b98840f340b86efa4ebcef24003721dd4c07c4718a3f4`
