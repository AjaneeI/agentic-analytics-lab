"""A3 retained-byte loader; external guarded watchdog required, no live CLI."""
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
APPROVAL='77292dc801e837544ffd7cb22a13f17039b2c4ad1b053a17abe79ee074276197'
C01='d166cb652b1e0f8d4e1e4abd4ea9e30595f287cd9e4ea27438cfb7ccaa261d97'
SOURCE='688f62dcedb3116e8ae46579cea0fd135eba94ce'
CORE='2036fe9efaf0b5c064d0def05655f52721edc2230b3b19a6ec4736c49d77539e'
def sha(raw):return hashlib.sha256(raw).hexdigest()
class VerifiedSource(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    def __init__(self,retained):self.retained=retained
    def find_spec(self,name,path=None,target=None):
        if name in self.retained:return importlib.util.spec_from_loader(name,self,is_package=self.retained[name][2])
        if name=='src' or name.startswith('src.') or name in ('capture_core','a3_observer','a3_adapter','test_acquisition'):raise ImportError('A3 unlisted source: '+name)
        spec=importlib.machinery.PathFinder.find_spec(name,path)
        if spec and spec.origin and spec.origin not in ('built-in','frozen') and Path(spec.origin).resolve().is_relative_to(ROOT):raise ImportError('A3 ambient project import: '+name)
    def create_module(self,spec):return None
    def exec_module(self,module):
        path,raw,package=self.retained[module.__name__];module.__file__=str(path)
        if package:module.__path__=[str(path.parent)]
        exec(compile(raw,str(path),'exec'),module.__dict__)

def bootstrap():
    if not getattr(sys,'_a3_guard_installed',False):raise RuntimeError('A3 external guarded supervisor required')
    raw=(HERE/'synthetic-config.json').read_bytes();config=json.loads(raw)
    if config['version']!='aalab-standalone-acquisition-preparation-v1' or config['approved_package_sha256']!=APPROVAL or config['C01_package_sha256']!=C01 or config['source_commit']!=SOURCE:raise ValueError('A3 exact approved configuration required')
    if config['real_dispatch_allowed'] is not False or config['authorized_live_transactions']!=0:raise ValueError('A3 inactive configuration required')
    if platform.python_version() not in ('3.11.16','3.12.6'):raise ValueError('A3 approved interpreter required')
    names=('capture_core','a3_adapter','a3_observer','test_acquisition')
    if any(n=='src' or n.startswith('src.') or n in names for n in sys.modules):raise ValueError('A3 ambient source cache refused')
    source_root=sys._a3_source_root;manifest_path=sys._a3_source_manifest
    manifest_raw=manifest_path.read_bytes()
    if sha(manifest_raw)!=config['retained_manifest_sha256']:raise ValueError('A3 retained manifest mismatch')
    manifest=json.loads(manifest_raw)
    def verify_sources(pins=None):
        pins=config['external_sources'] if pins is None else pins
        if set(pins)!=set(manifest['paths']) or len(pins)!=25:raise ValueError('A3 source closure mismatch')
        retained={};total=0
        for relative,pin in pins.items():
            path=source_root/relative
            if path.is_symlink() or not path.resolve().is_relative_to(source_root.resolve()):raise ValueError('A3 source path refused')
            b=path.read_bytes();total+=len(b)
            if len(b)!=pin['bytes'] or sha(b)!=pin['sha256'] or pin!=manifest['paths'][relative]:raise ValueError('A3 source pin mismatch: '+relative)
            name=relative[:-3].replace('/','.');package=name.endswith('.__init__')
            if package:name=name[:-9]
            retained[name]=(path,b,package)
        if total!=142504 or total>524288:raise ValueError('A3 closure byte mismatch')
        return retained
    retained=verify_sources()
    for relative,pin in config['implementation_sha256'].items():
        path=ROOT/relative
        if path.is_symlink():raise ValueError('A3 implementation symlink refused')
        b=path.read_bytes()
        if sha(b)!=pin:raise ValueError('A3 implementation pin mismatch: '+relative)
        if path.name=='contract.json' and sha(b)!=config['contract_sha256']:raise ValueError('A3 contract mismatch')
        if path.suffix=='.py' and path.name!='run_validation.py':
            name={'observer':'a3_observer','adapter':'a3_adapter'}.get(path.stem,path.stem)
            retained[name]=(path,b,False)
    core_path=ROOT/'proposals/aalab-host-receipt-integration-v1/capture_core.py';core_raw=core_path.read_bytes()
    if sha(core_raw)!=CORE:raise ValueError('A3 H1 core mismatch')
    retained['capture_core']=(core_path,core_raw,False)
    sys.meta_path.insert(0,VerifiedSource(retained))
    import a3_observer
    boundary=a3_observer.ClosedBoundary();urllib.request.urlopen=boundary.open;sys._a3_client_admitted=boundary.admitted
    import a3_adapter
    a3_adapter.CONFIG=config;a3_adapter.CONFIG_SHA=sha(raw);a3_adapter.BOUNDARY=boundary;a3_adapter.CHECK_SOURCES=verify_sources
    import test_acquisition
    a3_adapter.ALLOWED_DELEGATES=(test_acquisition.MemoryDelegate,)
    return a3_adapter,config,raw

class CaseResult(unittest.TextTestResult):
    def startTest(self,test):sys._a3_trial_entries=0;super().startTest(test)
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--review',type=Path)
    a=p.parse_args()
    if a.output.exists() or a.output.resolve().is_relative_to(ROOT) or a.evidence.resolve().is_relative_to(ROOT):p.error('A3 new private evidence outside checkout required')
    adapter,config,raw=bootstrap()
    import test_acquisition
    test_acquisition.EVIDENCE=a.evidence
    review_sha=None
    if a.review:
        review_raw=a.review.read_bytes();module=importlib.util.module_from_spec(importlib.util.spec_from_loader('_a3_independent',loader=None));module.__file__=str(a.review)
        exec(compile(review_raw,str(a.review),'exec'),module.__dict__);module.EVIDENCE=a.evidence
        suite=unittest.defaultTestLoader.loadTestsFromModule(module);count=suite.countTestCases();review_sha=sha(review_raw)
        if not 1<=count<=4:raise ValueError('A3 independent slot bound')
    else:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(test_acquisition.A3Controls)
        if suite.countTestCases()!=12:raise ValueError('A3 exact12 authored slots required')
    result=unittest.TextTestRunner(verbosity=2,resultclass=CaseResult).run(suite)
    sizes={d.name:sum(f.stat().st_size for f in d.rglob('*') if f.is_file()) for d in a.evidence.iterdir() if d.is_dir()}
    blocked=getattr(sys,'_a3_blocked',[])
    passed=result.wasSuccessful() and not blocked and all(n<=1048576 for n in sizes.values())
    report={'version':config['version'],'python':platform.python_version(),'source_commit':SOURCE,
      'configuration_sha256':sha(raw),'contract_sha256':config['contract_sha256'],
      'retained_manifest_sha256':config['retained_manifest_sha256'],'implementation_sha256':config['implementation_sha256'],
      'source_execution':'retained_verified_bytes_only','pre_import_effect_guards':True,'literal_synthetic_environment':True,
      'mode':'independent' if a.review else 'author','review_source_sha256':review_sha,
      'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'blocked_effects':blocked,
      'per_control_bytes':sizes,'passed':passed,**adapter.FLAGS}
    with a.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:report[k] for k in ('mode','tests','failures','errors','passed','live_qualified')}));raise SystemExit(0 if passed else 1)
if __name__=='__main__':main()
