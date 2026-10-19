"""New synthetic behavioral controls; no frozen task, runtime or dataset import."""
from dataclasses import replace
from pathlib import Path
import copy
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from capture_adapter import SyntheticCaptureSession, CaptureLimitError
except ModuleNotFoundError as error:
    if error.name != 'capture_adapter':
        raise
    CaptureLimitError = RuntimeError
    class SyntheticCaptureSession:
        """Explicit declining baseline; assertions demonstrate missing behavior."""
        def __init__(self, rows, config): self.calls = []; self.events = []
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def query(self, sql):
            self.calls.append(SimpleNamespace(execution_id='absent', call_id='absent'))
            return []
        def verify(self, claim, *, call=None):
            return {'status':'insufficient','reason':'not_implemented','live_qualified':False}
        def verification_context(self, call): return {'resolver':self,'expected':{}}
        def resolve(self, key): return None

BASE = '42befe12de7d4c8cf5813a99cb32b7f3eb7c25dd'
CONFIG = {'version':'synthetic-capture-fixture-v1','task_id':'SB-D01',
          'source_commit':BASE,'metric':'phase3-d01-provenance-v1'}
SQL = "SELECT team, 100.0*SUM(blocked)/COUNT(*) AS blocked_pct FROM delivery_work_items WHERE status!='done' GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"

def fixture():
    """Hand counts: Dune3/5=60, Elm1/4=25, Fern0/2=0; done rows excluded."""
    rows=[]
    for team,total,blocked in [('Dune',5,3),('Elm',4,1),('Fern',2,0)]:
        for i in range(total):
            rows.append({'id':len(rows)+1,'team':team,'status':'todo','blocked':int(i<blocked)})
    rows += [{'id':12,'team':'Dune','status':'done','blocked':1},
             {'id':13,'team':'Dune','status':'done','blocked':0}]
    return rows

def claim(call, **changes):
    result={'execution_id':call.execution_id,'team':'Dune','blocked_pct':60,'unique_winner':True}
    result.update(changes)
    return result

