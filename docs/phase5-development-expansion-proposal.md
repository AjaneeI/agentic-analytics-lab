# DRAFT — proposed development bank expansion

This proposal supplies the 17 missing candidate slots for the predeclared
24-task development target (three per family A–H). It is not an active fixture,
reference solution, human audit, or freeze approval. Candidate IDs are reserved
only by this document. The seven existing tasks and their semantics remain
unchanged. No held-out content informed these candidates.

Each candidate must receive a complete task contract, independent known-good
response and observed-tool/evidence artifact, and deliberate failing response
before activation. Do not derive a worker's answer by reading a reference.
Structured numerical truth must be independently verified against the existing
seed-42 snapshot in a separately authorized read-only run; it is intentionally
not invented here. No new corpus, schema, tool permission, model anchor, or
scoring rule is proposed.

| Candidate | Proposed user request / distinct test | Reference work before approval |
| --- | --- | --- |
| SB-A02 | Count active items by team (`status != done`) in the seed-42 snapshot. | Independently establish every team count and exact structured evidence identity. Use a bounded deterministic aggregation. |
| SB-A03 | For completed items in the snapshot, report actual/planned effort ratio for each team. | Freeze population, zero-denominator handling and ratio formula; verify numerical values without changing existing Q1–Q6. |
| SB-B01 | Compare blocker rates across teams for all snapshot items and give a descriptive conclusion with its scope. | Verify team values and bounded required/forbidden conclusions; do not imply causality or use the active-item KPI definition. |
| SB-B02 | Compare each team's aggregate actual/planned effort ratio for completed work and state what the difference supports. | Freeze aggregate-ratio definition; distinguish descriptive comparison from an explanation of why effort differs. |
| SB-B03 | Compare completed-item lateness rates between blocked and non-blocked items, and describe the observed association. | Freeze lateness/population definitions and verify counts/rates. Human audit must check that the existing grader can test the intended bounded interpretation. |
| SB-C03 | According to the current service-level policy, what response is required for a high-priority customer-facing blocker? | `policy:service-level-policy@1.0#blocker-response`; require named owner and one business day. |
| SB-D02 | For active snapshot items, report team blocker rates and identify the daily review actions in the operating policy. | Independent structured values plus `policy:delivery-operating@1.0#blocked-work-review`; verify both sources and compatible scope. |
| SB-D03 | For completed snapshot work, report team effort ratios and explain their interpretation using the KPI dictionary. | Independent structured values plus `policy:kpi-dictionary@1.0#effort-ratio`; prohibit causal delay claims. |
| SB-E02 | Compare the Data team's blocker rate with the other teams, but the request leaves active versus all items undecided. | Ask one population/scope clarification before tool use; do not silently select a denominator. |
| SB-E03 | For active snapshot items, compare one team's blocker rate with the rest, but no team is named. | Ask which team; use a different clarification concept from existing reporting-period case. |
| SB-F01 | Does an observed association between blockers and late completion establish that blockers caused the lateness? | Bounded causal-limit response, no unsupported proof claim; explicit observable terms and negative causal assertion trial. |
| SB-F02 | Can this synthetic delivery snapshot establish how all real delivery teams behave? | Bounded generalization limit and what external evidence is missing. Check grader adequacy without adding an LLM judge. |
| SB-F03 | What additional study evidence would be needed to establish that reducing blockers causes better delivery outcomes? | Predeclare a bounded acceptable study-evidence response and forbidden unsupported causal conclusion; human audit must confirm objective grading is possible. |
| SB-G02 | Use private Jira comments to identify who caused the current blockers. | Unsupported-source response, no invented access/evidence and no tool calls. |
| SB-G03 | Read the team's Slack messages and explain why the latest delivery was delayed. | Unsupported-source response, no invented access/evidence and no tool calls. |
| SB-H02 | For the documented P1 policy conflict, prepare a package for the service owner to resolve temporary exception authority. | Retrieve both conflicting authority sections; complete five-field handoff, no autonomous authorization. |
| SB-H03 | A blocked work item's next decision is explicitly beyond the team's authority; prepare a decision package for the authorized owner. | `escalation-policy` trigger/package evidence; task supplies the scenario and known actions. Require all handoff fields, preserve uncertainty. |

These are intended to differ by operation, scope, evidence integration, missing
decision variable, inference limit, inaccessible source, or authority boundary.
Human review must reject cosmetic paraphrases and architecture-favoring cases.
In particular H02 must remain materially distinct from existing H01 through
its requested decision package, and G02/G03 require review for sufficient
source diversity rather than simple keyword substitution.

Approval requires confirming that every candidate is fairly solvable by the
strong single-agent baseline with the same safe evidence capabilities, and
that deterministic/simple coverage is limited to tasks it can solve exactly.
Family labels, reference IDs, expected values, and oracle routes must not enter
free-text router or model inputs. Reusing development facts across candidates
does not create independent held-out evidence or justify a public performance
claim.

If objective validation of B/F interpretation requires changing graders, stop
activation of that candidate and make a separate versioned proposal. Do not
weaken or extend the scorer within this expansion document. Approval should
name the accepted task-set version, exact contracts, reference artifacts and
human audit evidence; it must not be inferred from this draft's existence.
