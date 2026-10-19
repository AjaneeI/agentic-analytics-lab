"""NEW synthetic controls only. Never imports the benchmark/runtime/scorer."""
import copy
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import verifier as v
except ModuleNotFoundError as error:
    if error.name != "verifier":
        raise
    # Explicit declining baseline; meaningful assertions fail before implementation.
    v = SimpleNamespace(
        capture=lambda **kw: SimpleNamespace(**kw),
        binding=lambda capture: {},
        verify=lambda *a, **kw: {"status": "insufficient", "reason": "not_implemented"},
    )

SQL = "SELECT team, 100.0 * SUM(blocked) / COUNT(*) AS blocked_pct FROM delivery_work_items WHERE status != 'done' GROUP BY team ORDER BY blocked_pct DESC, team ASC LIMIT 1"
CONFIG = {"version": "synthetic-d01-fixture-v1", "task_id":"SB-D01", "source_commit": "a" * 40, "metric": "phase3-d01-provenance-v1"}

def population():
    rows = []
    for team, blocked, total, done_blocked, done_total in [
        ("Amber", 3, 4, 0, 2), ("Birch", 2, 5, 1, 1), ("Cedar", 0, 3, 0, 0)
    ]:
        for index in range(total):
            rows.append({"id": len(rows) + 1, "team": team, "status": "todo", "blocked": int(index < blocked)})
        for index in range(done_total):
            rows.append({"id": len(rows) + 1, "team": team, "status": "done", "blocked": int(index < done_blocked)})
    return rows

def execute_fixture(sql, rows):
    """Actual bounded in-memory SQLite computation; entirely new synthetic SQL."""
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE delivery_work_items (id INTEGER, team TEXT, status TEXT, blocked INTEGER)")
        connection.executemany("INSERT INTO delivery_work_items VALUES (:id,:team,:status,:blocked)", rows)
        connection.set_progress_handler(lambda: 1, 100000)
        return [dict(row) for row in connection.execute(sql)]

class FixtureHost:
    """Test-owned resolver; unavailable to the claim under evaluation."""
    def __init__(self, sql=SQL, rows=None, call_id="call-1", **changes):
        rows = population() if rows is None else rows
        result = execute_fixture(sql, rows)
        args = dict(execution_id="exec-" + call_id, call_id=call_id, query=sql,
                    rows=result, snapshot=rows, config=CONFIG, origin="synthetic_sqlite",
                    success=True, complete=True)
        if "captured_rows" in changes:
            args["rows"] = changes.pop("captured_rows")
        args.update(changes)
        self.record = v.capture(**args)
        self.expected = v.binding(self.record)

    def resolve(self, execution_id):
        return self.record if execution_id == self.record.execution_id else None

def claim(team="Amber", rate=75, **changes):
    result = {"execution_id": "exec-call-1", "team": team, "blocked_pct": rate, "unique_winner": True}
    result.update(changes)
    return result

def check(host, response=None, expected=None):
    return v.verify(claim() if response is None else response, resolver=host,
                    expected=host.expected if expected is None else expected)

