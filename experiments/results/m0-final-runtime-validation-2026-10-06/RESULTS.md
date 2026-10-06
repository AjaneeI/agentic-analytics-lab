# M0 Final Runtime Validation Result

Verdict: **FAIL — M0 exit criterion not met.**

Freeze: `f92f7090256d81286b1278e50fa094519eb11599` / tag
`m0-final-runtime-validation-v1`.

The preregistered validation executed exactly once in 628.646 seconds with
zero retries, zero human intervention, and $0 incremental paid spend.
Preflight and postflight fixed-state checks passed.

## What held

- exactly one delegation and one child;
- no second worker or extra delegation;
- policy retrieval occurred first and succeeded;
- post-child `delegate_task` retirement held across every later parent request;
- the child used the approved fully qualified table and the correct blocker
  percentage formula;
- no paid or cloud fallback was configured or used.

## What failed

1. The child again generated nonexistent grouping identifier `team_id` rather
   than the schema column `team`.
2. Its first ClickHouse call timed out after the successful parent preflight,
   so the repaired wrapper received no HTTP error body to classify.
3. The child then attempted four more evidence calls despite the exactly-once
   instruction; the existing evidence budget blocked all four.
4. Only the policy call succeeded. The deterministic scorer rejected the
   trajectory because it contained six evidence attempts rather than exactly
   two successful calls.
5. The final response was fenced JSON rather than the required bare JSON and
   reported an incomplete result.

## Attribution correction

The generated `orchestration.json` counts four budget-blocked calls as parent
evidence because those event records omit `delegated_child`. Raw event order is
authoritative: all six evidence attempts occurred between `delegate_pre` and
`delegate_post`, so all six came from the child. The parent made no evidence
call after the child returned.

The five recorded interventions comprise one child query timeout plus four
child enforcement blocks.

## Classification and decision

The failure includes:

- **model/tool-contract understanding:** repeated use of nonexistent
  `team_id`;
- **infrastructure/runtime:** the child request timed out even though the
  parent live preflight passed;
- **model instruction-following / orchestration:** four extra child evidence
  attempts and fenced final JSON;
- **enforcement intervention:** four extra attempts were correctly blocked.

This is not accepted M0 evidence. M0 remains incomplete, Hermes Desktop is not
yet verified as Ajanee's primary local interface, and M1 is not authorized.
The preregistered stop rule applies: preserve this evidence and do not start a
new M0.x chain or another model run.
