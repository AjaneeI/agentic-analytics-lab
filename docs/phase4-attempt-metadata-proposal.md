# Inactive attempt-metadata consistency proposal

This optional utility checks a proposed metadata document by explicit manual
invocation. It is not imported by the runner, scorer, statistical comparison,
or any workflow. Its input format is a candidate explanatory format, not a
change to either benchmark's artifact contract. No Phase 4 method or analysis
plan is accepted or frozen, and all P4-01 through P4-12 remain unresolved.

```sh
python3 scripts/validate_attempt_metadata.py /path/to/proposed-metadata.json
```

The command reads one UTF-8 JSON file and prints a JSON consistency report to
standard output. Exit 0 means its supported metadata assertions are consistent;
exit 2 means invalid metadata, unreadable input, or malformed JSON. It does not
write reports, repair input, read referenced evidence, execute queries or call
services. The CLI suppresses Python bytecode writes as well.

## Candidate input

The top-level `examples` list contains hand-authored metadata records. Each
record separates a planned slot from any observed attempt and its evidence.
For example, a planned slot with no execution observations can be represented
as follows. Names containing `EXAMPLE` are labels, not benchmark identities.

```json
{
  "examples": [{
    "planned_slot": {
      "slot_id": "EXAMPLE-SLOT",
      "task_id": "EXAMPLE-TASK",
      "treatment_id": "EXAMPLE-ARM",
      "repeat_label": "EXAMPLE-REPEAT",
      "pairing_key": null,
      "pairing_status": "not_selected"
    },
    "attempt_id": null,
    "evidence_events": [],
    "artifact_evidence": "unknown",
    "score_evidence": "not_supplied_in_example",
    "timeout_evidence": "unknown",
    "query_log_export_evidence": "not_available",
    "planned_roster_member": true,
    "statistical_missingness_status": "unassigned_owner_policy_required",
    "analysis_denominator_membership": "unassigned_owner_policy_required",
    "exclusion_adjudication": "unassigned_owner_policy_required",
    "recovery_relation": null
  }]
}
```

Event records require a `kind`, `scope`, nonempty `evidence_locator`, and a
positive integer `sequence_within_example`. This ordinal describes the supplied
example order; it is not a timestamp, duration, timeout budget, or synchronization
claim. The utility does not dereference locators or verify authenticity.

| Event kind | Required scope |
|---|---|
| `launch_failed_before_invocation` | `launcher` |
| `invocation_started` | `worker_invocation` |
| `completion_observed` | `worker_invocation` |
| `timeout_terminal` | `worker_invocation` |
| `timeout_observed` | `client_request` |

Artifact availability is `unknown`, `present_in_example`, or
`absent_in_example`. Score evidence is either `not_supplied_in_example` or
`score_locator_present_in_example_no_score_value`; actual score values are
unsupported. Query-log export availability is `unknown`, `not_available`, or
`present_in_example`. Timeout evidence is `unknown`, `not_observed`,
`observed_client_request_timeout`, or `observed_worker_invocation_timeout`.
The latter two require their corresponding scoped events. `not_observed`
cannot accompany a timeout event.

The validator rejects duplicate slot IDs, duplicate planned task/treatment/repeat
coordinates, duplicate attempt IDs, repeated lifecycle markers, contradictory
pre-invocation/worker events, multiple worker terminal events, invalid ordinal
ordering, worker starts after worker terminal evidence, and mismatched or absent
event scope. It rejects unsupported row claims and assignments of pairing,
denominator, exclusion, recovery, or missingness policy. An optional
`observability_description` must agree with its event evidence. An optional
top-level `no_selected_policy` mapping may contain only null values.

## Deliberately preserved uncertainty

A client-request timeout does not establish worker termination. A client can
observe a timeout even after a separate worker completion record; those scopes
are not interchangeable. Missing start telemetry does not contradict independent
terminal evidence. An unavailable query-log export does not invalidate a
completion or artifact. A score locator can remain available when a raw artifact
was not preserved. A timeout event can coexist with any artifact-availability
state. None of those cases assigns an analysis denominator or outcome.

Consistency is not evidence authenticity, statistical usability or scientific
acceptance. Incomplete evidence, actual recovery lineage, approved policies and
other formats require separate owner review; this small proposal does not
implement a general metadata framework. No historical attempts are reclassified,
and a Phase 2 operational failure is not used as calibration evidence.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_attempt_metadata -v
python3 scripts/check_project_context.py
```

The tests use hand-authored metadata, local temporary files and subprocesses.
They do not import benchmark scorers, model workers or statistical resampling
helpers. Broader repository tests include simulations and bootstrap draws and
were not run under this proposal's no-draw execution boundary. This candidate
does not establish hosted CI results or activate any runtime behavior.