class ProvenanceControls(unittest.TestCase):
    def test_canonical_successful_computation_proves_fixture_only(self):
        result = check(FixtureHost())
        self.assertEqual(result["status"], "proven")
        self.assertEqual(result["winners"], ["Amber"])
        self.assertFalse(result["live_qualified"])

    def test_supported_equivalent_predicates_and_table_aliases(self):
        for predicate in ["w.status <> 'done'", "NOT (w.status = 'done')", "'done' != w.status", "w.status NOT IN ('done')", "((w.status != 'done'))"]:
            sql = SQL.replace("FROM delivery_work_items", "FROM delivery_work_items AS w").replace("status != 'done'", predicate)
            with self.subTest(predicate=predicate):
                self.assertEqual(check(FixtureHost(sql))["status"], "proven")

    def test_projection_and_aggregate_ctes_and_metric_aliases(self):
        queries = [
            "WITH active AS (SELECT team, blocked FROM delivery_work_items WHERE status != 'done') SELECT team, SUM(blocked) * 100.0 / COUNT(*) AS rate FROM active GROUP BY team ORDER BY rate DESC LIMIT 1",
            "WITH counts AS (SELECT team, SUM(blocked) AS b, COUNT(*) AS n FROM delivery_work_items WHERE status != 'done' GROUP BY team) SELECT team, 100.0*b/n AS rate FROM counts ORDER BY rate DESC LIMIT 1",
            "WITH projected AS (SELECT team AS squad, blocked AS flag, status AS state FROM delivery_work_items), active AS (SELECT squad, flag FROM projected WHERE state <> 'done') SELECT squad AS team, 100.0*AVG(flag) AS rate FROM active GROUP BY squad ORDER BY rate DESC LIMIT 1",
        ]
        for sql in queries:
            with self.subTest(sql=sql):
                self.assertEqual(check(FixtureHost(sql))["status"], "proven")

    def test_full_results_and_case_numerator(self):
        queries = [SQL.split(" ORDER BY")[0], SQL.split(" ORDER BY")[0]+" LIMIT 3", SQL.replace("SUM(blocked)", "SUM(CASE WHEN blocked = 1 THEN 1 ELSE 0 END)")]
        for sql in queries:
            with self.subTest(sql=sql):
                self.assertEqual(check(FixtureHost(sql))["status"], "proven")

    def test_literal_decorative_aggregate_and_wrong_denominator_do_not_prove(self):
        for expression in ["75.0", "75.0 + 0*SUM(blocked)", "SUM(blocked)*0 + 75.0", "100.0*COUNT(*)/SUM(blocked)", "100.0*SUM(blocked)/SUM(blocked)", "CASE WHEN 1=1 THEN 75.0 ELSE SUM(blocked) END"]:
            sql = SQL.replace("100.0 * SUM(blocked) / COUNT(*)", expression)
            with self.subTest(expression=expression):
                self.assertEqual(check(FixtureHost(sql))["status"], "contradicted")

    def test_literal_team_and_alias_shadowing_are_not_team_lineage(self):
        for sql in [SQL.replace("SELECT team,", "SELECT 'Amber' AS team,"), SQL.replace("AS blocked_pct", "AS status").replace("ORDER BY blocked_pct", "ORDER BY status")]:
            with self.subTest(sql=sql):
                self.assertNotEqual(check(FixtureHost(sql))["status"], "proven")

    def test_wrong_population_and_handpicked_team_do_not_prove(self):
        for predicate in ["status != 'Done'", "status != 'done' AND team='Amber'", "status='done'", "status!='done' OR 1=1"]:
            sql = SQL.replace("status != 'done'", predicate)
            with self.subTest(predicate=predicate):
                self.assertEqual(check(FixtureHost(sql))["status"], "contradicted")

    def test_wrong_ranking_and_preaggregation_limit_do_not_prove(self):
        for sql in [SQL.replace("blocked_pct DESC", "blocked_pct ASC"), SQL.replace("ORDER BY blocked_pct DESC, team ASC", "ORDER BY team DESC"), "WITH cut AS (SELECT team, blocked, status FROM delivery_work_items LIMIT 4) SELECT team, 100.0*SUM(blocked)/COUNT(*) AS blocked_pct FROM cut WHERE status!='done' GROUP BY team"]:
            with self.subTest(sql=sql):
                self.assertNotEqual(check(FixtureHost(sql))["status"], "proven")

    def test_unsupported_valid_sql_stays_insufficient(self):
        sql = SQL.replace("SUM(blocked)", "TOTAL(blocked)")
        self.assertEqual(check(FixtureHost(sql))["status"], "insufficient")

    def test_unsupported_equivalent_predicate_does_not_become_false(self):
        sql=SQL.replace("status != 'done'", "NOT NOT (status != 'done')")
        self.assertEqual(check(FixtureHost(sql))["status"], "insufficient")
        sql="WITH cut AS (SELECT team, blocked, status FROM delivery_work_items LIMIT 1000) SELECT team, 100.0*SUM(blocked)/COUNT(*) AS rate FROM cut WHERE status!='done' GROUP BY team"
        self.assertEqual(check(FixtureHost(sql))["status"], "insufficient")

    def test_malformed_result_and_stale_host_identity_do_not_crash_or_prove(self):
        for rows in [[{"team":[],"blocked_pct":75}], [{"team":None,"blocked_pct":75}], [None]]:
            self.assertEqual(check(FixtureHost(captured_rows=rows))["status"], "contradicted")
        first=FixtureHost();second=FixtureHost()
        self.assertEqual(check(second,expected=first.expected)["status"], "contradicted")

    def test_untrusted_dict_missing_failed_and_incomplete_capture(self):
        host = FixtureHost()
        for resolver in [None, {"origin": "host", "record": host.record}]:
            self.assertEqual(v.verify(claim(), resolver=resolver, expected=host.expected)["status"], "insufficient")
        for kw in [{"success": False}, {"complete": False}, {"origin": "agent"}, {"origin": "live_host"}]:
            with self.subTest(kw=kw):
                self.assertEqual(check(FixtureHost(**kw))["status"], "insufficient")

    def test_independent_binding_mismatch_and_stale_call(self):
        host = FixtureHost()
        for field in ["query_sha256", "result_sha256", "snapshot_sha256", "config_sha256", "source_commit", "call_id", "execution_id", "metric_version", "task_id"]:
            expected = dict(host.expected)
            expected[field] = "wrong"
            with self.subTest(field=field):
                self.assertEqual(check(host, expected=expected)["status"], "contradicted")
        self.assertEqual(check(host, claim(execution_id="exec-call-2"))["status"], "insufficient")

    def test_missing_metadata_cannot_be_self_consistently_hash_pinned(self):
        for change in [{"query":None},{"call_id":""},{"config":dict(CONFIG,source_commit=None)}, {"config":dict(CONFIG,task_id="SB-A01")}]:
            host=FixtureHost()
            args=dict(execution_id="exec-call-1",call_id="call-1",query=SQL,rows=[{"team":"Amber","blocked_pct":75}],snapshot=population(),config=CONFIG,origin="synthetic_sqlite",success=True,complete=True)
            args.update(change)
            host.record=v.capture(**args)
            # Expected identity can exist without complete valid commitments.
            expected={"capture_ref":host.record}
            try:
                expected=v.binding(host.record)
            except (TypeError,AttributeError):
                pass
            self.assertNotEqual(check(host,expected=expected)["status"],"proven")

    def test_capture_deep_copies_mutable_inputs(self):
        rows = population()
        host = FixtureHost(rows=rows)
        rows[0]["blocked"] = 0
        self.assertEqual(check(host)["status"], "proven")

    def test_fabricated_result_or_changed_claim_is_contradicted(self):
        for kw in [{"captured_rows": [{"team": "Amber", "blocked_pct": 76}]}, {"captured_rows": [{"team": "Amber", "blocked_pct": 75}, {"team": "Amber", "blocked_pct": 75}]}]:
            self.assertEqual(check(FixtureHost(**kw))["status"], "contradicted")
        host = FixtureHost()
        for response in [claim("Birch",40), claim(rate=74.7), claim(rate=float("nan")), claim(rate=True), claim(rate="75")]:
            self.assertEqual(check(host,response)["status"], "contradicted")
        self.assertEqual(check(host,claim(rate=74.8))["status"], "proven")

    def test_row_permutation_renaming_completed_and_duplication_invariants(self):
        rows = population()
        variants = [list(reversed(rows)), rows + [{"id":100,"team":"OnlyDone","status":"done","blocked":1}], rows + [dict(row,id=row["id"]+100) for row in rows]]
        for variant in variants:
            self.assertEqual(check(FixtureHost(rows=variant))["status"], "proven")
        renamed = [dict(row,team={"Amber":"Zulu","Birch":"Able","Cedar":"Mango"}[row["team"]]) for row in rows]
        self.assertEqual(check(FixtureHost(rows=renamed),claim("Zulu"))["status"], "proven")

    def test_active_mutations_and_competitor_flip_change_claim(self):
        for team, blocked, count, winner, rate in [("Amber",1,1,"Amber",80),("Amber",0,1,"Amber",60),("Birch",1,8,"Birch",1000/13)]:
            rows = population()+[{"id":100+i,"team":team,"status":"todo","blocked":blocked} for i in range(count)]
            host = FixtureHost(rows=rows)
            self.assertEqual(check(host,claim(winner,rate))["status"], "proven")
            self.assertEqual(check(host)["status"], "contradicted")

    def test_exact_ties_and_rounded_near_ties(self):
        rows = population()+[{"id":100+i,"team":"Birch","status":"todo","blocked":1} for i in range(7)]
        host=FixtureHost(rows=rows)
        self.assertEqual(check(host)["status"], "contradicted")
        result=check(host,claim(unique_winner=False))
        self.assertEqual(result["status"], "proven")
        self.assertEqual(result["winners"],["Amber","Birch"])
        near=[]
        for team,b,n in [("Low",97,129),("High",94,125)]:
            near.extend({"id":len(near)+i+1,"team":team,"status":"todo","blocked":int(i<b)} for i in range(n))
        host=FixtureHost(rows=near)
        self.assertEqual(check(host,claim("High",75.2))["status"], "proven")
        self.assertEqual(check(host,claim("Low",75.2))["status"], "contradicted")

    def test_empty_and_invalid_snapshots_do_not_turn_into_zero(self):
        for rows in [[], [dict(r,status="done") for r in population()]]:
            self.assertEqual(check(FixtureHost(rows=rows))["status"], "insufficient")
        for field,value in [("status",None),("blocked",2),("blocked",True),("team",None)]:
            rows=population();rows[0][field]=value
            self.assertEqual(check(FixtureHost(rows=rows))["status"], "insufficient")
        rows=population();rows[1]["id"]=rows[0]["id"]
        self.assertEqual(check(FixtureHost(rows=rows))["status"], "insufficient")

    def test_zero_rate_and_single_team_are_distinct_from_empty(self):
        rows=[{"id":1,"team":"Only","status":"todo","blocked":0}]
        self.assertEqual(check(FixtureHost(rows=rows),claim("Only",0))["status"], "proven")

    def test_cancellation_cannot_hide_wrong_denominator_or_ungrouped_column(self):
        # Both groups have positive blocked totals; value coincidence must not
        # validate denominators that fail on legitimate zero-blocked populations.
        rows=[r for r in population() if r["team"]!="Cedar"]
        for suffix in [" * SUM(blocked) / SUM(blocked)", " * blocked / blocked"]:
            sql=SQL.replace(" AS blocked_pct", suffix+" AS blocked_pct")
            self.assertNotEqual(check(FixtureHost(sql,rows=rows))["status"],"proven")

if __name__ == "__main__":
    unittest.main()
