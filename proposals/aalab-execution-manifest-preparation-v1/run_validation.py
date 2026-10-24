"""Pinned offline entrypoint. Invoke through the approved 30s/64KiB watchdog."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
from types import ModuleType
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NAMES={'manifest.py','test_manifest.py','run_validation.py','README.md','contract.json'}
C1_SHA256='17d79f9d986114a39edf921ada2b467ac8e356691873d52af1e8cd41258e6b37'

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--configuration',type=Path,default=HERE/'synthetic-config.json')
    args=p.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(ROOT.resolve()):p.error('new external output required')
    def guard(event,a):
        deny=event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.fork','os.exec','sqlite3.connect','sqlite3.connect/handle'}
        if event=='import':deny |= any(a[0]==x or a[0].startswith(x+'.') for x in ('random','numpy','sqlite3','socket','subprocess','openai','ollama','src.agents','src.tools'))
        if event=='open' and isinstance(a[0],(str,bytes)):
            path=Path(os.fsdecode(a[0])).absolute()
            deny |= any('heldout' in x.lower() or 'held-out' in x.lower() or x in ('private','secrets','.env') for x in path.parts)
            if path.is_relative_to(ROOT) and isinstance(a[1],str):deny |= any(c in a[1] for c in 'wax+')
        if deny:raise RuntimeError('P1 offline operation denied '+event)
    sys.addaudithook(guard)
    try:
        with args.configuration.open('rb') as f:config_bytes=f.read(65537)
        if len(config_bytes)>65536:raise ValueError('configuration cap')
        config=json.loads(config_bytes)
        if (config['version']!='aalab-execution-manifest-preparation-v1'
            or config['active'] is not False or config['live_qualified'] is not False
            or config['scientific_ready'] is not False or type(config['new_attempts']) is not int
            or config['new_attempts']!=0 or config['c1_source_sha256']!=C1_SHA256
            or re.fullmatch('[0-9a-f]{40}',config['source_commit']) is None
            or set(config['source_sha256'])!=NAMES):raise ValueError('inactive configuration mismatch')
        retained={}
        for name in sorted(NAMES):
            path=HERE/name
            if path.absolute()!=path.resolve():raise ValueError('source link')
            data=path.read_bytes()
            if sha(data)!=config['source_sha256'][name]:raise ValueError('source fingerprint: '+name)
            retained[name]=data
        contract=json.loads(retained['contract.json'])
    except (ValueError,TypeError,KeyError,OSError,RecursionError) as error:p.error('preflight refused: '+str(error))
    def load(name,file):
        m=ModuleType(name);m.__file__=str(HERE/file);m.__package__='';sys.modules[name]=m
        exec(compile(retained[file],m.__file__,'exec'),m.__dict__);return m
    validator=load('p1_manifest','manifest.py')
    if validator.CONTRACT!=contract:p.error('contract/source disagreement')
    tests=load('p1_manifest_tests','test_manifest.py')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    passed=result.wasSuccessful() and len(tests.OBSERVED)==16
    report={'version':config['version'],'active':False,'live_qualified':False,
      'independence_established':False,'scientific_ready':False,'new_attempts':0,
      'python':platform.python_version(),'source_commit':config['source_commit'],
      'configuration_sha256':sha(config_bytes),'contract_sha256':sha(retained['contract.json']),
      'source_sha256':config['source_sha256'],'preflight_before_candidate_import':True,
      'execution_source':'retained_verified_bytes','named_cases':tests.OBSERVED,
      'passed':passed,'new_SQL_executions':0,'new_model_calls':0,'new_stochastic_draws':0,
      'invocation_bounds':{'seconds':30,'combined_output_bytes':65536,'enforcement':'external approved watchdog required; no standalone wall-time guarantee'}}
    payload=(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(payload)>65536:p.error('receipt cap')
    descriptor=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as f:f.write(payload)
    print(json.dumps({'passed':passed,'named_cases':len(tests.OBSERVED),'live_qualified':False}))
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
