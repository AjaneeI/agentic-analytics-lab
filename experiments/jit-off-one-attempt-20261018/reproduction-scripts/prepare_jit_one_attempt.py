"""Prepare the separately authorized one-attempt configuration; no services."""
from pathlib import Path
import hashlib,json,subprocess
b=Path(__file__).resolve().parent.parent;r=b/'work/phase2-jit-off-authorized';o=b/'outputs/jit-off-one-attempt-20261018'
o.mkdir(exist_ok=False)
approval='''I approve exactly one new, bounded, standalone Treatment A attempt using runtime-clickhouse-expression-jit-off-v1, following successful final preflight.
Create and pin a new immutable authorization configuration and record, including the exact commit, configuration hash, execution parameters, and final invocation.
Before execution, verify the local model and digest, schema and data, source and configuration integrity, experimental contract, resource limits, and passive evidence capture.
Preserve all historical evidence without modification. Keep the existing prompt, model, dataset, SQL guards, scoring methodology, timeouts, and resource budgets unchanged. The only permitted runtime intervention is compile_expressions=0.
Execute exactly one attempt, with no retries, automatic corrections, replacement runs, or additional experiments.
Preserve all resulting evidence, including failures. Do not rescore historical attempts, merge pull requests, modify frozen methodology, or initiate paid provider calls.
After execution, evaluate the result against the established Phase 2 acceptance criteria. Report whether the timeout was resolved, whether the attempt qualifies, and what remains unresolved.
Reconcile GitHub, Notion, and Asana with the results. Stop after reporting. Do not proceed to another experiment without separate authorization.'''
stem='phase2-runtime-schema-v1-scope-observation-v1-response-format-v1-expression-jit-off-v1'
old=r/'configurations'/f'{stem}.activated.json';cfg=json.loads(old.read_text())
assert hashlib.sha256(old.read_bytes()).hexdigest()=='5da27c405734b48cb64dd731180c3d6db447d72073166ea8f2329697d2f42df9'
cfg.update(live_treatment_a_authorization='approved',authorized_live_attempts=1,
 authorization_record_id='runtime-clickhouse-expression-jit-off-v1-one-attempt-20261018',
 authorization_configuration_parent_commit='4d98b8f09b89e9d44aad39d41409cfcec67740ee',
 authorization_configuration_parent_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
 live_authorization_record='docs/jit-off-v1-one-attempt-authorization-2026-10-18.md',
 live_authorization_source='Explicit owner message in current chat, October 18, 2026 America/New_York; exactly one new bounded standalone attempt after final preflight.',
 authorized_evidence_directory=str(b/'outputs/treatment-a-jit-off-v1-20261018'),
 authorization_consumption='One exclusive outer launch record plus the existing passive capture invocation marker; no retry/replacement/output reuse. Immutable configuration remains a historical authorization record after consumption.')
path=r/'configurations'/f'{stem}.one-attempt-20261018.json'
path.write_text(json.dumps(cfg,indent=2)+'\n');digest=hashlib.sha256(path.read_bytes()).hexdigest()
doc=f'''# Exactly one authorized standalone JIT-off Treatment A — October 18, 2026

## Owner authorization

{approval}

The owner message is the authority. It supersedes only the activation-only configuration's absence of live authorization. Prior consumed authorizations are not reused. No previous experiment or evidence is changed.

## Pinned configuration and unchanged runtime

Parent activation commit: 4d98b8f09b89e9d44aad39d41409cfcec67740ee. New authorization configuration: configurations/{path.name}; SHA256 {digest}. Runtime version remains runtime-clickhouse-expression-jit-off-v1. Complete experimental contract remains 6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4; transport aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c. All runtime, prompt/tool/schema/scope, scorer, task/reference/data generator, SQL guards, client, capture and qualification runner bytes are identical to the reviewed activation. Only the new authorization JSON, this record and current status are added/updated.

Model hermes-local:qwen3.5-9b; digest 0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c; loopback Ollama; temperature0, num_predict512, num_ctx65536, model timeout120s, keep_alive30m. Existing SB-D01 development task/REF-D01, seed42 dataset500 rows/13columns, query_clickhouse and retrieve_policy only;6 model steps/2 evidence calls/0 retries/0 reprompts. ClickHouse compile_expressions0, readonly1, execution10s, HTTP15s, result1000/break, read10000rows/10485760bytes, memory134217728bytes, threads2. No global settings or warm-up inference.

## Final preflight and evidence

Before launch verify clean exact source commit/configuration hash, complete contract, model/tool/prompt/capture pins, historical seals and archive hashes. Run focused and full offline regressions with network/DNS denied, including existing scripted delivery/capture checks. Final local read-only preflight checks model/digest,13-column schema,500-row count, effective fixed request settings, and all500 rows against the existing seed42 CSV using declared column types including Float32. Dataset attestation uses no analytical aggregate, task answer or model inference; it is setup integrity only. No table is changed. Preserve hashes and type-normalization algorithm, not task answer hints. These setup reads are separate from the existing2 benchmark evidence calls; the runner's unchanged fresh model/schema/count preflight also runs before worker entry.

The final immutable execution commit and exact absolute invocation are recorded in the external pre-launch authorization execution record after this commit is created, avoiding a self-referential commit hash. That record binds this SHA256, exact source and contract hashes, one fixed evidence directory and exclusive one-launch marker. No invocation is permitted before all checks pass. No output directory or marker may be removed or reused.

## Frozen acceptance and stop

Use existing qualify_phase2_once.py and run_trial, unchanged. The frozen result must have task_success true; final collector_status complete, no collection errors, valid source/config/contract postflight and exactly1worker entry are required. Preserve final normalized response, observations, deterministic score/reasons, SQL/model/tool events, resource/timing evidence and all failures. Missing response/score is not zero. Do not repair/normalize a response, rewrite SQL, rescore historical attempts or repeat an observed failure.

Report separately whether this attempt's evidence query returned without a timeout, whether the unchanged Phase2 gate qualifies, and what remains unresolved. A different generated query or this single successful attempt cannot prove the original failed SQL universally fixed or isolate JIT causation. Phase3 evaluator validity, Phase4 freeze, schema parity/comparisons and held-out evaluation remain separate unaccepted gates. Reconcile existing GitHub, canonical Notion and Asana records, then stop. No new experiment or merge.
'''
(r/'docs/jit-off-v1-one-attempt-authorization-2026-10-18.md').write_text(doc)
p=r/'STATUS.md';p.write_text('# Owner-authorized single JIT-off attempt — final preflight pending\n\nOctober18 owner approval permits exactly one new bounded standalone TreatmentA after final preflight, using unchanged runtime-clickhouse-expression-jit-off-v1. New separate authorization configuration binds one attempt; prior activation-only configuration and all failed evidence are preserved. No live attempt has started. Stop on its observed outcome; no retry, correction, other experiment or merge. See docs/jit-off-v1-one-attempt-authorization-2026-10-18.md.\n\nHistorical checkpoints follow unchanged.\n\n'+p.read_text())
(o/'owner-authorization.txt').write_text(approval+'\n')
(o/'authorized-configuration.json').write_bytes(path.read_bytes())
(o/'authorization-preparation.json').write_text(json.dumps({'configuration':str(path),'configuration_sha256':digest,'parent_commit':'4d98b8f09b89e9d44aad39d41409cfcec67740ee','authorized_attempts':1,'live_attempt_started':False},indent=2)+'\n')
print(json.dumps({'config_sha256':digest,'config_path':str(path)},indent=2))
