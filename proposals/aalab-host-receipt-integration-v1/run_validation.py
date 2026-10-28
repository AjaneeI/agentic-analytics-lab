"""Verified-source H1 entrypoint. Use only the external29/30s64KiB supervisor."""
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import platform
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
APPROVAL='ecb630a9d9fb5647150e23c539865c485a25b29e3b2c20dd25b15ccd8cbeddd0'

def sha(b):return hashlib.sha256(b).hexdigest()

class VerifiedSource(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    def __init__(self,retained):self.retained=retained
    def find_spec(self,fullname,path=None,target=None):
        if fullname in self.retained:
            filename,raw,package=self.retained[fullname]
            return importlib.util.spec_from_loader(fullname,self,is_package=package)
        if fullname=='src' or fullname.startswith('src.'):raise ImportError('unpinned H1 source import: '+fullname)
    def create_module(self,spec):return None
    def exec_module(self,module):
        filename,raw,package=self.retained[module.__name__];module.__file__=str(filename)
        if package:module.__path__=[str(filename.parent)]
        exec(compile(raw,str(filename),'exec'),module.__dict__)

def bootstrap():
    raw=(HERE/'synthetic-config.json').read_bytes();config=json.loads(raw)
    if config['version']!='aalab-host-receipt-integration-v1' or config['approved_package_sha256']!=APPROVAL or config['inactive'] is not True:raise ValueError('inactive approved configuration required')
    if any(n=='src' or n.startswith('src.') or n in ('bridge','capture_core','test_bridge') for n in sys.modules):raise ValueError('ambient candidate/runtime cache refused')
    retained={}
    for relative,expected in config['source_sha256'].items():
        path=ROOT/relative;b=path.read_bytes()
        if sha(b)!=expected:raise ValueError('source pin mismatch: '+relative)
        if path.suffix=='.py':
            if relative.startswith('src/'):
                name=relative[:-3].replace('/','.');package=name.endswith('.__init__')
                if package:name=name[:-9]
            else:name=path.stem;package=False
            retained[name]=(path,b,package)
    if not {'bridge','capture_core','test_bridge','src.evals.system_benchmark.local_worker','src.evals.system_benchmark.runner','src.evals.system_benchmark.scoring'}.issubset(retained):raise ValueError('incomplete pinned import closure')
    sys.meta_path.insert(0,VerifiedSource(retained))
    import bridge
    bridge.CONFIG=config;bridge.CONFIG_SHA=sha(raw)
    bridge.SCORER_SHA=config['source_sha256']['src/evals/system_benchmark/scoring.py']
    return bridge,config,raw

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--review',type=Path)
    a=p.parse_args()
    if a.output.exists() or a.output.resolve().is_relative_to(ROOT) or a.evidence.resolve().is_relative_to(ROOT):p.error('new evidence outside checkout required')
    # A trusted enclosing supervisor installs effect/PRNG guards before this file
    # or candidate imports and provides deterministic private tempfile names.
    if not getattr(sys,'_h1_guard_installed',False):p.error('H1 bounded guarded supervisor required')
    bridge,config,raw=bootstrap()
    import test_bridge
    test_bridge.EVIDENCE=a.evidence
    if a.review:
        review_raw=a.review.read_bytes();spec=importlib.util.spec_from_loader('_h1_independent',loader=None)
        module=importlib.util.module_from_spec(spec);module.__file__=str(a.review)
        exec(compile(review_raw,str(a.review),'exec'),module.__dict__)
        module.EVIDENCE=a.evidence
        suite=unittest.defaultTestLoader.loadTestsFromModule(module);count=suite.countTestCases()
        if not 1<=count<=8:raise ValueError('independent slot bound')
        review_sha=sha(review_raw)
    else:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(test_bridge.H1Controls);count=suite.countTestCases()
        if count!=16:raise ValueError('authored inventory must remain exactly16')
        review_sha=None
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    artifacts=sum(x.stat().st_size for x in a.evidence.rglob('*') if x.is_file())
    per_control={d.name:sum(x.stat().st_size for x in d.rglob('*') if x.is_file()) for d in a.evidence.iterdir() if d.is_dir()}
    blocked=getattr(sys,'_h1_blocked',[])
    passed=result.wasSuccessful() and not blocked and all(x<=1048576 for x in per_control.values())
    report={'version':config['version'],'python':platform.python_version(),'source_commit':config['source_commit'],
        'configuration_sha256':sha(raw),'contract_sha256':config['source_sha256'][str(HERE.relative_to(ROOT)/'contract.json')],
        'source_sha256':config['source_sha256'],'preflight_before_candidate_import':True,'execution_source':'retained_verified_source_bytes',
        'mode':'independent' if a.review else 'author','review_source_sha256':review_sha,
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'blocked_effects':blocked,
        'artifact_bytes':artifacts,'per_control_bytes':per_control,'passed':passed,**bridge.FLAGS}
    with a.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:report[k] for k in ('mode','tests','failures','errors','passed','live_qualified')}))
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
