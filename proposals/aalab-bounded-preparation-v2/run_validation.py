"""Inactive synthetic integration only; refuses existing/in-checkout evidence paths."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
from types import ModuleType
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LOADER_SHA256="76a6674a38350a4442448f994e52d8d052839db871aef3c8259911d9a2eee62c"

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--configuration',type=Path,default=HERE/'synthetic-config.json')
    args=p.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(ROOT.resolve()):
        p.error('refusing existing or in-checkout evidence output')
    observations={'memory_sqlite_connect_events':0,'blocked_side_effect_attempts':[]}
    def guard(event,arguments):
        deny=event.startswith('socket.') or event in {
            'http.client.connect','subprocess.Popen','os.system','os.posix_spawn','os.fork','os.exec'}
        if event=='sqlite3.connect':
            if arguments[0]==':memory:':observations['memory_sqlite_connect_events']+=1
            else:deny=True
        if event=='open' and isinstance(arguments[0],(str,bytes)):
            name=arguments[0].decode() if isinstance(arguments[0],bytes) else arguments[0]
            path=Path(name).absolute()
            if path.is_relative_to(ROOT):
                parts=path.relative_to(ROOT).parts
                deny |= any('heldout' in part.lower() or 'held-out' in part.lower()
                            or part in ('private','secrets','.env') for part in parts)
                # Validation may read pinned inputs but must never edit the checkout.
                mode=arguments[1]
                if isinstance(mode,str) and any(c in mode for c in 'wax+'):deny=True
        if deny:
            observations['blocked_side_effect_attempts'].append(event)
            raise RuntimeError('offline integration denied '+event)
    sys.addaudithook(guard)
    # Bootstrap path is externally trusted/pinned by exact source commit. It
    # compiles retained loader bytes, never a cached import or .pyc.
    loader_path=HERE/'offline_loader.py'
    source=loader_path.read_bytes()
    if sha(source)!=LOADER_SHA256:p.error('bootstrap loader fingerprint mismatch')
    loader=ModuleType('offline_loader');loader.__file__=str(loader_path);loader.__package__=''
    sys.modules[loader.__name__]=loader
    exec(compile(source,str(loader_path),'exec'),loader.__dict__)
    try:config,retained=loader.preflight(args.configuration)
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as error:
        p.error('offline preflight refused: '+str(error))
    modules=loader.load_candidate(retained)
    capture_tests=modules['test_capture_integration']
    capture_tests.CONFIG={'version':config['version'],'task_id':'SB-D01',
        'source_commit':config['source_commit'],'metric':'phase3-d01-tie-order-v1',
        'configuration_sha256':sha(args.configuration.read_bytes()),
        'approved_package_sha256':config['approved_package_sha256']}
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(modules[name])
        for name in ('test_capture_integration','test_semantic_guards','test_endpoint_contract','test_preflight'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    semantics=[]
    for case in modules['test_semantic_guards'].synthetic_cases():
        verdict=modules['semantic_guards'].assess(case['claim'],context=case['context'])
        semantics.append({'id':case['name'],'expected':case['expected_status'],
            'observed':verdict,'reason_matches':verdict['reason']==case['expected_reason']})
    endpoint_tests=modules['test_endpoint_contract'];expected,observed=endpoint_tests.synthetic_metadata()
    endpoint=[]
    for name,ex,obs,want in [('complete',expected,observed,True),
                           ('missing',expected,observed[:-1],False),
                           ('duplicate',expected,observed+[observed[0]],False)]:
        verdict=modules['endpoint_contract'].evaluate_metadata(ex,obs)
        endpoint.append({'id':'SYN-V2-metadata-'+name,'expected_eligible':want,'observed':verdict})
    capture_matrix=[]
    v=modules['integrated_capture']
    for name,sql,want in [('genuine',capture_tests.SQL,'proven'),
                          ('literal',capture_tests.SQL.replace('100.0*SUM(blocked)/COUNT(*)','75.0'),'contradicted'),
                          ('unknown',capture_tests.SQL+' -- newly authored comment','insufficient')]:
        with v.SyntheticCaptureSession(capture_tests.snapshot(),capture_tests.CONFIG) as host:
            rows=host.query(sql);token=host.calls[0]
            verdict=host.verify(capture_tests.claim(token),call=token)
            record=host.resolve(token.execution_id)
            capture_matrix.append({'id':'SYN-V2-capture-'+name,'expected':want,'observed':verdict,
                'query':record.query,'result_rows':rows,'snapshot_sha256':sha(record.snapshot_json.encode()),
                'config_sha256':sha(record.config_json.encode()),'call_id':record.call_id,
                'contract_sha256':record.contract_sha256,'execution_id':record.execution_id})
    passed=(result.wasSuccessful()
        and all(c['expected']==c['observed']['status'] and c['reason_matches']
                and c['observed']['live_qualified'] is False for c in semantics)
        and all(c['expected_eligible']==c['observed']['eligible_for_primary'] for c in endpoint)
        and all(c['expected']==c['observed']['status'] and c['observed']['live_qualified'] is False for c in capture_matrix)
        and not observations['blocked_side_effect_attempts'])
    report={'version':config['version'],'python':platform.python_version(),'source_commit':config['source_commit'],
        'configuration_sha256':sha(args.configuration.read_bytes()),'contract_sha256':sha(retained[str((HERE/'contract.json').resolve())]),
        'source_sha256':config['source_sha256'],'dependency_sha256':config['dependency_sha256'],
        'preflight_before_candidate_import':True,'execution_source':'retained_verified_source_bytes',
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'semantic_controls':semantics,'endpoint_controls':endpoint,'capture_controls':capture_matrix,
        'side_effect_guard':observations,'candidate_active':False,'live_qualified':False,
        'phase3_accepted':False,'phase4_frozen':False,'phase5_entered':False,
        'new_treatment_a_attempts':0,'new_stochastic_draws':0,'passed':passed}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:report[k] for k in ('version','python','tests','failures','errors','passed','live_qualified')}))
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
