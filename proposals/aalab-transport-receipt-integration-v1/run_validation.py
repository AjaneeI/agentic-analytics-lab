"""Retained verified-source entry; requires the bounded external H2 supervisor."""
import argparse
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import platform
import sys
import unittest
import urllib.request

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
APPROVAL='2d2009984962d716186bd78a565448c8d1eea0be648b2bce9bf814349ce034f1'
def sha(raw):return hashlib.sha256(raw).hexdigest()
class VerifiedSource(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    def __init__(self,retained):self.retained=retained
    def find_spec(self,name,path=None,target=None):
        if name in self.retained:return importlib.util.spec_from_loader(name,self,is_package=self.retained[name][2])
        if name=='src' or name.startswith('src.') or name in ('capture_core','h1_bridge','h2_transport','h2_bridge','test_transport'):raise ImportError('unpinned H2 import: '+name)
        spec=importlib.machinery.PathFinder.find_spec(name,path)
        if spec is not None and spec.origin and spec.origin not in ('built-in','frozen') and Path(spec.origin).resolve().is_relative_to(ROOT):raise ImportError('ambient unpinned project import: '+name)
    def create_module(self,spec):return None
    def exec_module(self,module):
        path,raw,package=self.retained[module.__name__];module.__file__=str(path)
        if package:module.__path__=[str(path.parent)]
        exec(compile(raw,str(path),'exec'),module.__dict__)

def bootstrap():
    raw=(HERE/'synthetic-config.json').read_bytes();config=json.loads(raw)
    if config['version']!='aalab-transport-receipt-integration-v1' or config['approved_package_sha256']!=APPROVAL or config['inactive'] is not True:raise ValueError('approved inactive H2 context required')
    if platform.python_version() not in ('3.11.16','3.12.6'):raise ValueError('approved interpreter required')
    names=('capture_core','h1_bridge','h2_transport','h2_bridge','test_transport')
    if any(n=='src' or n.startswith('src.') or n in names or n in ('bridge','transport','test_bridge') for n in sys.modules):raise ValueError('ambient project source cache refused')
    retained={};h1_raw=None
    for relative,expected in config['source_sha256'].items():
        path=ROOT/relative
        if path.is_symlink():raise ValueError('source symlink refused')
        b=path.read_bytes()
        if sha(b)!=expected:raise ValueError('source pin mismatch: '+relative)
        if relative=='proposals/aalab-host-receipt-integration-v1/synthetic-config.json':h1_raw=b
        if path.suffix!='.py':continue
        if relative.startswith('src/'):
            name=relative[:-3].replace('/','.');package=name.endswith('.__init__')
            if package:name=name[:-9]
        else:
            package=False
            if relative.startswith(config['proposal_path']+'/'):
                name={'transport':'h2_transport','bridge':'h2_bridge'}.get(path.stem,path.stem)
            elif path.stem=='bridge':name='h1_bridge'
            elif path.stem=='capture_core':name='capture_core'
            else:continue
        retained[name]=(path,b,package)
    required=set(names)|{'src.agents.ollama_client','src.tools.clickhouse_readonly','src.evals.system_benchmark.local_worker','src.evals.system_benchmark.runner','src.evals.system_benchmark.scoring'}
    if not required.issubset(retained) or h1_raw is None:raise ValueError('incomplete H2 pinned closure')
    sys.meta_path.insert(0,VerifiedSource(retained))
    import h2_transport
    boundary=h2_transport.ClosedTransport()
    urllib.request.urlopen=boundary.open
    sys._h2_client_admitted=boundary.admitted
    import h1_bridge
    h1_bridge.CONFIG=json.loads(h1_raw);h1_bridge.CONFIG_SHA=sha(h1_raw)
    h1_bridge.SCORER_SHA=config['source_sha256']['src/evals/system_benchmark/scoring.py']
    import h2_bridge
    h2_bridge.CONFIG=config;h2_bridge.CONFIG_SHA=sha(raw);h2_bridge.TRANSPORT=boundary
    return h2_bridge,config,raw

class CaseResult(unittest.TextTestResult):
    def startTest(self,test):sys._h2_trial_entries=0;super().startTest(test)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--review',type=Path)
    a=p.parse_args()
    if not getattr(sys,'_h2_guard_installed',False):p.error('H2 guarded external supervisor required')
    if a.output.exists() or a.output.resolve().is_relative_to(ROOT) or a.evidence.resolve().is_relative_to(ROOT):p.error('new evidence outside checkout required')
    bridge,config,raw=bootstrap()
    import test_transport
    test_transport.EVIDENCE=a.evidence
    if a.review:
        review_raw=a.review.read_bytes();module=importlib.util.module_from_spec(importlib.util.spec_from_loader('_h2_independent',loader=None));module.__file__=str(a.review)
        exec(compile(review_raw,str(a.review),'exec'),module.__dict__);module.EVIDENCE=a.evidence
        suite=unittest.defaultTestLoader.loadTestsFromModule(module);count=suite.countTestCases()
        if not 1<=count<=4:raise ValueError('H2 independent slot bound')
        review_sha=sha(review_raw)
    else:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(test_transport.H2Controls);count=suite.countTestCases()
        if count!=12:raise ValueError('H2 authored inventory must be exactly12')
        review_sha=None
    result=unittest.TextTestRunner(verbosity=2,resultclass=CaseResult).run(suite)
    per_control={d.name:sum(f.stat().st_size for f in d.rglob('*') if f.is_file()) for d in a.evidence.iterdir() if d.is_dir()}
    blocked=getattr(sys,'_h2_blocked',[])
    passed=result.wasSuccessful() and not blocked and all(n<=524288 for n in per_control.values())
    report={'version':config['version'],'python':platform.python_version(),'source_commit':config['source_commit'],
      'configuration_sha256':sha(raw),'contract_sha256':config['source_sha256'][config['proposal_path']+'/contract.json'],
      'source_sha256':config['source_sha256'],'execution_source':'retained_verified_source_bytes',
      'preflight_before_project_import':True,'literal_synthetic_environment':True,
      'mode':'independent' if a.review else 'author','review_source_sha256':review_sha,
      'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
      'blocked_effects':blocked,'per_control_bytes':per_control,'passed':passed,**bridge.FLAGS}
    with a.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:report[k] for k in ('mode','tests','failures','errors','passed','live_qualified')}))
    raise SystemExit(0 if passed else 1)
if __name__=='__main__':main()
