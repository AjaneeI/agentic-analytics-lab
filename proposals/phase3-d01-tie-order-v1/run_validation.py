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
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phase3-d01-provenance-v1'
spec=importlib.util.spec_from_file_location('_tie_guard_upstream',OLD/'run_validation.py')
upstream=importlib.util.module_from_spec(spec);spec.loader.exec_module(upstream)
sys.path.insert(0,str(HERE))
import test_tie_order


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
    p.add_argument('--configuration',type=Path)
    args=p.parse_args()
    if args.output.exists():p.error('refusing to overwrite evidence')
    if args.configuration:
        config=json.loads(args.configuration.read_text())
        expected={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in HERE.iterdir() if f.name in ('verifier_candidate.py','tie_sql_proof.py','test_tie_order.py','run_validation.py','contract.json')}
        if (config.get('state')!='inactive_proposal' or config.get('activation') is not False or
            type(config.get('authorized_treatment_a_attempts')) is not int or config.get('authorized_treatment_a_attempts')!=0 or
            not isinstance(config.get('source_commit'),str) or not re.fullmatch('[0-9a-f]{40}',config['source_commit']) or
            config.get('metric')!=test_tie_order.v.VERSION or config.get('task_id')!='SB-D01' or
            config.get('source_sha256')!=expected):p.error('candidate configuration fingerprint mismatch')
        test_tie_order.CONFIG=config
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(test_tie_order.TieOrderControls)
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
    report={'tie_controls':tie_controls,'version':'phase3-d01-tie-order-v1','python':platform.python_version(),
        'new_unit_tests':r.testsRun,'new_failures':len(r.failures),'new_errors':len(r.errors),
        'reused_unit_tests':regression.testsRun,'reused_failures':len(regression.failures),'reused_errors':len(regression.errors),
        'upstream_controls_with_new_versioned_captures':controls,'side_effect_guard':upstream.observations,
        'candidate_active':False,'live_qualified':False,'phase3_accepted':False,'new_treatment_a_attempts':0,
        'configuration_sha256':hashlib.sha256(args.configuration.read_bytes()).hexdigest() if args.configuration else None,
        'passed':r.wasSuccessful() and regression.wasSuccessful() and not controls['reason_or_outcome_mismatches'] and not tie_controls['mismatches'] and not upstream.observations['blocked_side_effect_attempts']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('upstream_controls_with_new_versioned_captures','side_effect_guard','tie_controls')}))
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
