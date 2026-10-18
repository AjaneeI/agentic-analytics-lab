The frozen development scorer rejects valid alternatives and accepts incorrect
answers despite conforming response envelopes. The real D01 worker also
rejects correctly filtered active-work SQL when its rows omit a scope label,
while accepting a literal percentage and false scope label from an unfiltered
row. This preserves the defects as model-free evaluator evidence without
changing production code, frozen contracts or scoring semantics.

The original audit remains byte-identical: 7/7 authored references pass,
17/22 negative controls reject correctly, 5/9 valid alternatives pass, and
nine mismatches remain unresolved. It documents ambiguity, policy/version
authority and task-template overlap. A separate eight-case integration
characterization loads the actual frozen D01 task/reference, regenerates
unchanged seed-42 data in a temporary directory, executes SQL on in-memory
SQLite through the production SQL validator, and runs the real worker,
repository-local policy retrieval and frozen scorer. Independent counts
confirm Data at 8/45 active items (17.7778%). Four integration controls match
expectations; three valid queries wrongly reject and one invalid query
wrongly passes. Both report commands intentionally exit 2.

All 18 frozen inputs match base
`58add5e58e581be21d3511fc4cd2cb5be44f49b7`. Source and generated-data hashes,
queries, actual rows, runtime observations, exact scores and reproduction
commands are preserved in `experiments/evaluator-validation-20261017/`.
Scripted tool decisions/final prose and SQLite behavior do not establish
model quality or live ClickHouse qualification.

Validation: four audit tests, four integration tests and all 297 repository
tests pass locally on Python 3.14.7; Project Context Protocol and diff checks
pass. Integration execution also passes with network connections, live model
construction/methods and external ClickHouse transport blocked. The original
audit still imports no model/tool runtime. Hosted Python 3.11/3.12 checks
remain pending for this update.

This is preparation under #94/#95, not Phase 3 acceptance. Phase 2 remains a
separate prerequisite. Runtime SQL provenance is the selected remedy
direction, with implementation/activation handled separately and approval
required before activation. No live model, external database, paid provider,
held-out access, automatic Codex review or automatic merge is involved.

Refs #94, #95. This PR does not close either gate.
