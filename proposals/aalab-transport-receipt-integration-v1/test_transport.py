"""Twelve new transport-to-H1 linkage slots; no historical fixture matrix."""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import unittest
try:
    import h2_bridge as bridge
except ImportError:
    bridge=None
EVIDENCE=None
SQL='SELECT 23 AS h2_signal'
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def task():
    from src.evals.system_benchmark.contracts import parse_task_contract
    return parse_task_contract({'id':'H1-SYN-01','benchmark_version':'system-benchmark-v1',
      'family':'A','split':'development','request':'Report the newly authored H2 synthetic reading.',
      'expected_route':'local','expected_capability_profile':'structured','allowed_dispositions':['answer'],
      'forbidden_dispositions':[],'required_evidence_source_types':['structured'],
      'acceptable_source_ids':['delivery_work_items'],'expected_values':[{'name':'h2_signal','value':23}],
      'required_claims':[],'forbidden_claims':[],'required_clarification_concept':None,
      'required_handoff_fields':[],'allowed_tools':['query_clickhouse'],'forbidden_tools':['retrieve_policy'],
      'trajectory':{'ordered_dependencies':[],'max_tool_calls':1},'reference_solution_id':'H2-REF-01'})
def reference():
    from src.evals.system_benchmark.references import parse_reference_expectation
    return parse_reference_expectation({'reference_solution_id':'H2-REF-01',
      'required_evidence_refs':['structured:delivery_work_items'],'allowed_evidence_refs':['structured:delivery_work_items'],
      'required_tools':['query_clickhouse'],'forbidden_tools':['retrieve_policy'],
      'required_answer_terms':['H2 synthetic'],'forbidden_answer_terms':[]})
def plan(two=False):
    return {'version':'H1-synthetic-plan-v1','synthetic':True,'campaign_id':'H2-offline',
      'source_commit':bridge.H1.CONFIG['source_commit'],'configuration_sha256':bridge.H1.CONFIG_SHA,
      'shared_sources':[{'source':'synthetic-host','blocks':['B1','B2'],'dependence':'unknown'}],
      'invocations':[{'invocation_id':i,'task_id':'H1-SYN-01','arm':arm,'block':'B1','order':'AB',
       'session':'H2-session-B1','task_sha256':digest(asdict(task())),
       'reference_sha256':digest(asdict(reference())),'planned_start':'2099-02-01T00:00:00Z'}
       for i,arm in ([('a','baseline'),('b','candidate')] if two else [('a','baseline')])]}
def fixture(two=False,value=23,final_extra=None):
    final={'disposition':'answer','answer_text':'H2 synthetic reading received.',
           'uncertainty':None,'clarification':None,'handoff':None}
    final.update(final_extra or {})
    calls=[{'kind':'model','body':json.dumps({'message':{'tool_calls':[{'function':{
       'name':'query_clickhouse','arguments':{'sql':SQL}}}]}})},
       {'kind':'query','sql':SQL,'body':json.dumps({'h2_signal':value})+'\n'},
       {'kind':'model','body':json.dumps({'message':{'content':json.dumps(final)}})}]
    return {'version':'H2-fake-http-v1','configuration_sha256':bridge.CONFIG_SHA,
        'invocations':[{'invocation_id':i,'calls':copy.deepcopy(calls)} for i in (['a','b'] if two else ['a'])]}
