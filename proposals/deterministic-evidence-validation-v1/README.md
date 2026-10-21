# Inactive deterministic raw-evidence validation v1

This opt-in adapter correction prepares the existing development baseline. It
does not activate a configuration or qualify any benchmark/phase. It is stacked
on PR104 head `15256f598e70bb09032120c0f0c0cf9e289a25fe`; PR99/104 and original
evidence remain unchanged. Coordinator queue: issue95 comment6322040363;
executor pickup6322090272. Implementation commit and content pins are in
`candidate.json` (SHA256
`a72a3eb63bbf78946c7fe4a190add66030c6525c920d455f76f816000e320b72`).

## Observed defect and correction

The shared handler normalizes team with `str`, counts with `int`, and metrics
with `float`. The opt-in adapter checked only normalized evidence: a missing
team could become the name `None`, Boolean counts became integers and fractional
counts were truncated. Malformed containers and oversized numbers could also
escape as conversion errors. No actual database query was needed to reproduce
this defect: the callback returned newly authored synthetic rows.

Only this adapter now validates the callback's raw list/dictionaries before
passing the same rows to the unchanged handler. Teams must be nonempty strings;
numeric fields cannot be Boolean, null, containers, invalid or nonfinite values;
counts cannot be fractional. Existing whole numeric counts and decimal-integer
strings remain accepted, as do finite numeric metrics and numeric strings.
Integral floats preserve previous valid callback behavior. Input rows remain
unchanged; errors do not cause another callback. Existing count/rate bounds,
unique-leader behavior, request applicability, permissions and budgets remain.

The existing tool decodes JSONEachRow with `json.loads`; numeric strings are
therefore possible, and the existing handler explicitly accepts them. Quoted
integers/floats are documented in the [ClickHouse output-format settings](https://clickhouse.com/docs/reference/settings/formats/output-format#output_format_json_quote_64bit_integers).
No server-setting default is assumed or changed. No cross-field rate/count
consistency, rounding, population, tie, SQL or scoring rule is added.

## Offline evidence

- Existing adapter baseline: 18 tests pass on Python3.11.16.
- Before correction, seven new methods produce 17 assertion failures (false
  acceptance) and 11 errors (malformed inputs escaping the decline boundary).
- Candidate: 39 focused adapter/handler tests pass on Python3.11.16 and3.12.6.
- Complete repository suite: 332 tests pass on each interpreter.
- Focused runs deny network, subprocess and SQLite access; none was attempted.
  Full-suite wrapper denies network/database access and permits inspected local
  regression children (read-only Git and Python validation). Existing child
  probes contain their own guards; fake transports do not perform inference.
- Initial full-suite wrapper was overbroad for macOS temporary policy fixtures
  and guard-under-test paths: 18 errors and one failure per interpreter were
  preserved, then its repository-file guard was scoped correctly. No product
  fix was made to accommodate that wrapper error.
- Preservation manifest compares all192 base paths:191 unchanged, with only
  the opt-in baseline source changed; a new test file is added. Shared handler,
  SQL, scorers, tasks, references, generator, model/runtime and prior evidence
  bytes are unchanged. This document/STATUS/config are preparation additions.

Commands and raw logs remain in the executor workspace at
`outputs/deterministic-evidence-validation-v1-20261021/`. No raw archives from
the separately rejected PR123 publication are included or re-exported. This
package's code/configuration/docs may be reviewed independently of those logs.
Scripted and injected tests do not establish live data or model compliance.

## Remaining gates

Independent exact-commit review and draft delivery are the engineering closeout
steps. They do not close Phase2 qualification, Phase3 evaluator acceptance,
Phase4's twelve methodological decisions or Phase5 entry. Existing runtime
equivalence and numeric observation-mapping limitations remain. No TreatmentA,
failed SQL replay, held-out evaluation, live model/database/service operation,
new resource observation, statistical calibration, automatic review or merge is
authorized or performed by this preparation.
