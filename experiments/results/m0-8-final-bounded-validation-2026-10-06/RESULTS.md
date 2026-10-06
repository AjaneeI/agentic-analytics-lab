# M0.8 Final Bounded Hermes Validation Result

M0.8 failed the M0 exit criterion. The single run is preserved without repair
or retry.

Hermes made exactly one valid delegation, created one child, launched no
second worker, and retired `delegate_task` from the only post-child parent
request. The parent made no evidence calls and returned the child's final JSON.

The child failed the evidence-call contract. In its first response it batched
two `query_clickhouse` calls followed by one `retrieve_policy` call. The two
queries succeeded and consumed the two-call evidence budget, so policy
retrieval was blocked. The child then made five more query attempts; all were
blocked. Total child evidence attempts were eight, with six enforcement
interventions.

Because policy evidence never succeeded, the final response could identify
Data at 20.86% but explicitly could not interpret the result using the KPI
definition. The existing scorer wrapper correctly refused eligibility because
the raw trace did not contain exactly two successful evidence calls and no
failed calls.

`orchestration.json` conservatively labels the six blocked events as parent
evidence because the plugin's budget-blocked event shape omits
`delegated_child`. Raw request session IDs prove those attempts were from the
child. This correction does not change the failure verdict because six
enforcement interventions and missing policy evidence independently fail M0.8.

The smallest final successor changes only the child instruction: retrieve
policy exactly once first, wait for the result, then query exactly once; do not
batch or repeat evidence calls. If that successor fails, M0 and dependent M1
work stop for this run.

Retries, Ajanee intervention, and incremental paid spend were all zero.
