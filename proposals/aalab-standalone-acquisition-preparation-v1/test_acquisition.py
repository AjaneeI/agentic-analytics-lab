"""Exactly twelve authored A3 slots. All replies belong to the test delegate."""
import copy
from dataclasses import asdict
import hashlib
import http.client
import io
import json
from pathlib import Path
import unittest
import urllib.error
import urllib.request
try:
    import a3_adapter as adapter
except ImportError:
    adapter=None
EVIDENCE=None
SQL='SELECT 37 AS a3_signal'
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def task(identity='A3-SYN-01'):
    from src.evals.system_benchmark.contracts import parse_task_contract
    return parse_task_contract({'id':identity,'benchmark_version':'system-benchmark-v1',
      'family':'A','split':'development','request':'Report the newly authored A3 synthetic signal.',
      'expected_route':'local','expected_capability_profile':'structured','allowed_dispositions':['answer'],
      'forbidden_dispositions':[],'required_evidence_source_types':['structured'],
      'acceptable_source_ids':['delivery_work_items'],'expected_values':[{'name':'a3_signal','value':37}],
      'required_claims':[],'forbidden_claims':[],'required_clarification_concept':None,
      'required_handoff_fields':[],'allowed_tools':['query_clickhouse'],'forbidden_tools':['retrieve_policy'],
      'trajectory':{'ordered_dependencies':[],'max_tool_calls':1},'reference_solution_id':'A3-REF-01'})
def reference():
    from src.evals.system_benchmark.references import parse_reference_expectation
    return parse_reference_expectation({'reference_solution_id':'A3-REF-01',
      'required_evidence_refs':['structured:delivery_work_items'],'allowed_evidence_refs':['structured:delivery_work_items'],
      'required_tools':['query_clickhouse'],'forbidden_tools':['retrieve_policy'],
      'required_answer_terms':['A3 synthetic'],'forbidden_answer_terms':[]})
def plan(two=False):
    return {'version':'A3-synthetic-plan-v1','synthetic':True,'live_dispatch_allowed':False,
      'configuration_sha256':adapter.CONFIG_SHA,'source_commit':adapter.CONFIG['source_commit'],
      'invocations':[{'invocation_id':i,'task_id':'A3-SYN-01','arm':arm,'block':'B1',
       'session':'A3-session-'+i,'task_sha256':digest(asdict(task())),
       'reference_sha256':digest(asdict(reference()))}
       for i,arm in ([('a','baseline'),('b','candidate')] if two else [('a','baseline')])]}
def replies(extra=None):
    final={'disposition':'answer','answer_text':'A3 synthetic signal received.',
      'uncertainty':None,'clarification':None,'handoff':None};final.update(extra or {})
    return [encoded({'message':{'tool_calls':[{'function':{'name':'query_clickhouse','arguments':{'sql':SQL}}}]}}),
      encoded({'a3_signal':37})+b'\n',encoded({'message':{'content':json.dumps(final)}})]
class MemoryResponse:
    def __init__(self,body,url,partial=False):
        self.body=body;self.url=url;self.status=202;self.headers={'X-A3-Capture':'delegate-owned'}
        self.partial=partial;self.reads=0;self.exits=0
    def __enter__(self):return self
    def __exit__(self,*args):self.exits+=1;return False
    def geturl(self):return self.url
    def read(self,*args,**kwargs):
        self.reads+=1
        if self.partial:raise http.client.IncompleteRead(self.body,5)
        return self.body
class MemoryDelegate:
    """Trusted fixture producer, separate from the acquisition implementation."""
    def __init__(self,bodies=None,*,error_at=None,partial=False):
        self.bodies=list(replies() if bodies is None else bodies)
        assert len(encoded([b.decode() for b in self.bodies]))<=16384
        assert all(len(b)<=4096 for b in self.bodies)
        self.calls=[];self.responses=[];self.error_at=error_at;self.partial=partial;self.unread_error_body=None
    def __call__(self,request,*,timeout):
        index=len(self.calls);self.calls.append((request,timeout))
        if self.error_at==index:
            self.unread_error_body=io.BytesIO(b'A3 unread error body')
            raise RuntimeError('A3 synthetic upstream failure')
        response=MemoryResponse(self.bodies[index],request.full_url,self.partial)
        self.responses.append(response);return response
