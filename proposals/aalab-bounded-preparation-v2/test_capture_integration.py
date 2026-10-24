"""New synthetic capture controls; no task answers or benchmark execution."""
from copy import copy, deepcopy
from dataclasses import replace
import json
import sqlite3
import unittest

from integrated_capture import SyntheticCaptureSession, CaptureLimitError, verifier
try:
    from integrated_capture import assess_answer
except ImportError:
    def assess_answer(*args,**kwargs):
        return {"status":"insufficient","reason":"integration_missing","live_qualified":False}

CONFIG = {"version": "aalab-v2-new-synthetic-captures", "task_id": "SB-D01",
          "source_commit": "a0bfc5ed3c855b917294003c1f38617e0c29782a",
          "metric": verifier.VERSION if hasattr(verifier, "VERSION") else "phase3-d01-provenance-v1"}
SQL = "SELECT team,100.0*SUM(blocked)/COUNT(*) AS rate FROM delivery_work_items WHERE status!='done' GROUP BY team ORDER BY rate DESC LIMIT 1"

def snapshot(spec=(("Nacre", 2, 5), ("Umber", 3, 4), ("Rowan", 0, 2))):
    rows = []
    for team, blocked, total in spec:
        for i in range(total):
            rows.append({"id": len(rows)+1, "team": team, "status": "todo", "blocked": int(i < blocked)})
    rows.append({"id": len(rows)+1, "team": "Nacre", "status": "done", "blocked": 1})
    return rows

def claim(call, team="Umber", rate=75, unique=True, **extra):
    return {"execution_id": call.execution_id, "team": team, "blocked_pct": rate,
            "unique_winner": unique, **extra}

