"""Consume the one explicit authorization and invoke the pinned CLI exactly once."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess,sys,time
from phase2_existing_environment import load_existing_clickhouse_environment
import jit_one_attempt_preflight as p
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert not p.OUT.exists(),'Prior evidence directory exists; no reuse/retry/overwrite'
assert not (p.o/'launch.json').exists(),'Authorization already consumed; do not launch again'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.r,text=True).strip()==p.PIN
assert not subprocess.check_output(['git','status','--porcelain'],cwd=p.r,text=True).strip()
assert sha(p.CONFIG)==p.SHA
record=json.loads((p.o/'authorization-execution-record.json').read_text())
assert record['execution_commit']==p.PIN and record['configuration_sha256']==p.SHA
assert record['command']==p.command() and record['attempt_ceiling']==1 and record['retries']==0
assert json.loads((p.o/'final-source-preflight.json').read_text())['execution_blockers']==[]
review=json.loads((p.o/'independent-authorization-review.json').read_text())
assert review['reviewed_commit']==p.PIN and review['configuration_sha256']==p.SHA and review['must_fix']==[]
setup=json.loads((p.o/'final-service-preflight.json').read_text())
assert setup['final_preflight_passed'] is True and setup['data_attestation']['all_rows_equal'] is True
assert setup['effective_settings']['compile_expressions'] in ('false','0')
assert setup['dataset_csv_sha256']==sha(p.CSV)==p.EXPECTED_CSV_SHA256
params=record['execution_parameters'];assert params['authorized_live_attempts']==1 and params['live_treatment_a_authorization']=='approved'
env=load_existing_clickhouse_environment()
start=time.monotonic()
launch={'classification':'exactly_one_owner_authorized_standalone_Treatment_A',
 'authorization_consumed_for_this_one_CLI_invocation':True,'start_utc':datetime.now(timezone.utc).isoformat(),
 'command':record['command'],'execution_commit':p.PIN,'configuration_sha256':p.SHA,
 'contract_sha256':record['experimental_contract_sha256'],'environment':env,
 'outer_launcher_sha256':sha(Path(__file__)),'setup_verifier_sha256':sha(Path(p.__file__)),
 'environment_loader_sha256':sha(p.b/'work/phase2_existing_environment.py'),
 'final_service_preflight_sha256':sha(p.o/'final-service-preflight.json'),
 'authorization_execution_record_sha256':sha(p.o/'authorization-execution-record.json'),
 'retries':0,'reprompts':0,'replacement_runs':0,'paid_provider_calls':0,
 'incremental_benchmark_paid_spend_usd':0,'human_hands_on_minutes':None,
 'measurement_boundary':'Local Ollama only; human time and per-request CPU/GPU/energy/peak-model-memory not measured. Existing capture records returned usage and shared host/service snapshots.'}
# Exclusive durable consumption precedes the only child invocation. Never remove it.
with (p.o/'launch.json').open('x') as stream:
    stream.write(json.dumps(launch,indent=2)+'\n');stream.flush()
    import os
    os.fsync(stream.fileno())
try:
    with (p.o/'run-stdout.txt').open('x') as stdout,(p.o/'run-stderr.txt').open('x') as stderr:
        result=subprocess.run(record['command'],cwd=p.r,stdout=stdout,stderr=stderr)
    launch['exit_code']=result.returncode
finally:
    launch.update(end_utc=datetime.now(timezone.utc).isoformat(),outer_wall_seconds=time.monotonic()-start)
    with (p.o/'outer-result.json').open('x') as stream:stream.write(json.dumps(launch,indent=2)+'\n')
print(json.dumps({k:launch[k] for k in ['start_utc','end_utc','outer_wall_seconds','exit_code','retries','replacement_runs']}))