class CaptureControls(unittest.TestCase):
    def test_callback_returns_only_actual_rows_and_proves_selected_capture(self):
        with SyntheticCaptureSession(fixture(), CONFIG) as host:
            rows=host.query(SQL)
            self.assertEqual(rows,[{'team':'Dune','blocked_pct':60.0}])
            self.assertEqual(len(host.calls),1)
            verdict=host.verify(claim(host.calls[0]),call=host.calls[0])
            self.assertEqual(verdict['status'],'proven')
            self.assertFalse(verdict['live_qualified'])

    def test_equivalent_cte_and_avg_keep_semantic_proof(self):
        queries=[SQL.replace('100.0*SUM(blocked)/COUNT(*)','100.0*AVG(blocked)'),
                 SQL.replace('FROM delivery_work_items','FROM agentic_analytics.delivery_work_items'),
                 "WITH a AS (SELECT team, blocked FROM delivery_work_items WHERE status!='done') SELECT team,100.0*SUM(blocked)/COUNT(*) AS blocked_pct FROM a GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"]
        for sql in queries:
            with self.subTest(sql=sql), SyntheticCaptureSession(fixture(),CONFIG) as h:
                h.query(sql);self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[0])['status'],'proven')

    def test_no_implicit_or_favorable_call_selection(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            h.query(SQL);first=h.calls[0]
            h.query(SQL.replace('100.0*SUM(blocked)/COUNT(*)','60.0'));second=h.calls[1]
            self.assertEqual(h.verify(claim(first))['reason'],'explicit_call_required')
            self.assertEqual(h.verify(claim(second),call=second)['status'],'contradicted')
            self.assertEqual(h.verify(claim(first),call=second)['status'],'contradicted')
            self.assertEqual(h.verify(claim(first),call=first)['status'],'proven')

    def test_cross_session_and_copied_tokens_cannot_select_records(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as a, SyntheticCaptureSession(fixture(),CONFIG) as b:
            a.query(SQL);b.query(SQL);token=a.calls[0]
            self.assertEqual(b.verify(claim(token),call=token)['reason'],'untrusted_call_token')
            cloned=copy.copy(token)
            self.assertEqual(a.verify(claim(token),call=cloned)['reason'],'untrusted_call_token')
            self.assertNotEqual(token.execution_id,b.calls[0].execution_id)

    def test_forged_claim_fields_cannot_register_or_replace_capture(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            h.query(SQL);call=h.calls[0]
            forged=claim(call,execution_id='forged',resolver={'rows':[{'blocked_pct':60}]},expected={'capture_ref':'forged'})
            self.assertEqual(h.verify(forged,call=call)['status'],'insufficient')
            self.assertIsNone(h.resolve('forged'))
            self.assertEqual(h.verify(claim(call),call={'execution_id':call.execution_id})['reason'],'untrusted_call_token')

    def test_mutating_returned_rows_snapshot_and_config_does_not_rewrite_capture(self):
        rows=fixture();config=copy.deepcopy(CONFIG)
        with SyntheticCaptureSession(rows,config) as h:
            rows[0]['blocked']=0;config['task_id']='forged'
            returned=h.query(SQL);call=h.calls[0]
            self.assertEqual(returned[0]['blocked_pct'],60.0)
            returned[0]['blocked_pct']=0
            self.assertEqual(h.verify(claim(call),call=call)['status'],'proven')
            self.assertEqual(h.verify(claim(call,blocked_pct=0),call=call)['status'],'contradicted')

    def test_borrowed_context_changes_cannot_overwrite_host_commitment(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            h.query(SQL);call=h.calls[0];context=h.verification_context(call)
            context['expected']['query_sha256']='0'*64
            self.assertNotEqual(h.verification_context(call)['expected']['query_sha256'],'0'*64)
            self.assertEqual(h.verify(claim(call),call=call)['status'],'proven')

    def test_original_sql_error_is_captured_once_without_retry(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            with self.assertRaises(sqlite3.OperationalError):h.query('SELECT missing FROM delivery_work_items')
            self.assertEqual(len(h.calls),1)
            self.assertEqual(h.events[0].execute_attempts,1)
            self.assertEqual(h.events[0].error_type,'OperationalError')
            self.assertFalse(h.events[0].success)
            self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[0])['reason'],'execution_not_successful')
            h.query(SQL)
            self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[1])['status'],'contradicted')

    def test_mutation_attachment_and_unrelated_reads_are_denied(self):
        for sql in ['DELETE FROM delivery_work_items',"ATTACH DATABASE ':memory:' AS extra",'SELECT name FROM sqlite_master']:
            with self.subTest(sql=sql), SyntheticCaptureSession(fixture(),CONFIG) as h:
                with self.assertRaises(sqlite3.DatabaseError):h.query(sql)
                self.assertFalse(h.events[0].success)
                self.assertEqual(h.query(SQL),[{'team':'Dune','blocked_pct':60.0}])

    def test_partial_row_capture_cannot_be_promoted_to_complete(self):
        rows=[{'id':i,'team':'Dune','status':'todo','blocked':1} for i in range(1001)]
        with SyntheticCaptureSession(rows,CONFIG) as h:
            with self.assertRaises(CaptureLimitError):h.query('SELECT id FROM delivery_work_items')
            self.assertFalse(h.events[0].complete)
            self.assertEqual(h.events[0].returned_rows,1000)
            self.assertNotEqual(h.verify(claim(h.calls[0]),call=h.calls[0])['status'],'proven')

    def test_two_call_bound_stops_before_a_third_execute(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            h.query(SQL);h.query(SQL)
            with self.assertRaises(CaptureLimitError):h.query(SQL)
            self.assertEqual(len(h.calls),2)
            self.assertEqual(sum(e.execute_attempts for e in h.events),2)
            self.assertEqual(h.events[-1].execute_attempts,0)
            self.assertEqual(h.events[-1].error_type,'CaptureLimitError')

    def test_tie_uses_captured_team_and_cannot_claim_uniqueness(self):
        rows=[{'id':i+1,'team':team,'status':'todo','blocked':1} for i,team in enumerate(['Dune','Elm'])]
        with SyntheticCaptureSession(rows,CONFIG) as h:
            result=h.query(SQL.replace('DESC LIMIT','DESC, team ASC LIMIT'));call=h.calls[0]
            response=claim(call,team=result[0]['team'],blocked_pct=100,unique_winner=False)
            self.assertEqual(h.verify(response,call=call)['status'],'proven')
            self.assertEqual(h.verify(dict(response,unique_winner=True),call=call)['reason'],'false_unique_claim')

    def test_upstream_unspecified_tie_order_gap_is_preserved_not_corrected(self):
        # Characterization, not a scientifically correct expected outcome.
        # Legitimate tied LIMIT1 without a secondary key is rejected upstream.
        rows=[{'id':i+1,'team':team,'status':'todo','blocked':1} for i,team in enumerate(['Dune','Elm'])]
        with SyntheticCaptureSession(rows,CONFIG) as h:
            result=h.query(SQL);call=h.calls[0]
            response=claim(call,team=result[0]['team'],blocked_pct=100,unique_winner=False)
            verdict=h.verify(response,call=call)
            self.assertEqual(result,[{'team':'Elm','blocked_pct':100.0}])
            self.assertEqual(verdict['reason'],'captured_result_mismatch')
            self.assertFalse(verdict['live_qualified'])

    def test_invalid_snapshot_and_config_reject_before_sqlite_creation(self):
        for rows,config in [(fixture()+[fixture()[0]],CONFIG),(fixture(),dict(CONFIG,source_commit='bad')),
                            (fixture(),dict(CONFIG,adapter_source_sha256={'capture_adapter.py':'0'*64})),
                            ([dict(fixture()[0],blocked=True)],CONFIG)]:
            with self.subTest(rows=rows[:1],config=config), self.assertRaises(ValueError):
                SyntheticCaptureSession(rows,config)

    def test_no_active_population_is_insufficient(self):
        with SyntheticCaptureSession([dict(r,status='done') for r in fixture()],CONFIG) as h:
            self.assertEqual(h.query(SQL),[]);c=h.calls[0]
            self.assertEqual(h.verify(claim(c),call=c)['reason'],'no_eligible_population')

    def test_closed_session_never_executes_a_query(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:pass
        with self.assertRaises(RuntimeError):h.query(SQL)
        self.assertEqual(len(h.calls),0)
        self.assertEqual(h.events[0].execute_attempts,0)

    def test_invalid_query_input_leaves_a_zero_execute_failure_record(self):
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            with self.assertRaises(ValueError):h.query(None)
            self.assertEqual(len(h.calls),0)
            self.assertEqual(h.events[0].error_type,'ValueError')
            self.assertEqual(h.events[0].execute_attempts,0)

    def test_expensive_new_synthetic_query_stops_once_and_session_remains_read_only(self):
        rows=[{'id':i,'team':'Dune','status':'todo','blocked':1} for i in range(1000)]
        with SyntheticCaptureSession(rows,CONFIG) as h:
            with self.assertRaises(sqlite3.OperationalError):
                h.query('SELECT COUNT(*) AS n FROM delivery_work_items a CROSS JOIN delivery_work_items b')
            self.assertEqual(h.events[0].execute_attempts,1)
            self.assertFalse(h.events[0].success)
            self.assertEqual(h.query(SQL),[{'team':'Dune','blocked_pct':100.0}])

    def test_byte_bound_preserves_bounded_prefix_without_fetching_all_rows(self):
        rows=[{'id':i,'team':'x'*3000,'status':'todo','blocked':1} for i in range(100)]
        with SyntheticCaptureSession(rows,CONFIG) as h:
            with self.assertRaises(CaptureLimitError):
                h.query('SELECT a.team AS label FROM delivery_work_items a CROSS JOIN delivery_work_items b LIMIT 1000')
            self.assertGreater(h.events[0].returned_rows,0)
            self.assertLess(h.events[0].returned_rows,1000)
            self.assertFalse(h.events[0].complete)

    def test_sqlite_value_limit_rejects_oversized_expression_before_python_capture(self):
        rows=[{'id':1,'team':'x'*200000,'status':'todo','blocked':1}]
        with SyntheticCaptureSession(rows,CONFIG) as h:
            with self.assertRaises(sqlite3.DataError):
                h.query('SELECT '+'||'.join(['team']*12)+' AS huge FROM delivery_work_items')
            self.assertEqual(h.events[0].returned_rows,0)
            self.assertEqual(h.events[0].execute_attempts,1)

    def test_invalid_utf8_query_records_denial_without_partial_registry(self):
        sql='SELECT \ud800 FROM delivery_work_items'
        with SyntheticCaptureSession(fixture(),CONFIG) as h:
            with self.assertRaises(UnicodeEncodeError):h.query(sql)
            self.assertEqual(len(h.calls),0)
            self.assertEqual(h.events[0].execute_attempts,0)
            self.assertEqual(h.events[0].error_type,'UnicodeEncodeError')
            import json
            self.assertEqual(json.loads(h.events[0].rejected_query_json),sql)
            self.assertIsNone(h.events[0].query_sha256)
            self.assertEqual(h.verify({'execution_id':'forged'},call={'id':'forged'})['status'],'insufficient')

    def test_execute_cancellation_preserves_original_error_without_retry(self):
        # Controlled fault at the slow/native boundary; all setup uses real SQLite.
        import capture_adapter
        original_connect=sqlite3.connect
        query='SELECT team FROM delivery_work_items'
        class InterruptedConnection(sqlite3.Connection):
            def execute(self,sql,*args,**kwargs):
                if sql==query:raise KeyboardInterrupt('new synthetic cancellation')
                return super().execute(sql,*args,**kwargs)
        def connect(*args,**kwargs):
            return original_connect(*args,factory=InterruptedConnection,**kwargs)
        with patch.object(capture_adapter.sqlite3,'connect',side_effect=connect):
            with SyntheticCaptureSession(fixture(),CONFIG) as h:
                with self.assertRaises(KeyboardInterrupt):h.query(query)
                self.assertEqual(len(h.calls),1)
                self.assertEqual(h.events[0].error_type,'KeyboardInterrupt')
                self.assertEqual(h.events[0].error_message,'new synthetic cancellation')
                self.assertEqual(h.events[0].execute_attempts,1)
                self.assertFalse(h.events[0].success)
                self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[0])['reason'],'execution_not_successful')

if __name__=='__main__':unittest.main(verbosity=2)
