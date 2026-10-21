"""New inactive tie candidate only; side effects denied before test imports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys
import unittest
from types import ModuleType
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phase3-d01-provenance-v1'
# Keep import inert: only standard-library modules are loaded above.
ROOT=HERE.parents[1]
CANDIDATE_FILES={'verifier_candidate.py','tie_sql_proof.py','test_tie_order.py',
                 'run_validation.py','test_preflight.py','contract.json'}
DEPENDENCIES={
 'proposals/phase3-d01-provenance-v1/run_validation.py',
 'proposals/phase3-d01-provenance-v1/test_verifier.py',
 'proposals/phase3-d01-provenance-v1/verifier.py',
 'proposals/phase3-d01-provenance-v1/sql_proof.py',
 'proposals/phase3-d01-provenance-v1/contract.json',
 'proposals/phase3-d01-capture-integration-v1/capture_adapter.py',
 'proposals/phase3-d01-capture-integration-v1/contract.json'}
CONTRACT_DEPENDENCIES=DEPENDENCIES-{
 'proposals/phase3-d01-provenance-v1/run_validation.py',
 'proposals/phase3-d01-provenance-v1/test_verifier.py'}
upstream=None
test_tie_order=None
_verified_sources=None

def _check_files(pins,names,root,verified_sources):
    if not isinstance(pins,dict) or pins.keys()!=names:
        raise ValueError('incomplete or unexpected dependency/source manifest')
    actual={}
    for name in sorted(names):
        expected=pins[name]
        if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected):
            raise ValueError('invalid fingerprint: '+name)
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('missing or outside-checkout dependency: '+name)
        source=path.read_bytes()
        actual[name]=hashlib.sha256(source).hexdigest()
        if actual[name]!=expected:
            raise ValueError('dependency/source fingerprint mismatch: '+name)
        verified_sources[path]=source
    return actual

def preflight(configuration):
    """Read/hash only. Reject before loading any candidate/upstream code."""
    global _verified_sources
    _verified_sources=None
    verified_sources={}
    config=json.loads(configuration.read_text())
    if (not isinstance(config,dict) or config.get('version')!='phase3-d01-tie-order-v1-offline-config-v3'
        or config.get('state')!='inactive_proposal' or config.get('activation') is not False
        or type(config.get('authorized_treatment_a_attempts')) is not int
        or config['authorized_treatment_a_attempts']!=0
        or not isinstance(config.get('source_commit'),str)
        or not re.fullmatch('[0-9a-f]{40}',config['source_commit'])
        or config.get('metric')!='phase3-d01-tie-order-v1' or config.get('task_id')!='SB-D01'):
        raise ValueError('candidate configuration fingerprint mismatch')
    candidate=_check_files(config.get('source_sha256'),CANDIDATE_FILES,HERE,verified_sources)
    contract=json.loads((HERE/'contract.json').read_text())
    if contract.get('state')!='inactive_proposal' or contract.get('version')!=config['metric']:
        raise ValueError('inactive contract mismatch')
    declared=contract.get('upstream_source_sha256')
    if not isinstance(declared,dict) or declared.keys()!=CONTRACT_DEPENDENCIES:
        raise ValueError('contract dependency manifest mismatch')
    dependencies=_check_files(config.get('dependency_sha256'),DEPENDENCIES,ROOT,verified_sources)
    if any(dependencies[name]!=value for name,value in declared.items()):
        raise ValueError('configuration conflicts with pinned upstream contract')
    _verified_sources=verified_sources
    return config,{'version':'phase3-d01-dependency-preflight-v1',
        'verified_dependency_count':len(dependencies),'dependency_sha256':dependencies,
        'candidate_source_sha256':candidate,'verified_before_dependency_imports':True,'execution_source':'retained_verified_source_bytes'}

def _load_verified_dependencies():
    """Use pinned bytes, never timestamp-based .pyc or ambient module caches."""
    global upstream,test_tie_order
    if _verified_sources is None:
        raise RuntimeError('dependency preflight required before source loading')
    modules=[
        ('sql_proof',OLD/'sql_proof.py'),
        ('verifier',OLD/'verifier.py'),
        ('test_verifier',OLD/'test_verifier.py'),
        ('_tie_guard_upstream',OLD/'run_validation.py'),
        ('tie_sql_proof',HERE/'tie_sql_proof.py'),
        ('verifier_candidate',HERE/'verifier_candidate.py'),
        ('test_tie_order',HERE/'test_tie_order.py'),
        ('test_preflight',HERE/'test_preflight.py')]
    for name,path in modules:
        module=ModuleType(name)
        module.__file__=str(path)
        module.__package__=''
        sys.modules[name]=module
        exec(compile(_verified_sources[path.resolve()],str(path),'exec'),module.__dict__)
    upstream=sys.modules['_tie_guard_upstream']
    test_tie_order=sys.modules['test_tie_order']


def tie_matrix():
    t=test_tie_order;cases=[]
    def case(name,expected,host,**claim):
        observed=t.check(host,**claim)
        cases.append({'id':name,'expected':expected,'observed':observed['status'],'reason':observed['reason'],
            'sql':host.record.query,'rows':json.loads(host.record.result_json),
            'snapshot_sha256':host.expected['snapshot_sha256'],'query_sha256':host.expected['query_sha256'],
            'config_sha256':host.expected['config_sha256'],'contract_sha256':host.record.contract_sha256,
            'live_qualified':observed['live_qualified']})
    case('T01-real-sqlite-unspecified-co-max','proven',t.Host())
    for team in ['Dune','Elm']:
        case('T02-peer-'+team,'proven',t.Host(returned=[{'team':team,'rate':100.0}]),team=team)
    for direction,team,other in [('ASC','Dune','Elm'),('DESC','Elm','Dune')]:
        sql=t.SQL.replace('rate DESC LIMIT','rate DESC, team '+direction+' LIMIT')
        case('T03-explicit-'+direction,'proven',t.Host(sql))
        case('N01-explicit-wrong-'+direction,'contradicted',t.Host(sql,returned=[{'team':other,'rate':100.0}]),team=other)
    case('N02-false-unique','contradicted',t.Host(),unique=True)
    case('N03-uncaptured-winner','contradicted',t.Host(),team='Dune')
    case('N04-fabricated-rate','contradicted',t.Host(returned=[{'team':'Elm','rate':99.9}]))
    rows=t.snapshot((('Aster',1,1),('Birch',1,2),('Cedar',1,2)))
    sql=t.SQL.replace('LIMIT 1','LIMIT 2')
    for team in ['Birch','Cedar']:
        case('T04-boundary-'+team,'proven',t.Host(sql,rows,[{'team':'Aster','rate':100.0},{'team':team,'rate':50.0}]),team='Aster',unique=True)
    case('N05-missing-strict-prefix','contradicted',t.Host(sql,rows,[{'team':'Birch','rate':50.0},{'team':'Cedar','rate':50.0}]),team='Birch',rate=50)
    case('N06-duplicate','contradicted',t.Host(sql,rows,[{'team':'Aster','rate':100.0}]*2),team='Aster')
    case('I01-failed-execution','insufficient',t.Host(success=False))
    case('I02-incomplete-capture','insufficient',t.Host(complete=False))
    return {'cases':cases,'case_count':len(cases),
        'mismatches':[c['id'] for c in cases if c['expected']!=c['observed']],
        'false_acceptances':[c['id'] for c in cases if c['expected']!='proven' and c['observed']=='proven'],
        'supported_valid_false_rejections':[c['id'] for c in cases if c['expected']=='proven' and c['observed']!='proven']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--configuration',type=Path,default=HERE/'synthetic-config-v3.json')
    args=p.parse_args()
    if args.output.exists():p.error('refusing to overwrite evidence')
    try:
        config,preflight_receipt=preflight(args.configuration)
    except (OSError,ValueError,TypeError,RecursionError) as error:
        p.error('offline preflight refused: '+str(error))
    _load_verified_dependencies()
    test_tie_order.CONFIG=config
    import test_preflight
    suite=unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(test_tie_order.TieOrderControls),
        unittest.defaultTestLoader.loadTestsFromTestCase(test_preflight.PreflightControls)])
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    # Reuse unchanged upstream control definitions with separately versioned NEW
    # host captures. Original runner/evidence are exercised independently.
    import test_verifier as old_tests
    old_v,old_config=old_tests.v,old_tests.CONFIG
    try:
        old_tests.v=test_tie_order.v;old_tests.CONFIG=test_tie_order.CONFIG
        regression=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(old_tests.ProvenanceControls))
        controls=upstream.matrix()
    finally:
        old_tests.v=old_v;old_tests.CONFIG=old_config
    tie_controls=tie_matrix()
    report={'preflight':preflight_receipt,'tie_controls':tie_controls,'version':'phase3-d01-tie-order-v1','python':platform.python_version(),
        'new_unit_tests':r.testsRun,'new_failures':len(r.failures),'new_errors':len(r.errors),
        'reused_unit_tests':regression.testsRun,'reused_failures':len(regression.failures),'reused_errors':len(regression.errors),
        'upstream_controls_with_new_versioned_captures':controls,'side_effect_guard':upstream.observations,
        'candidate_active':False,'live_qualified':False,'phase3_accepted':False,'new_treatment_a_attempts':0,
        'configuration_sha256':hashlib.sha256(args.configuration.read_bytes()).hexdigest() if args.configuration else None,
        'passed':r.wasSuccessful() and regression.wasSuccessful() and not controls['reason_or_outcome_mismatches'] and not tie_controls['mismatches'] and not upstream.observations['blocked_side_effect_attempts']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('upstream_controls_with_new_versioned_captures','side_effect_guard','tie_controls','preflight')}))
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
