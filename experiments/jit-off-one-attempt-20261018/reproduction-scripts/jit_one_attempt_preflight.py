"""Source-only or approved read-only setup; never enters a benchmark worker."""
from pathlib import Path
import argparse,csv,hashlib,json,os,socket,struct,subprocess,sys
from unittest.mock import patch
b=Path(__file__).resolve().parent.parent;r=b/'work/phase2-jit-off-authorized';o=b/'outputs/jit-off-one-attempt-20261018'
PIN='688f62dcedb3116e8ae46579cea0fd135eba94ce'
CONFIG=r/'configurations/phase2-runtime-schema-v1-scope-observation-v1-response-format-v1-expression-jit-off-v1.one-attempt-20261018.json'
SHA='f1afa4f6d3b6238b87155729d63453dd43d7d001f6aeb45c99cd64dd9e8ca27b'
CSV=Path('/Users/ajaneeigharo/Projects/agentic-analytics-lab/data/delivery_work_items.csv')
EXPECTED_CSV_SHA256='cb3e85f970aa640624444ffc9dd13ffe7f3cbee9e97ab78050c34c35ab9d33ef'
APPROVAL='Owner explicit current-chat authorization October18 2026 America/New_York: exactly one new bounded standalone Treatment A using runtime-clickhouse-expression-jit-off-v1 after successful final preflight; record docs/jit-off-v1-one-attempt-authorization-2026-10-18.md; no retry/correction/replacement/additional experiment.'
OUT=b/'outputs/treatment-a-jit-off-v1-20261018'
FIELDS=['work_item_id','team','priority','status','created_at','due_at','completed_at','planned_hours','actual_hours','blocked','blocker_type','rework_count','customer_impact']
INTS={'planned_hours','blocked','rework_count','customer_impact'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def typed(rows):
    result=[]
    for row in rows:
        assert set(row)==set(FIELDS),'Dataset columns differ'
        normalized={}
        for key in FIELDS:
            value=row[key]
            if key in INTS:
                assert type(value) in (int,str),'Integer dataset field type differs'
                value=int(value)
            elif key=='actual_hours':
                assert type(value) in (int,float,str),'Float32 dataset field type differs'
                value=struct.unpack('!f',struct.pack('!f',float(value)))[0]
            elif key=='completed_at' and value in ('',None):value=None
            else:assert type(value) is str,'Text/time dataset field type differs'
            normalized[key]=value
        result.append(normalized)
    return sorted(result,key=lambda x:x['work_item_id'])
def data_equality(actual,expected):
    a,e=typed(actual),typed(expected)
    assert len(a)==len(e)==500,'Dataset row count differs'
    assert len({x['work_item_id'] for x in a})==500,'Dataset IDs are not unique'
    ah,eh=hashlib.sha256(canonical(a)).hexdigest(),hashlib.sha256(canonical(e)).hexdigest()
    assert ah==eh,'Dataset contents differ from existing seed42 CSV; no correction permitted'
    return {'rows_verified':500,'columns_verified':13,'actual_typed_sha256':ah,'expected_typed_sha256':eh,
            'all_rows_equal':True,'normalization':'Declared schema: integer fields parsed as int; actual_hours rounded to IEEE754 Float32 on both sides; empty CSV completed_at equals SQL NULL; other strings exact; sorted by work_item_id. No benchmark response/scorer normalization.'}
def request():
    sys.path.insert(0,str(r))
    from scripts import passive_capture as capture
    return capture.CaptureRequest(r,PIN,CONFIG,SHA)
def source():
    assert sha(CSV)==EXPECTED_CSV_SHA256,'Original seed42 CSV fingerprint differs'
    sys.path.insert(0,str(r))
    from scripts import qualify_phase2_once as runner
    result=runner.source_preflight(request())
    assert result['activation_ready'] is True and result['execution_ready'] is True
    assert result['execution_blockers']==[] and result['services_contacted'] is False
    return result
def command():return [sys.executable,'-B',str(r/'scripts/qualify_phase2_once.py'),'--root',str(r),'--expected-commit',PIN,'--config',str(CONFIG),'--config-sha256',SHA,'--out',str(OUT),'--run','--approval-reference',APPROVAL]
def record_source():
    def deny(*a,**k):raise AssertionError('Source-only preflight denies network and DNS')
    sys.path.insert(0,str(r))
    with patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny),patch('socket.create_connection',deny),patch('socket.getaddrinfo',deny):
        result=source()
    with (o/'final-source-preflight.json').open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    import shlex
    record={'authorization_record_id':'runtime-clickhouse-expression-jit-off-v1-one-attempt-20261018',
        'execution_commit':PIN,'configuration_path':str(CONFIG),'configuration_sha256':SHA,
        'experimental_contract_sha256':result['checks']['benchmark_contract']['benchmark_contract_sha256'],
        'execution_parameters':result['checks']['config'],'runner_sha256':result['adapter_sha256'],
        'passive_capture_sha256':result['capture_sha256'],'runtime_contract_files':result['checks']['benchmark_contract']['contract_files'],
        'command':command(),'exact_shell_invocation':shlex.join(command()),'evidence_directory':str(OUT),
        'attempt_ceiling':1,'retries':0,'reprompts':0,'status_at_recording':'authorized_pending_final_service_preflight_not_launched',
        'other_experiments_authorized':False,'historical_evidence_modified':False}
    with (o/'authorization-execution-record.json').open('x') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
    (o/'final-invocation.txt').write_text(shlex.join(command())+'\n')
    print(json.dumps({'source_preflight_passed':True,'execution_commit':PIN,'configuration_sha256':SHA,'services_contacted':False}))
