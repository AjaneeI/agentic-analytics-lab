#!/usr/bin/env python3
"""Fixed, model-free diagnostic protocol. No benchmark worker or scorer imports."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request
from unittest.mock import patch

VERSION = 'jit-off-model-free-validation-v1'
PROPOSAL_PIN = '7f010f242c9b8bfe10f83f0bfd19650ea8867305'
CANDIDATE_PIN = '2252aed9803d9276934951676b76b889857c411f'
BASE_SHA = '3f4667601120d0a660274a66da5608da4de2461ff4a5b86385a731d3daa5f1c1'
CANDIDATE_SHA = 'aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c'
PARAMETERS = {'default_format':'JSONEachRow','readonly':'1','max_execution_time':'10',
    'max_result_rows':'1000','result_overflow_mode':'break','max_rows_to_read':'10000',
    'max_bytes_to_read':'10485760','max_memory_usage':'134217728','max_threads':'2'}
SETTINGS_SQL = "SELECT version() AS server_version, " + ', '.join(
    f"toString(getSetting('{key}')) AS {key}" for key in [
        'compile_expressions','readonly','max_execution_time','max_result_rows',
        'result_overflow_mode','max_rows_to_read','max_bytes_to_read','max_memory_usage','max_threads'])
ROWS = "WITH validation_rows AS (SELECT toFloat64(-2.5) AS x UNION ALL SELECT toFloat64(0) AS x UNION ALL SELECT toFloat64(1.25) AS x UNION ALL SELECT toFloat64(7.75) AS x) "
SCALAR_SQL = ROWS + "SELECT x, x * 2.0 + 0.5 AS affine, (x + 3.0) / 7.0 AS seventh FROM validation_rows ORDER BY x"
AGGREGATE_SQL = ROWS + "SELECT sum(x) AS sum_x, min(x) AS min_x, max(x) AS max_x FROM validation_rows"
EXPECTED_SCALAR = [{'x':-2.5,'affine':-4.5,'seventh':1/14},
    {'x':0.0,'affine':0.5,'seventh':3/7}, {'x':1.25,'affine':3.0,'seventh':17/28},
    {'x':7.75,'affine':16.0,'seventh':43/28}]
EXPECTED_AGGREGATE = [{'sum_x':6.5,'min_x':-2.5,'max_x':7.75}]
PLAN = [
    {'id':'candidate-settings','lane':'candidate','kind':'settings','sql':SETTINGS_SQL},
    {'id':'baseline-settings','lane':'baseline','kind':'settings','sql':SETTINGS_SQL},
    {'id':'baseline-scalar','lane':'baseline','kind':'scalar','sql':SCALAR_SQL},
    {'id':'candidate-scalar','lane':'candidate','kind':'scalar','sql':SCALAR_SQL},
    {'id':'baseline-aggregate','lane':'baseline','kind':'aggregate','sql':AGGREGATE_SQL},
    {'id':'candidate-aggregate','lane':'candidate','kind':'aggregate','sql':AGGREGATE_SQL},
]

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise AssertionError(message)

def protocol():
    return {'version':VERSION,'authorization':'Owner approved bounded model-free PR111 validation using unrelated synthetic SQL; no failed SQL replay, Treatment A or merge.',
        'proposal_commit':PROPOSAL_PIN,'candidate_commit':CANDIDATE_PIN,
        'baseline_transport_sha256':BASE_SHA,'candidate_transport_sha256':CANDIDATE_SHA,
        'maximum_SQL_requests':6,'total_start_new_request_budget_seconds':120,
        'client_timeout_seconds':15,'request_parameters':PARAMETERS,
        'candidate_only_parameter':{'compile_expressions':'0'},'plan':PLAN,
        'expected_scalar_rows':EXPECTED_SCALAR,'expected_aggregate_rows':EXPECTED_AGGREGATE,
        'numeric_tolerance':{'relative':1e-12,'absolute':1e-12,'finite_only':True},
        'stop_rule':'Stop at first request error, settings/numeric mismatch or budget violation; zero retries, no replacement queries.',
        'no_application_tables_or_table_functions':True,'model_calls':0,'benchmark_worker_entries':0,
        'qualification_or_comparative_acceptance':False,
        'limits':'Checks validate delivery, effective settings and these synthetic values only. No proof of original timeout causation, all-query equivalence, JIT-on execution, cold/warm independence or speedup.'}

def check_rows(actual, expected):
    require(len(actual)==len(expected),'row count differs')
    for got,want in zip(actual,expected):
        require(set(got)==set(want),'column keys differ')
        for key,value in want.items():
            number=got[key]
            require(type(number) in (int,float) and math.isfinite(number),'nonfinite or nonnumeric result')
            require(math.isclose(number,value,rel_tol=1e-12,abs_tol=1e-12),f'numeric mismatch in {key}')

def check_settings(rows, lane):
    require(len(rows)==1,'settings row count differs')
    row=rows[0]
    require(isinstance(row.get('server_version'),str) and bool(row['server_version']),'missing server version')
    for key,value in PARAMETERS.items():
        if key=='default_format': continue
        require(str(row.get(key))==value,f'effective setting differs: {key}')
    mode=str(row.get('compile_expressions'))
    require(mode in ('0','1'),'unknown effective compilation mode')
    if lane=='candidate': require(mode=='0','candidate JIT setting is not disabled')


def execute(out, modules, *, expected_script_commit, transport=None):
    """Reserve one evidence directory and process the immutable plan once."""
    out=Path(out);out.mkdir(parents=False,exist_ok=False)
    def save(name,value):
        with (out/name).open('x') as f: f.write(json.dumps(value,indent=2)+'\n')
    save('protocol.json',protocol())
    save('STARTED.json',{'utc':utc(),'script_commit':expected_script_commit,'script_sha256':sha(Path(__file__).read_bytes()),'retries':0})
    started=time.monotonic();results=[];attempts=0;wire=[]
    real_open=transport if transport is not None else urllib.request.urlopen
    def event(event_type,**fields):
        with (out/'events.jsonl').open('a') as f:
            f.write(json.dumps({'event':event_type,'utc':utc(),'elapsed_seconds':time.monotonic()-started,**fields})+'\n');f.flush()
    try:
        for case in PLAN:
            require(time.monotonic()-started<120,'total request-start budget exceeded')
            expected_params=dict(PARAMETERS)
            if case['lane']=='candidate':expected_params['compile_expressions']='0'
            def observed_open(request, *, timeout):
                nonlocal attempts
                require(attempts<6,'request ceiling exceeded')
                require(timeout==15,'client wait changed')
                parsed=urllib.parse.urlsplit(request.full_url)
                require(parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost') and parsed.port==8123,'nonlocal destination')
                require(request.get_method()=='POST','HTTP method differs')
                require(request.data==case['sql'].encode(),'unplanned SQL')
                require(urllib.parse.parse_qs(parsed.query)=={k:[v] for k,v in expected_params.items()},'wire parameters differ')
                attempts+=1
                rec={'case':case['id'],'SQL_utf8':request.data.decode(),'SQL_sha256':sha(request.data),'timeout_seconds':timeout,'parameters':expected_params}
                wire.append(rec);event('http_start',**rec)
                response=real_open(request,timeout=timeout)
                rec['http_status']=getattr(response,'status',None)
                headers=getattr(response,'headers',{})
                rec['response_headers']={key:headers.get(key) for key in ['X-ClickHouse-Query-Id','X-ClickHouse-Summary','Content-Type'] if headers.get(key) is not None}
                class ResponseCapture:
                    def __enter__(self):response.__enter__();return self
                    def __exit__(self,*args):return response.__exit__(*args)
                    def read(self,*args,**kwargs):
                        raw=response.read(*args,**kwargs);rec['body_utf8']=raw.decode('utf-8');rec['body_sha256']=sha(raw);return raw
                return ResponseCapture()
            tick=time.monotonic();event('case_start',case=case['id'],lane=case['lane'])
            with patch('urllib.request.urlopen',observed_open):
                rows=modules[case['lane']].query_clickhouse(case['sql'])
            if case['kind']=='settings':check_settings(rows,case['lane'])
            else:check_rows(rows,EXPECTED_SCALAR if case['kind']=='scalar' else EXPECTED_AGGREGATE)
            result={'case':case['id'],'lane':case['lane'],'kind':case['kind'],'rows':rows,'wall_seconds':time.monotonic()-tick,'passed':True}
            results.append(result);event('case_pass',**result)
        for kind in ['scalar','aggregate']:
            rows=[x['rows'] for x in results if x['kind']==kind];check_rows(rows[0],rows[1])
        settings=[x['rows'][0] for x in results if x['kind']=='settings']
        require(settings[0]['server_version']==settings[1]['server_version'],'server version changed across settings reads')
        status='passed_bounded_synthetic_validation'
    except BaseException as error:
        status='failed_stopped_without_retry';event('validation_error',type=type(error).__name__,message=str(error))
        save('error.json',{'type':type(error).__name__,'message':str(error),'case':case['id'] if 'case' in locals() else None})
    finally:
        save('wire-captures.json',wire)
        save('results.json',results)
        save('manifest.json',{'version':VERSION,'status':status,'start_utc':json.loads((out/'STARTED.json').read_text())['utc'],'end_utc':utc(),'wall_seconds':time.monotonic()-started,'SQL_attempts':attempts,'completed_cases':len(results),'maximum_SQL_requests':6,'retries':0,'model_calls':0,'Treatment_A_entries':0,'scorer_calls':0,'script_commit':expected_script_commit,'benchmark_activation':False})
    return status


def load_transport(root,expected_commit,expected_sha,name):
    root=Path(root)
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    require(git('rev-parse','HEAD')==expected_commit,'transport commit differs')
    require(not git('status','--porcelain'),'transport checkout is dirty')
    path=root/'src/tools/clickhouse_readonly.py';require(sha(path.read_bytes())==expected_sha,'transport hash differs')
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for case in PLAN:require(module.validate_read_only(case['sql'])==case['sql'],'guard changed diagnostic SQL')
    return module


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--baseline-root',type=Path);p.add_argument('--candidate-root',type=Path);p.add_argument('--script-commit');p.add_argument('--out',type=Path);a=p.parse_args()
    if not a.run:
        print(json.dumps(protocol(),indent=2));return 0
    require(a.baseline_root and a.candidate_root and a.script_commit and a.out,'all immutable execution pins and output required')
    root=Path(__file__).resolve().parents[1]
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==a.script_commit,'script commit differs')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip(),'script tree dirty')
    modules={'baseline':load_transport(a.baseline_root,PROPOSAL_PIN,BASE_SHA,'jit_validation_baseline'),
             'candidate':load_transport(a.candidate_root,CANDIDATE_PIN,CANDIDATE_SHA,'jit_validation_candidate')}
    result=execute(a.out,modules,expected_script_commit=a.script_commit)
    print(json.dumps({'status':result,'output':str(a.out)}));return 0 if result.startswith('passed') else 1

if __name__=='__main__':raise SystemExit(main())