class A3Controls(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(adapter,'A3 delegating acquisition adapter is not implemented')
        self.root=Path(EVIDENCE)/self._testMethodName;self.root.mkdir(exist_ok=False)
    def tearDown(self):
        if hasattr(self,'root'):self.assertLessEqual(sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file()),1048576)
    def host(self,delegate=None,two=False):
        self.delegate=delegate if delegate is not None else MemoryDelegate(replies()* (2 if two else 1))
        return adapter.prepare_acquisition(encoded(plan(two)),self.root/'host',transport_delegate=self.delegate)
    def run_one(self,h,i='a'):return adapter.run_acquired_trial(h,i,task=task(),reference=reference())
    def linked(self,h,i='a'):
        r=h.acquisition_receipt(i);self.assertTrue(h.verify_acquisition(i,r));self.assertTrue(r['complete'])
        self.assertFalse(r['live_qualified']);self.assertFalse(r['live_dispatch_allowed']);return r
    def test_01_delegate_bytes_link_genuine_outcome(self):
        h=self.host();row=self.run_one(h);r=self.linked(h)
        self.assertEqual(len(self.delegate.calls),3)
        self.assertEqual([c['kind'] for c in r['calls']],['model','query','model'])
        self.assertEqual(r['result_sha256'],digest(row));self.assertFalse(row['task_success'])
        for i,(response,c) in enumerate(zip(self.delegate.responses,r['calls'])):
            self.assertTrue(c.get('synthetic'));self.assertTrue(c.get('inactive'))
            for flag in ('live_dispatch_allowed','live_authentication','live_qualified','independence_established','scientific_ready'):
                self.assertIs(c.get(flag),False)
            self.assertEqual(c.get('new_attempts'),0)
            self.assertEqual(c['response']['status'],202);self.assertEqual(c['response']['headers'],[['X-A3-Capture','delegate-owned']])
            self.assertEqual((h.root/c['body_path']).read_bytes(),self.delegate.bodies[i])
            self.assertEqual(response.reads,1);self.assertEqual(response.exits,1)
            self.assertEqual(c['delegate_entries'],1);self.assertEqual(c['remote_lifetime'],'unverified')
        payload=json.loads(self.delegate.calls[0][0].data)
        self.assertEqual(payload['options'],{'temperature':0,'num_predict':512,'num_ctx':65536})
        self.assertEqual(payload['keep_alive'],'30m');self.assertEqual(self.delegate.calls[1][0].data,SQL.encode())
        self.assertIn('compile_expressions=0',self.delegate.calls[1][0].full_url)
        sidecar=json.loads((h.root/'a/invocation-entry.json').read_bytes())
        self.assertFalse(sidecar['live_dispatch_allowed']);self.assertIn('inherited H1 records unmodified',sidecar['flag_scope'])
    def test_02_false_score_no_invented_evidence(self):
        h=self.host();row=self.run_one(h);r=self.linked(h)
        self.assertFalse(row['task_success']);self.assertFalse(r['success'])
        self.assertIn('missing_required_evidence',row['score']['reason_codes'])
        self.assertEqual(row['evidence_refs'],[]);self.assertEqual(row['structured_values'],{})
    def test_03_acquired_body_before_model_parse_failure(self):
        h=self.host(MemoryDelegate([b'A3 malformed JSON']))
        with self.assertRaises(json.JSONDecodeError):self.run_one(h)
        r=self.linked(h);self.assertEqual(r['score_status'],'not_reached');self.assertIsNone(r['success'])
        self.assertEqual((h.root/r['calls'][0]['body_path']).read_bytes(),b'A3 malformed JSON')
        self.assertEqual(r['calls'][0]['stage'],'read_complete');self.assertEqual(r['surfaced_error']['type'],'JSONDecodeError')
    def test_04_query_wrap_preserves_upstream_unread_error(self):
        h=self.host(MemoryDelegate(error_at=1))
        with self.assertRaisesRegex(RuntimeError,'ClickHouse query failed: A3 synthetic upstream failure'):self.run_one(h)
        r=self.linked(h);c=r['calls'][1]
        self.assertEqual(c['upstream_error']['type'],'RuntimeError');self.assertIsNone(c['response']['status'])
        self.assertEqual(c['body_state'],'unavailable');self.assertIsNone(c['body_path'])
        self.assertEqual(self.delegate.unread_error_body.tell(),0)
        self.assertEqual(r['surfaced_error']['type'],'RuntimeError');self.assertEqual(len(self.delegate.calls),2)
    def test_05_partial_read_no_extra_drain(self):
        h=self.host(MemoryDelegate([b'{"message":'],partial=True))
        with self.assertRaises(http.client.IncompleteRead):self.run_one(h)
        r=h.acquisition_receipt('a');self.assertFalse(h.verify_acquisition('a',r));self.assertFalse(r['complete'])
        self.assertEqual(r['calls'][0]['body_state'],'partial')
        self.assertEqual((h.root/r['calls'][0]['body_path']).read_bytes(),b'{"message":')
        self.assertEqual(self.delegate.responses[0].reads,1);self.assertEqual(self.delegate.responses[0].exits,1)
    def test_06_source_mismatch_before_client_entry(self):
        pins=copy.deepcopy(adapter.CONFIG['external_sources']);pins['src/agents/ollama_client.py']['sha256']='0'*64
        d=MemoryDelegate()
        with self.assertRaisesRegex(ValueError,'source pin mismatch'):adapter.CHECK_SOURCES(pins)
        self.assertEqual(d.calls,[]);self.assertEqual(adapter.BOUNDARY.active,None)
    def test_07_required_binding_failure_prevents_dispatch(self):
        h=self.host();write=h._write
        def failed(path,raw,**kwargs):
            if Path(path).name=='call-1-entry.json':raise OSError('A3 required sink unavailable')
            return write(path,raw,**kwargs)
        h._write=failed
        with self.assertRaisesRegex(OSError,'required sink unavailable'):self.run_one(h)
        r=h.acquisition_receipt('a');self.assertFalse(r['complete']);self.assertEqual(self.delegate.calls,[])
    def test_08_secondary_sink_failure_preserves_original_row(self):
        h=self.host();write=h._write
        def failed(path,raw,**kwargs):
            if Path(path).name=='call-1-body.bin':raise OSError('A3 secondary sink unavailable')
            return write(path,raw,**kwargs)
        h._write=failed;row=self.run_one(h);r=h.acquisition_receipt('a')
        self.assertFalse(row['task_success']);self.assertEqual(r['result_sha256'],digest(row))
        self.assertFalse(r['complete']);self.assertFalse(h.verify_acquisition('a',r));self.assertEqual(len(self.delegate.calls),3)
    def test_09_agent_fields_cannot_replace_host_facts(self):
        h=self.host(MemoryDelegate(replies({'provider':'forged','model_digest':'forged','effective_settings':{'x':1},'approval':'forged'})))
        self.run_one(h);r=self.linked(h)
        self.assertIsNone(r['live_model_digest']);self.assertIsNone(r['live_effective_settings'])
        self.assertEqual(r['configuration_sha256'],adapter.CONFIG_SHA)
        forged=copy.deepcopy(r);forged['live_model_digest']='forged';self.assertFalse(h.verify_acquisition('a',forged))
    def test_10_cross_invocation_swap_invalid(self):
        h=self.host(two=True);self.run_one(h,'a');self.run_one(h,'b');a=self.linked(h,'a');b=self.linked(h,'b')
        self.assertFalse(h.verify_acquisition('b',a))
        swapped=copy.deepcopy(b);swapped['calls']=a['calls'];swapped['result_sha256']=a['result_sha256']
        self.assertFalse(h.verify_acquisition('b',swapped));self.assertEqual(len(self.delegate.calls),6)
    def test_11_consumed_invocation_no_new_delegate(self):
        h=self.host();self.run_one(h);r=self.linked(h)
        with self.assertRaisesRegex(ValueError,'unused'):self.run_one(h)
        self.assertEqual(len(self.delegate.calls),3);self.assertEqual(h.acquisition_receipt('a'),r)
    def test_12_default_transport_live_mode_refused(self):
        p=plan();p['live_dispatch_allowed']=True
        with self.assertRaisesRegex(ValueError,'inactive'):adapter.prepare_acquisition(encoded(p),self.root/'live',transport_delegate=MemoryDelegate())
        with self.assertRaisesRegex(ValueError,'in-memory'):adapter.prepare_acquisition(encoded(plan()),self.root/'default',transport_delegate=urllib.request.urlopen)
        self.assertFalse((self.root/'live').exists());self.assertFalse((self.root/'default').exists())