def live_setup():
    # All source/auth/offline/review conditions must already exist before setup.
    assert not OUT.exists() and not (o/'launch.json').exists()
    review=json.loads((o/'independent-authorization-review.json').read_text())
    assert review['reviewed_commit']==PIN and review['configuration_sha256']==SHA and review['must_fix']==[]
    for name in ['full-python311.txt','full-python312.txt']:
        text=(o/name).read_text();assert 'Ran 375 tests' in text and text.rstrip().endswith('OK')
    from phase2_existing_environment import load_existing_clickhouse_environment
    env=load_existing_clickhouse_environment()
    sys.path.insert(0,str(r))
    from scripts import qualify_phase2_once as runner
    from src.tools.clickhouse_readonly import query_clickhouse
    inspected=source();cfg=inspected['checks']['config']
    report=runner.service_preflight(cfg,json_get=runner._get_json,query_fn=query_clickhouse)
    setting_keys=['compile_expressions','readonly','max_execution_time','max_result_rows','result_overflow_mode','max_rows_to_read','max_bytes_to_read','max_memory_usage','max_threads']
    settings_sql='SELECT version() AS server_version, '+', '.join("toString(getSetting('"+k+"')) AS "+k for k in setting_keys)
    settings=query_clickhouse(settings_sql);assert len(settings)==1
    values=settings[0];assert values['compile_expressions'] in ('0','false')
    assert all(values[k]==cfg['clickhouse_fixed_request_parameters'][k] for k in setting_keys if k!='compile_expressions')
    data_sql='SELECT '+', '.join(FIELDS)+' FROM agentic_analytics.delivery_work_items ORDER BY work_item_id'
    csv_before=sha(CSV)
    with CSV.open(newline='') as stream:expected=list(csv.DictReader(stream))
    data_check=data_equality(query_clickhouse(data_sql),expected)
    assert sha(CSV)==csv_before
    report.update(classification='approved_read_only_final_preflight_not_experiment',environment=env,
        effective_settings=values,effective_settings_SQL=settings_sql,data_attestation_SQL=data_sql,
        additional_setup_SQL_calls=2,preflight_SQL_calls_total=4,dataset_csv_sha256=csv_before,data_attestation=data_check,
        live_model_calls=0,benchmark_worker_entries=0,source_preflight_rechecked=True,
        client_HTTP_timeout_seconds=15,request_settings_sha256=hashlib.sha256(canonical(cfg['clickhouse_fixed_request_parameters'])).hexdigest(),
        ollama_version=runner._get_json(cfg['model']['base_url']+'/api/version'))
    report['final_preflight_passed']=True
    with (o/'final-service-preflight.json').open('x') as stream:stream.write(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'final_preflight_passed':True,'model_digest_verified':True,'schema_columns':13,'data_rows_verified':500,'effective_compile_expressions':values['compile_expressions'],'live_model_calls':0,'benchmark_worker_entries':0}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--service-preflight',action='store_true');args=p.parse_args()
    if args.service_preflight:live_setup()
    else:record_source()
