"""Sixteen literal fixture controls; no benchmark outcomes or SQL."""
import copy
import json
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
if 'p1_manifest' in sys.modules:
    validator=sys.modules['p1_manifest']
elif (HERE/'manifest.py').exists():
    validator=ModuleType('p1_manifest');validator.__file__=str(HERE/'manifest.py')
    sys.modules[validator.__name__]=validator
    exec(compile((HERE/'manifest.py').read_bytes(),validator.__file__,'exec'),validator.__dict__)
else:
    validator=SimpleNamespace(validate=lambda *args,**kwargs:{'valid':None,'reason':'not_implemented'})

def encode(value):return json.dumps(value,separators=(',',':'),allow_nan=False).encode()

def fixture(order='AB',shared=False,unavailable=False):
    cells=[]
    for task in range(1,3 if shared else 2):
        for arm in ('baseline','candidate'):
            first=(arm=='baseline')==(order=='AB');start=0 if first else 2
            cells.append({'task_id':'P1-SYN-'+str(task),'task_version':'synthetic-v1','family':'A',
              'arm':arm,'repeat_id':1,'block_id':'block-1','execution_order':order,
              'start_utc':f'2026-01-01T00:00:0{start}Z','end_utc':f'2026-01-01T00:00:0{start+1}Z',
              'run_id':'synthetic-run','session_id':'synthetic-session','shared_block_id':'shared-1',
              'seed_control':{'state':'unavailable','seed':None,'reason':'Synthetic source cannot set seed'} if unavailable else {'state':'controlled','seed':17,'reason':None},
              'treatment_sha256':('a' if arm=='baseline' else 'b')*64,
              'configuration_sha256':('c' if arm=='baseline' else 'd')*64})
    return {'version':'aalab-execution-manifest-preparation-v1','synthetic':True,
            'independence':'dependent' if shared else 'unknown','cells':cells}

def cases():
    result=[]
    for name,kwargs in [('P1-AB',{}),('P1-BA',{'order':'BA'}),('P1-SHARED',{'shared':True}),('P1-SEED-UNAVAILABLE',{'unavailable':True})]:
        ex=fixture(**kwargs);result.append((name,copy.deepcopy(ex),ex,True,'consistent'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'].pop();result.append(('P1-MISSING-IDENTITY',m,ex,False,'missing_pair'))
    ex=fixture();m=copy.deepcopy(ex);new=fixture()['cells'];new[0]['task_id']=new[1]['task_id']='P1-SYN-EXTRA';m['cells']+=new;result.append(('P1-EXTRA-IDENTITY',m,ex,False,'identity_mismatch'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][1]['execution_order']='BA';result.append(('P1-ORDER-CONTRADICTION',m,ex,False,'order_conflict'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][0]['end_utc']='2025-12-31T23:59:59Z';result.append(('P1-REVERSED-CHRONOLOGY',m,ex,False,'chronology'))
    ex=fixture();ex['cells'][0]['end_utc']='2026-01-01T00:00:03Z';result.append(('P1-SEQUENTIAL-OVERLAP',copy.deepcopy(ex),ex,False,'expected_overlap'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][1]['session_id']='other-session';result.append(('P1-RUN-SESSION-MISMATCH',m,ex,False,'pair_provenance'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][1]['family']='B';result.append(('P1-FAMILY-DRIFT',m,ex,False,'task_membership'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][1]['shared_block_id']='other-block';result.append(('P1-SHARED-BLOCK-DRIFT',m,ex,False,'pair_provenance'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][0]['seed_control']['seed']=None;result.append(('P1-CONTROLLED-SEED-MISSING',m,ex,False,'seed_state'))
    ex=fixture(unavailable=True);m=copy.deepcopy(ex);m['cells'][0]['seed_control']['seed']=17;result.append(('P1-UNAVAILABLE-SEED-INCONSISTENT',m,ex,False,'seed_state'))
    ex=fixture();m=copy.deepcopy(ex);m['cells'][0]['treatment_sha256']='e'*64;m['cells'][0]['configuration_sha256']='f'*64;result.append(('P1-TREATMENT-CONFIG-DRIFT',m,ex,False,'binding_mismatch'))
    ex=fixture();m=copy.deepcopy(ex);m['independence']='independent';result.append(('P1-UNSUPPORTED-INDEPENDENCE',m,ex,False,'unsupported_independence'))
    return result

OBSERVED=[]

class ManifestControls(unittest.TestCase):
    def test_sixteen_declared_cases(self):
        for name,submitted,expected,want,reason in cases():
            with self.subTest(case=name):
                raw=encode(submitted);trusted=encode(expected)
                verdict=validator.validate(raw,expected=trusted)
                OBSERVED.append({'case':name,'expected_valid':want,'expected_reason':reason,'verdict':verdict})
                self.assertIs(verdict['valid'],want,name)
                self.assertEqual(verdict['reason'],reason,name)
                self.assertIs(verdict['live_qualified'],False)
                self.assertIs(verdict['independence_established'],False)
                self.assertIs(verdict['scientific_ready'],False)
                self.assertIs(verdict['active'],False)
                self.assertEqual(verdict['new_attempts'],0)
                self.assertEqual(encode(submitted),raw)
                self.assertEqual(encode(expected),trusted)
                self.assertLessEqual(len(encode(verdict)),65536)
                if want:self.assertEqual(verdict['declared_dependence'],submitted['independence'])

if __name__=='__main__':unittest.main(verbosity=2)
