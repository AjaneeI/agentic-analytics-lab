# Inactive development lineage validation

The opt-in `src.evals.development_lineage` module checks a single pinned
`inactive-source-lineage-v1` source manifest. It is not called by benchmark
runners, loaders, CI workflows, or scoring. It writes no files and has no
benchmark path defaults. Supply the manifest SHA-256 independently; computing
it from an untrusted manifest does not establish selection authority.

Every invocation requires explicit `--manifest`, `--manifest-sha256`, `--node-id`,
`--tasks`, `--references`, `--corpus-manifest`, `--kpi`, and `--scorer` arguments.
Run `python -m src.evals.development_lineage --help` for the complete interface.
The five source roles are explicit local file paths. The scorer is hashed; it is never imported or run. Informational AST digests
from earlier inventories are not compared: AST serialization differs across
Python versions, while the exact scorer byte hash remains authoritative.

The manifest contains `lineages` and `field_bindings`. A lineage binds the task
and reference file/object SHA-256 and JSON pointers, KPI corpus entry/version/
path/section, scorer bytes, expected population-scope literal, and content
binding ID. Each field binding names its node, declared source, JSON pointer,
value and canonical JSON SHA-256. The standalone tests provide temporary input
examples; no benchmark fixtures or approved population choices are replaced.
Canonical JSON uses sorted keys, compact separators and unescaped Unicode.
Field pointers reject malformed escapes, negative/noncanonical array indexes,
missing keys and out-of-range indexes.

Validation checks file/object/field digests, unique selected node, development
split, task/reference joins, typed structured and policy source identities, KPI
section content, population metadata and the final binding digest. A different
task file is rejected even if it reuses the same benchmark label. Identical
reference/KPI bytes can be shared across snapshots without inventing a version
difference. The corpus document scope (such as `analytics`) stays distinct from
the metric population literal (such as `active_work_items`).

Exit 0 returns `source_integrity_validated`. Exit 2 reports rejection or missing
explicit inputs. Even success always reports `evaluator_accepted=false`,
`selection_authority_verified=false`, and `runtime_provenance_verified=false`.
Hashes identify selected source bytes; they do not adjudicate A01 population,
D01 version authority, wording semantics, answer correctness, dataset snapshot,
query provenance, metric/ranking derivation or any phase gate. This validator
neither activates a selection nor establishes that a manifest is owner-approved.

It does not read held-out inputs, execute SQL, load a model, call a service, or
rescore historical attempts. Future activation, population/version policy,
runtime validation and evaluator remediation remain separate decisions.