class CaptureIntegrationControls(unittest.TestCase):
    def test_final_answer_is_checked_against_same_proven_capture_not_claim_value(self):
        with SyntheticCaptureSession(snapshot(),CONFIG) as h:
            h.query(SQL); token=h.calls[0]
            for text,status in (
                ("Umber has the highest blocker rate at 75% among active work items.","proven"),
                ("Nacre has the highest blocker rate at 75% among active work items.","contradicted"),
                ("Umber has the highest blocker rate at 75.3% among active work items.","contradicted"),
                ("Umber has the highest blocker rate at 75% among all work items.","contradicted"),
                ("Blocker rate is blocked active work divided by all active work in the selected scope, multiplied by 100.","insufficient"),
                ("Umber has the highest blocker rate at 75% among active work items. Freeform unknown suffix.","insufficient")):
                with self.subTest(text=text):
                    v=assess_answer(h,claim(token),text,call=token,policy_context={})
                    self.assertEqual(v["status"],status);self.assertFalse(v["live_qualified"])
            self.assertEqual(len(h.calls),1)

    def test_exact_host_ratio_prevents_tolerance_accumulation(self):
        with SyntheticCaptureSession(snapshot((("Umber",1,3),("Nacre",0,2))),CONFIG) as h:
            h.query(SQL); token=h.calls[0]
            for rate,status in (("33.53333333","proven"),("33.53333334","contradicted")):
                text="Umber has the highest blocker rate at "+rate+"% among active work items."
                v=assess_answer(h,claim(token,rate=33.5),text,call=token,policy_context={})
                self.assertEqual(v["status"],status)

    def test_actual_rows_and_exact_selected_capture(self):
        with SyntheticCaptureSession(snapshot(), CONFIG) as h:
            self.assertEqual(h.query(SQL), [{"team": "Umber", "rate": 75.0}])
            v = h.verify(claim(h.calls[0]), call=h.calls[0])
            self.assertEqual(v["status"], "proven")
            self.assertFalse(v["live_qualified"])
            self.assertEqual((v["numerator"], v["denominator"]), (3, 4))
            self.assertEqual(h.events[0].execute_attempts, 1)

    def test_equivalent_sql_qualified_table_cte_and_average(self):
        variants = [SQL.replace("100.0*SUM(blocked)/COUNT(*)", "100.0*AVG(blocked)"),
                    SQL.replace("FROM delivery_work_items", "FROM agentic_analytics.delivery_work_items"),
                    "WITH source AS (SELECT team,blocked FROM delivery_work_items WHERE status!='done') SELECT team,100.0*SUM(blocked)/COUNT(*) AS rate FROM source GROUP BY team ORDER BY rate DESC LIMIT 1"]
        for sql in variants:
            with self.subTest(sql=sql), SyntheticCaptureSession(snapshot(), CONFIG) as h:
                h.query(sql)
                self.assertEqual(h.verify(claim(h.calls[0]), call=h.calls[0])["status"], "proven")

    def test_unspecified_exact_tie_uses_actual_peer_without_false_rejection(self):
        with SyntheticCaptureSession(snapshot((("Nacre",1,1),("Umber",1,1))), CONFIG) as h:
            rows = h.query(SQL)
            self.assertEqual(rows, [{"team":"Umber", "rate":100.0}])
            c = claim(h.calls[0], team="Umber", rate=100, unique=False)
            self.assertEqual(h.verify(c, call=h.calls[0])["status"], "proven")
            self.assertEqual(h.verify(dict(c, unique_winner=True), call=h.calls[0])["status"], "contradicted")

    def test_secondary_order_and_exact_unrounded_winner_remain_binding(self):
        for direction, team in (("ASC","Nacre"),("DESC","Umber")):
            with self.subTest(direction=direction), SyntheticCaptureSession(snapshot((("Nacre",1,1),("Umber",1,1))), CONFIG) as h:
                rows = h.query(SQL.replace("rate DESC LIMIT", "rate DESC, team "+direction+" LIMIT"))
                self.assertEqual(rows[0]["team"], team)
                self.assertEqual(h.verify(claim(h.calls[0], team,100,False),call=h.calls[0])["status"], "proven")
        with SyntheticCaptureSession(snapshot((("Nacre",97,129),("Umber",94,125))), CONFIG) as h:
            h.query(SQL)
            self.assertEqual(h.verify(claim(h.calls[0],rate=75.2),call=h.calls[0])["status"],"proven")
            self.assertEqual(h.verify(claim(h.calls[0],team="Nacre",rate=75.2),call=h.calls[0])["status"],"contradicted")

    def test_two_calls_need_explicit_selection_no_favorable_fallback(self):
        with SyntheticCaptureSession(snapshot(), CONFIG) as h:
            h.query(SQL); first = h.calls[0]
            h.query(SQL.replace("100.0*SUM(blocked)/COUNT(*)", "75.0")); second = h.calls[1]
            self.assertEqual(h.verify(claim(first))["reason"], "explicit_call_required")
            self.assertEqual(h.verify(claim(second),call=second)["status"], "contradicted")
            self.assertEqual(h.verify(claim(first),call=second)["status"], "contradicted")
            self.assertEqual(h.verify(claim(first),call=first)["status"], "proven")
            with self.assertRaises(CaptureLimitError): h.query(SQL)
            self.assertEqual([e.execute_attempts for e in h.events], [1,1,0])

    def test_cross_session_forged_tokens_and_claim_context_cannot_replace_host(self):
        with SyntheticCaptureSession(snapshot(),CONFIG) as a, SyntheticCaptureSession(snapshot(),CONFIG) as b:
            a.query(SQL); b.query(SQL); token = a.calls[0]
            for fake in (token, copy(b.calls[0]), {"execution_id": b.calls[0].execution_id}):
                with self.subTest(fake=fake):
                    self.assertEqual(b.verify(claim(token),call=fake)["reason"], "untrusted_call_token")
            bad = claim(token,execution_id="forged",resolver=a,expected={"capture_ref":"fake"})
            self.assertEqual(a.verify(bad,call=token)["status"],"insufficient")
            self.assertIsNone(a.resolve("forged"))

    def test_host_binding_mutation_is_rejected(self):
        with SyntheticCaptureSession(snapshot(),CONFIG) as h:
            h.query(SQL); token = h.calls[0]; context = h.verification_context(token)
            for field in ("query_sha256","result_sha256","snapshot_sha256","config_sha256","source_commit","contract_sha256","call_id"):
                expected = dict(context["expected"], **{field:"changed"})
                with self.subTest(field=field):
                    self.assertEqual(verifier.verify(claim(token),resolver=h,expected=expected)["status"],"contradicted")
            context["expected"]["query_sha256"] = "caller copy changed"
            self.assertEqual(h.verify(claim(token),call=token)["status"],"proven")

    def test_inputs_and_returned_rows_cannot_rewrite_bound_capture(self):
        rows = snapshot(); config = deepcopy(CONFIG)
        with SyntheticCaptureSession(rows,config) as h:
            rows[0]["blocked"]=1; config["task_id"]="forged"
            result=h.query(SQL); result[0]["rate"]=0
            self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[0])["status"],"proven")
            record=h.resolve(h.calls[0].execution_id)
            self.assertEqual(json.loads(record.result_json),[{"team":"Umber","rate":75.0}])
            self.assertEqual(json.loads(record.config_json)["task_id"],"SB-D01")

    def test_failed_execution_preserved_once_without_retry(self):
        with SyntheticCaptureSession(snapshot(),CONFIG) as h:
            with self.assertRaises(sqlite3.Error): h.query("SELECT absent FROM delivery_work_items")
            token=h.calls[0]; event=h.events[0]
            self.assertEqual((event.execute_attempts,event.success,event.complete),(1,False,False))
            self.assertEqual(h.verify(claim(token),call=token)["reason"],"execution_not_successful")
            self.assertEqual(len(h.calls),1)

    def test_incomplete_collection_never_proves(self):
        rows=snapshot((("Nacre",0,1001),))
        with SyntheticCaptureSession(rows,CONFIG) as h:
            with self.assertRaises(CaptureLimitError): h.query("SELECT id FROM delivery_work_items")
            record=h.resolve(h.calls[0].execution_id)
            self.assertFalse(record.complete)
            self.assertEqual(len(json.loads(record.result_json)),1000)
            self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[0])["status"],"insufficient")

    def test_unknown_valid_sql_remains_insufficient(self):
        with SyntheticCaptureSession(snapshot(),CONFIG) as h:
            h.query(SQL + " -- synthetically authored unsupported comment")
            self.assertEqual(h.verify(claim(h.calls[0]),call=h.calls[0])["reason"],"unsupported_sql")

    def test_invalid_unicode_no_partial_registry_and_security_denial_preserved(self):
        with SyntheticCaptureSession(snapshot(),CONFIG) as h:
            with self.assertRaises(UnicodeEncodeError): h.query("\ud800")
            self.assertEqual(h.calls,())
            self.assertEqual(h.events[0].execute_attempts,0)
            with self.assertRaises(sqlite3.Error): h.query("SELECT name FROM sqlite_master")
            self.assertFalse(h.events[-1].success)

if __name__ == "__main__": unittest.main()
