"""Inspected new synthetic tests plus pinned D01 synthetic regressions only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import unittest

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phase3-d01-provenance-v1'
# The unchanged upstream runner installs socket/process/runtime/file-DB guards.
spec=importlib.util.spec_from_file_location('_capture_validation_upstream',OLD/'run_validation.py')
upstream=importlib.util.module_from_spec(spec);spec.loader.exec_module(upstream)
sys.path.insert(0,str(HERE))
import test_capture

def integration_cases(config):
    t=test_capture;cases=[]
    for name,sql,want in [
        ('canonical',t.SQL,'proven'),
        ('qualified',t.SQL.replace('FROM delivery_work_items','FROM agentic_analytics.delivery_work_items'),'proven'),
        ('average',t.SQL.replace('100.0*SUM(blocked)/COUNT(*)','100.0*AVG(blocked)'),'proven'),
        ('literal',t.SQL.replace('100.0*SUM(blocked)/COUNT(*)','60.0'),'contradicted'),
        ('decorative',t.SQL.replace('100.0*SUM(blocked)/COUNT(*)','60.0+0*SUM(blocked)'),'contradicted'),
        ('wrong-population',t.SQL.replace(" WHERE status!='done'",''),'contradicted')]:
        with t.SyntheticCaptureSession(t.fixture(),config) as h:
            rows=h.query(sql);c=h.calls[0];v=h.verify(t.claim(c),call=c)
            context=h.verification_context(c);record=h.resolve(c.execution_id)
            cases.append({'id':name,'expected_scientific':want,'observed':v['status'],'reason':v['reason'],
                'sql':sql,'rows':rows,'query_sha256':context['expected']['query_sha256'],
                'snapshot_sha256':context['expected']['snapshot_sha256'],'config_sha256':context['expected']['config_sha256'],
                'complete':record.complete,'success':record.success,'known_gap':False})
    for stable in [True,False]:
        rows=[{'id':i+1,'team':team,'status':'todo','blocked':1} for i,team in enumerate(['Dune','Elm'])]
        with t.SyntheticCaptureSession(rows,config) as h:
            sql=t.SQL.replace('DESC LIMIT','DESC, team ASC LIMIT') if stable else t.SQL
            result=h.query(sql);c=h.calls[0]
            v=h.verify(t.claim(c,team=result[0]['team'],blocked_pct=100,unique_winner=False),call=c)
            cases.append({'id':'stable-tie' if stable else 'upstream-unspecified-tie-order-gap',
                'expected_scientific':'proven','observed':v['status'],'reason':v['reason'],
                'sql':sql,'rows':result,'known_gap':not stable})
    mismatches=[c['id'] for c in cases if c['observed']!=c['expected_scientific']]
    return {'cases':cases,'case_count':len(cases),'semantic_mismatches':mismatches,
        'false_acceptances':[c['id'] for c in cases if c['observed']=='proven' and c['expected_scientific']!='proven'],
        'supported_valid_false_rejections':[c['id'] for c in cases if c['observed']!='proven' and c['expected_scientific']=='proven'],
        'unexpected_mismatches':[c['id'] for c in cases if c['observed']!=c['expected_scientific'] and not c['known_gap']]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--configuration',type=Path)
    args=p.parse_args()
    if args.output.exists():p.error('refusing to overwrite evidence')
    config=json.loads(args.configuration.read_text()) if args.configuration else test_capture.CONFIG
    if args.configuration:
        from capture_adapter import validate_host_config
        if 'adapter_source_sha256' not in config:p.error('explicit configuration requires complete source pins')
        validate_host_config(config)  # Before even synthetic tests create SQLite.
    suite=unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(test_capture.CaptureControls),
        unittest.defaultTestLoader.loadTestsFromName('test_verifier.ProvenanceControls')])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    controls=upstream.matrix()
    integration=integration_cases(config)
    report={'version':'phase3-d01-capture-integration-v1','python':platform.python_version(),
        'unit_tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'upstream_controls':controls,'integration_controls':integration,'side_effect_guard':upstream.observations,
        'configuration_file_sha256':hashlib.sha256(args.configuration.read_bytes()).hexdigest() if args.configuration else None,
        'integration_host_config':config,
        'unit_fixture_source_commit_scope':'PR121 upstream pin in unit fixtures; actual reviewed candidate commit and source hashes recorded separately',
        'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(HERE.iterdir()) if f.is_file() and f.suffix in ('.py','.json')},
        'live_qualified':False,'candidate_active':False,'new_treatment_a_attempts':0,
        'phase3_accepted':False,'full_semantic_compatibility':False,
        'known_blocker':'Upstream verifier can reject a legitimate tied LIMIT1 member without a secondary sort; preserved, not corrected or scored as success.',
        'passed':result.wasSuccessful() and not controls['reason_or_outcome_mismatches'] and not integration['unexpected_mismatches'] and not integration['false_acceptances'] and not upstream.observations['blocked_side_effect_attempts']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(report,handle,indent=2,sort_keys=True);handle.write('\n')
    print(json.dumps({k:report[k] for k in ['python','unit_tests','failures','errors','passed']}))
    raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__':main()
