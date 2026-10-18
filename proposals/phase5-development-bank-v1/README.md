# INACTIVE — 24-case development candidate bank

This proposal contains the unchanged seven existing development task/reference
contracts followed by 17 proposed additions, reaching three candidates per
family A–H. **The active bank remains seven tasks.** No task-set activation,
human task/reference audit, interface freeze or Phase 5 entry is approved here.
All six new B/F cases have unapproved semantic validity.

The unchanged seed-42 generator ran in a temporary directory, producing 500 CSV
rows (SHA-256 `cb3e85f970aa640624444ffc9dd13ffe7f3cbee9e97ab78050c34c35ab9d33ef`).
Five local SQLite SELECT operations were independently cross-checked against
Python aggregation. They establish candidate numeric facts about that generated
CSV. They do not qualify live ClickHouse syntax, transport, Float32 precision,
model output or production behavior. The CSV and SQLite database are temporary.

`reference_controls.json` preserves 24 authored passing response/observation
controls and 24 deliberate negative controls that fail for the stated reason
under the existing scorer. Each passing control includes actual offline SQL
rows or bounded local policy-retrieval payloads. These are reference authoring
controls, not model trials. The preparation code never supplies reference
metadata to a model, and it makes no model or external database calls.

`validation.json` also preserves six unsupported causal/generalization answers
for B/F that **incorrectly pass** the unchanged lexical grader. The 24 passing
controls therefore establish grader mechanics, not semantic adequacy. No scorer
or existing criterion was changed to hide these gaps. Human review must address
them through the approved evaluator/versioning process before accepting these
candidates. New numeric cases also need runtime observation-mapping and strong
single-agent solvability verification; current adapters are not qualified for
the full candidate bank.

Reproduce or check from the repository root:

```sh
python3 scripts/prepare_phase5_candidate_bank.py
python3 scripts/prepare_phase5_candidate_bank.py --check
python3 -m unittest tests.system_benchmark.test_candidate_development_bank -v
```

Both preparation commands return **2** after successful preparation/validation
to preserve the explicit acceptance blockers. `--check` returns 1 for missing
or changed generated candidate outputs. The check writes no proposal or active
fixture files. It regenerates temporary CSV data and uses in-memory SQLite.

The candidate task/reference files preserve the frozen seven-case byte prefix
up to the original closing list bracket. Tests also compare all seven parsed
contracts and reference expectations exactly. Existing active files, Q1–Q6,
policy corpus, scoring and model anchors remain unchanged.

Before activation: audit candidate distinctness and fairness (especially G02/G03
source diversity and H01/H02 overlap), audit every reference and negative trial,
resolve B/F semantic controls, qualify observation mapping, confirm approved
baseline solvability and treatment parity, and record the accepted task-set
version and exact candidate artifacts. No held-out data was read or created.