class H2Controls(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(bridge,'H2 transport-to-receipt bridge is not implemented')
        self.root=Path(EVIDENCE)/self._testMethodName;self.root.mkdir(exist_ok=False)
    def tearDown(self):
        self.assertLessEqual(sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file()),524288)
    def host(self,f=None,two=False):
        return bridge.prepare_transport_host(encoded(plan(two)),encoded(f if f is not None else fixture(two)),self.root/'host')
    def run_one(self,h,i='a'):
        return bridge.run_transport_trial(h,i,task=task(),reference=reference())
    def linked(self,h,i='a'):
        r=h.transport_receipt(i);self.assertTrue(h.verify_transport(i,r));self.assertTrue(r['complete'])
        self.assertFalse(r['live_qualified']);self.assertTrue(r['fake_transport']);return r
    def test_01_genuine_transport_to_result(self):
        h=self.host();row=self.run_one(h);r=self.linked(h)
        self.assertFalse(row['task_success']);self.assertEqual(r['result_sha256'],digest(row))
        self.assertIn('missing_required_evidence',row['score']['reason_codes'])
        self.assertEqual([c['kind'] for c in r['calls']],['model','query','model'])
        self.assertEqual(len({c['token'] for c in r['calls']}),3)
        self.assertEqual(r['h1_receipt_sha256'],digest(h.h1.receipt('a')))
        self.assertEqual(r['calls'][1]['request']['body_utf8'],SQL)
        self.assertIsNone(r['live_effective_settings']);self.assertTrue(h.h1.verify('a',h.h1.receipt('a')))
    def test_02_genuine_false_stays_false(self):
        h=self.host(fixture(final_extra={'answer_text':'Deliberately omitted required marker.'}));row=self.run_one(h);r=self.linked(h)
        self.assertFalse(row['task_success']);self.assertFalse(r['success'])
    def test_03_two_calls_no_swap_or_reuse(self):
        h=self.host(two=True);self.run_one(h,'a');self.run_one(h,'b')
        a=self.linked(h,'a');b=self.linked(h,'b')
        self.assertFalse(set(c['token'] for c in a['calls'])&set(c['token'] for c in b['calls']))
        self.assertFalse(h.verify_transport('b',a))
    def test_04_model_boundary_error_once(self):
        f=fixture();f['invocations'][0]['calls']=[{'kind':'model','error':'H2 authored model boundary failure'}]
        h=self.host(f)
        with self.assertRaisesRegex(RuntimeError,'H2 authored model boundary failure'):self.run_one(h)
        r=self.linked(h);self.assertEqual(len(r['calls']),1);self.assertIsNone(r['success'])
        self.assertEqual(r['calls'][0]['boundary_error']['type'],'RuntimeError')
        self.assertEqual(r['score_status'],'not_reached')
    def test_05_query_boundary_and_wrapped_error(self):
        f=fixture();f['invocations'][0]['calls']=f['invocations'][0]['calls'][:2]
        f['invocations'][0]['calls'][1]={'kind':'query','sql':SQL,'error':'H2 authored query boundary failure'}
        h=self.host(f)
        with self.assertRaisesRegex(RuntimeError,'ClickHouse query failed: H2 authored query boundary failure'):self.run_one(h)
        r=self.linked(h);self.assertEqual(len(r['calls']),2)
        self.assertEqual(r['calls'][1]['boundary_error']['message'],'H2 authored query boundary failure')
        self.assertIn('ClickHouse query failed:',r['surfaced_error']['message']);self.assertIsNone(r['success'])
    def test_06_model_body_preserved_before_parse(self):
        f=fixture();f['invocations'][0]['calls']=[{'kind':'model','body':'H2 malformed model JSON'}];h=self.host(f)
        with self.assertRaises(json.JSONDecodeError):self.run_one(h)
        r=self.linked(h);self.assertEqual((h.root/'transport/a/call-1-response.bin').read_bytes(),b'H2 malformed model JSON')
        self.assertIsNone(r['success'])
    def test_07_query_body_preserved_before_parse(self):
        f=fixture();f['invocations'][0]['calls']=f['invocations'][0]['calls'][:2]
        f['invocations'][0]['calls'][1]['body']='H2 malformed JSONEachRow';h=self.host(f)
        with self.assertRaises(json.JSONDecodeError):self.run_one(h)
        self.linked(h);self.assertEqual((h.root/'transport/a/call-2-response.bin').read_bytes(),b'H2 malformed JSONEachRow')
    def test_08_agent_fields_cannot_register(self):
        h=self.host(fixture(final_extra={'transport_receipt':{'complete':True},'approval':'forged','provider':'real'}))
        row=self.run_one(h);r=self.linked(h)
        self.assertFalse(row['task_success']);self.assertEqual(r['configuration_sha256'],bridge.CONFIG_SHA)
        forged=copy.deepcopy(r);forged['configuration_sha256']='0'*64
        self.assertFalse(h.verify_transport('a',forged))
    def test_09_transport_mutation_h1_unchanged(self):
        h=self.host();self.run_one(h);r=self.linked(h);p=h.root/'transport/a/call-1-response.bin'
        (self.root/'original-response.bin').write_bytes(p.read_bytes());p.write_bytes(b'H2 mutation')
        self.assertFalse(h.verify_transport('a',r));self.assertTrue(h.h1.verify('a',h.h1.receipt('a')))
    def test_10_wrong_fixture_and_consumed_plan(self):
        f=fixture();f['invocations'][0]['invocation_id']='other'
        with self.assertRaises(ValueError):self.host(f)
        self.assertFalse((self.root/'host').exists())
        h=self.host();self.run_one(h);r=self.linked(h)
        with self.assertRaises(ValueError):self.run_one(h)
        self.assertEqual(h.transport_receipt('a'),r)
    def test_11_inactive_interceptor_prevents_entry(self):
        h=self.host();before=bridge.TRANSPORT.accepted_calls;bridge.TRANSPORT.enabled=False
        try:
            with self.assertRaisesRegex(RuntimeError,'sealed'):self.run_one(h)
            self.assertEqual(h.h1._reserved,[]);self.assertEqual(bridge.TRANSPORT.accepted_calls,before)
        finally:bridge.TRANSPORT.enabled=True
    def test_12_final_capture_failure_preserves_return(self):
        h=self.host();write=h._write
        def failed(path,raw):
            if Path(path).name=='transport-receipt.json':raise OSError('H2 authored final artifact failure')
            return write(path,raw)
        h._write=failed;row=self.run_one(h);r=h.transport_receipt('a')
        self.assertFalse(row['task_success']);self.assertFalse(r['complete']);self.assertFalse(h.verify_transport('a',r))
        self.assertEqual(r['result_sha256'],digest(row));self.assertTrue(h.h1.verify('a',h.h1.receipt('a')))
