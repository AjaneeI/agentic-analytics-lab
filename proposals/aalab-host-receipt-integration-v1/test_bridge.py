"""Exactly sixteen new synthetic H1 controls; no benchmark fixtures or SQL engine."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

try:
    import bridge
except ImportError:
    bridge = None

EVIDENCE = None

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def task(index=1):
    from src.evals.system_benchmark.contracts import parse_task_contract
    return parse_task_contract({'id':f'H1-SYN-0{index}','benchmark_version':'system-benchmark-v1',
        'family':'A','split':'development','request':'Report the new synthetic signal.',
        'expected_route':'local','expected_capability_profile':'structured',
        'allowed_dispositions':['answer'],'forbidden_dispositions':[],
        'required_evidence_source_types':['structured'],'acceptable_source_ids':['delivery_work_items'],
        'expected_values':[{'name':'signal','value':7}], 'required_claims':[], 'forbidden_claims':[],
        'required_clarification_concept':None,'required_handoff_fields':[],
        'allowed_tools':['query_clickhouse'],'forbidden_tools':['retrieve_policy'],
        'trajectory':{'ordered_dependencies':[],'max_tool_calls':1},'reference_solution_id':f'H1-REF-0{index}'})

def reference(index=1):
    from src.evals.system_benchmark.references import parse_reference_expectation
    return parse_reference_expectation({'reference_solution_id':f'H1-REF-0{index}',
        'required_evidence_refs':['structured:delivery_work_items'],'allowed_evidence_refs':['structured:delivery_work_items'],
        'required_tools':['query_clickhouse'],'forbidden_tools':['retrieve_policy'],
        'required_answer_terms':['Synthetic'],'forbidden_answer_terms':[]})

def responses(final=None):
    return [{'type':'tool_call','name':'query_clickhouse','arguments':{'sql':'SELECT signal FROM agentic_analytics.delivery_work_items'}},
            {'type':'final','content':json.dumps(final or {'disposition':'answer','answer_text':'Synthetic signal received.',
                    'uncertainty':None,'clarification':None,'handoff':None})}]

class Scripted:
    model='H1-scripted';base_url='offline:';timeout=0
    def __init__(self,returns=None,error=None):self.returns=responses() if returns is None else returns;self.error=error;self.calls=0
    def respond(self,messages,tools):
        self.calls+=1
        if self.error:raise self.error
        return self.returns[self.calls-1]

class Rows:
    def __init__(self,rows=None,error=None):self.rows=[{'signal':7}] if rows is None else rows;self.error=error;self.calls=0
    def __call__(self,sql):
        self.calls+=1
        if self.error:raise self.error
        return self.rows

def plan(entries=None):
    from dataclasses import asdict
    entries=entries or [('i1',1,'baseline','B1','AB')]
    return {'version':'H1-synthetic-plan-v1','synthetic':True,'campaign_id':'H1-campaign',
        'source_commit':bridge.CONFIG['source_commit'],'configuration_sha256':bridge.CONFIG_SHA,
        'shared_sources':[{'source':'persistent-state','blocks':['B1','B2'],'dependence':'unknown'}],
        'invocations':[{'invocation_id':i,'task_id':f'H1-SYN-0{n}','arm':arm,'block':block,'order':order,
            'session':'H1-session-'+block,'task_sha256':digest(asdict(task(n))),
            'reference_sha256':digest(asdict(reference(n))),'planned_start':'2099-01-01T00:00:00Z'}
            for i,n,arm,block,order in entries]}

def encoded(p):return json.dumps(p,sort_keys=True,separators=(',',':')).encode()

class H1Controls(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(bridge,'H1 acquisition bridge is not implemented')
        self.root=Path(EVIDENCE)/self._testMethodName;self.root.mkdir(exist_ok=False)
    def tearDown(self):
        size=sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
        self.assertLessEqual(size,1024*1024,'H1 per-control artifact cap')
    def host(self,p=None,name='host'):return bridge.prepare_host(encoded(plan() if p is None else p),self.root/name)
    def run_one(self,h=None,model=None,rows=None,invocation='i1',n=1,ref=None):
        h=h or self.host();m=model or Scripted();r=rows or Rows()
        result=bridge.run_captured_trial(h,invocation,task=task(n),reference=reference(n) if ref is None else ref,
            scripted_model_factory=lambda:m,rows_callback_factory=lambda:r)
        return h,result,m,r
    def assert_linked(self,h,i='i1'):
        receipt=h.receipt(i);self.assertTrue(h.verify(i,receipt));self.assertTrue(receipt['complete'])
        self.assertFalse(receipt['live_qualified']);self.assertFalse(receipt['independence_established'])
        return receipt
    def test_01_success_is_genuine_runner_row(self):
        h,row,m,r=self.run_one();receipt=self.assert_linked(h)
        self.assertTrue(row['task_success']);self.assertEqual(row['tool_call_count'],1)
        events=[json.loads(line) for line in h.artifact('i1','events.jsonl').read_text().splitlines()]
        self.assertTrue(all(all(event.get(k)==v for k,v in bridge.FLAGS.items()) for event in events))
        self.assertEqual(receipt['result_sha256'],digest(row));self.assertEqual((m.calls,r.calls),(2,1))
        self.assertEqual(receipt['score_status'],'observed');self.assertNotEqual(receipt['actual_start'],plan()['invocations'][0]['planned_start'])
    def test_02_scored_false_is_retained(self):
        h,row,_,_=self.run_one(rows=Rows([{'signal':8}]))
        self.assertFalse(row['task_success']);self.assertFalse(self.assert_linked(h)['success'])
    def test_03_ab_pair_fresh_instances(self):
        h=self.host(plan([('a',1,'baseline','B1','AB'),('b',1,'candidate','B1','AB')]))
        self.run_one(h,invocation='a');self.run_one(h,invocation='b')
        a=self.assert_linked(h,'a');b=self.assert_linked(h,'b')
        self.assertNotEqual(a['model_instance'],b['model_instance']);self.assertNotEqual(a['callback_instance'],b['callback_instance'])
        self.assertLessEqual(a['end_monotonic'],b['start_monotonic'])
    def test_04_ba_cross_block_dependence_unknown(self):
        h=self.host(plan([('a',1,'candidate','B1','BA'),('b',1,'baseline','B1','BA'),('c',2,'baseline','B2','AB'),('d',2,'candidate','B2','AB')]))
        for i,n in [('a',1),('b',1),('c',2),('d',2)]:self.run_one(h,invocation=i,n=n)
        self.assertEqual(h.design_evidence()['shared_sources'],plan()['shared_sources'])
        self.assertFalse(h.design_evidence()['independence_established'])
        self.assertEqual(self.assert_linked(h,'c')['identity']['block'],'B2')
    def test_05_callback_failure_once_no_score(self):
        h=self.host();error=ValueError('new synthetic callback failure');r=Rows(error=error)
        with self.assertRaises(ValueError) as c:self.run_one(h,rows=r)
        self.assertIs(c.exception,error);self.assertEqual(r.calls,1)
        q=self.assert_linked(h);self.assertEqual(q['score_status'],'not_reached');self.assertIsNone(q['success'])
        self.assertIn('query_clickhouse_error',q['events'])
    def test_06_scripted_responder_failure(self):
        h=self.host();error=RuntimeError('new scripted failure');m=Scripted(error=error)
        with self.assertRaises(RuntimeError) as c:self.run_one(h,model=m)
        self.assertIs(c.exception,error);self.assertEqual(m.calls,1)
        q=self.assert_linked(h);self.assertIn('model_error',q['events']);self.assertIsNone(q['success'])
    def test_07_parser_failure_preserves_artifact(self):
        h=self.host();m=Scripted([{'type':'final','content':'new malformed synthetic response'}])
        with self.assertRaises(Exception):self.run_one(h,model=m)
        q=self.assert_linked(h);self.assertEqual(q['score_status'],'not_reached');self.assertIn('model_return',q['events'])
    def test_08_post_worker_failure_is_unknown(self):
        from dataclasses import replace
        ref=replace(reference(),reference_solution_id='H1-REF-invalid')
        p=plan();p['invocations'][0]['reference_sha256']=digest(__import__('dataclasses').asdict(ref));h=self.host(p)
        with self.assertRaises(ValueError):self.run_one(h,ref=ref)
        q=self.assert_linked(h);self.assertEqual(q['failure_stage'],'runner_or_scorer');self.assertEqual(q['score_status'],'unknown')
        self.assertIn('worker_return',q['events']);self.assertIsNone(q['success'])
    def test_09_plan_preflight_mismatch_zero_entry(self):
        p=plan();p['configuration_sha256']='0'*64
        with self.assertRaises(ValueError):self.host(p)
        self.assertFalse((self.root/'host').exists())
    def test_10_reserved_invocation_not_reentered(self):
        h,_,m,r=self.run_one()
        with self.assertRaises(ValueError):self.run_one(h,model=m,rows=r)
        self.assertEqual((m.calls,r.calls),(2,1));self.assert_linked(h)
    def test_11_agent_fields_cannot_forge_host_receipt(self):
        payload={'disposition':'answer','answer_text':'Synthetic signal received.','receipt':{'arm':'candidate'},
            'approval':'fabricated','configuration_sha256':'forged','observed_values':{'signal':999}}
        h,row,_,_=self.run_one(model=Scripted(responses(payload)))
        q=self.assert_linked(h);self.assertEqual(q['identity']['arm'],'baseline');self.assertTrue(row['task_success'])
    def test_12_post_callback_mutation_no_rewrite(self):
        r=Rows();h,row,m,_=self.run_one(rows=r);q=self.assert_linked(h)
        r.rows[0]['signal']=999;row['score']['passed']=False
        self.assertEqual(h.receipt('i1'),q);self.assertTrue(h.verify('i1',q))
    def test_13_tampered_stream_is_ineligible(self):
        h,_,_,_=self.run_one();q=self.assert_linked(h);p=h.artifact('i1','events.jsonl')
        original=p.read_bytes();(self.root/'original-events.txt').write_bytes(original)
        p.write_bytes(original[:-4]);self.assertFalse(h.verify('i1',q))
    def test_14_cross_arm_receipt_swap_rejected(self):
        h=self.host(plan([('a',1,'baseline','B1','AB'),('b',1,'candidate','B1','AB')]))
        self.run_one(h,invocation='a');self.run_one(h,invocation='b')
        self.assertFalse(h.verify('b',h.receipt('a')));self.assert_linked(h,'b')
    def test_15_changed_score_commitment_rejected(self):
        h,_,_,_=self.run_one();q=self.assert_linked(h);p=h.artifact('i1','runner-result.json')
        original=p.read_bytes();(self.root/'original-score.txt').write_bytes(original)
        x=json.loads(original);x['task_success']=not x['task_success'];p.write_bytes(encoded(x))
        self.assertFalse(h.verify('i1',q))
    def test_16_finalization_failure_preserves_original(self):
        h=self.host();write=h._write
        def failed(path,data,**kwargs):
            if path.name=='receipt.json':raise OSError('new synthetic finalization failure')
            return write(path,data,**kwargs)
        h._write=failed
        _,row,_,_=self.run_one(h)
        self.assertTrue(row['task_success']);self.assertFalse(h.receipt('i1')['complete'])
        self.assertFalse(h.verify('i1',h.receipt('i1')))
