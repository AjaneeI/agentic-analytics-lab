"""New synthetic, host-owned LIMIT-boundary controls; no benchmark inputs."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import unittest

import verifier_candidate as v

BASE='35ce571c448055aee8a2cbc6f841d17a69108d31'
CONFIG={'version':'synthetic-tie-order-fixture-v1','metric':v.VERSION,
        'task_id':'SB-D01','source_commit':BASE}
SQL="SELECT team, 100.0*SUM(blocked)/COUNT(*) AS rate FROM delivery_work_items WHERE status!='done' GROUP BY team ORDER BY rate DESC LIMIT 1"

def snapshot(spec=(('Dune',1,1),('Elm',1,1))):
    rows=[]
    for team,b,n in spec:
        offset=len(rows)
        rows.extend({'id':offset+i+1,'team':team,'status':'todo','blocked':int(i<b)} for i in range(n))
    return rows

class Host:
    """Explicit new synthetic capture; expected commitments never come from claim."""
    def __init__(self,sql=SQL,rows=None,returned=None,config=None,success=True,complete=True):
        rows=snapshot() if rows is None else rows
        with sqlite3.connect(':memory:') as conn:
            conn.row_factory=sqlite3.Row
            conn.execute('CREATE TABLE delivery_work_items(id INTEGER,team TEXT,status TEXT,blocked INTEGER)')
            conn.executemany('INSERT INTO delivery_work_items VALUES (:id,:team,:status,:blocked)',rows)
            actual=[dict(r) for r in conn.execute(sql)]
        self.actual=actual
        self.record=v.capture(execution_id='synthetic-execution',call_id='selected-call',query=sql,
            rows=actual if returned is None else returned,snapshot=rows,config=CONFIG if config is None else config,
            origin='synthetic_sqlite',success=success,complete=complete)
        self.expected=v.binding(self.record)
    def resolve(self,execution_id):
        return self.record if execution_id==self.record.execution_id else None

def check(host,team=None,rate=100,unique=False,expected=None,**changes):
    if team is None:team=host.actual[0]['team'] if host.actual else 'Dune'
    claim={'execution_id':'synthetic-execution','team':team,'blocked_pct':rate,'unique_winner':unique,**changes}
    verdict=v.verify(claim,resolver=host,expected=host.expected if expected is None else expected)
    assert verdict['live_qualified'] is False
    return verdict

class TieOrderControls(unittest.TestCase):
    def test_real_sqlite_unspecified_co_max_is_proven(self):
        h=Host();self.assertEqual(h.actual,[{'team':'Elm','rate':100.0}])
        self.assertEqual(check(h)['status'],'proven')

    def test_each_exact_peer_is_admissible_independent_of_snapshot_order(self):
        for rows in [snapshot(),list(reversed(snapshot()))]:
            for team in ['Dune','Elm']:
                with self.subTest(team=team,rows=rows):
                    h=Host(rows=rows,returned=[{'team':team,'rate':100.0}])
                    self.assertEqual(check(h,team)['status'],'proven')

    def test_secondary_team_ascending_and_descending_remain_binding(self):
        for direction,winner,other in [('ASC','Dune','Elm'),('DESC','Elm','Dune')]:
            sql=SQL.replace('rate DESC LIMIT','rate DESC, team '+direction+' LIMIT')
            self.assertEqual(check(Host(sql))['status'],'proven')
            self.assertEqual(check(Host(sql,returned=[{'team':other,'rate':100.0}]),other)['status'],'contradicted')

    def test_tertiary_key_breaks_secondary_tie(self):
        rows=snapshot((('Dune',1,1),('Elm',1,1)))
        sql=SQL.replace(' AS rate',' AS rate, COUNT(*) AS size').replace('rate DESC LIMIT','rate DESC, size ASC, team DESC LIMIT')
        self.assertEqual(check(Host(sql,rows))['status'],'proven')
        bad=[{'team':'Dune','rate':100.0,'size':1}]
        self.assertEqual(check(Host(sql,rows,bad),'Dune')['status'],'contradicted')

    def test_boundary_top_two_can_select_any_two_of_three_exact_peers(self):
        rows=snapshot((('Aster',1,1),('Birch',1,1),('Cedar',1,1)))
        sql=SQL.replace('LIMIT 1','LIMIT 2')
        for teams in [('Aster','Birch'),('Aster','Cedar'),('Birch','Cedar')]:
            h=Host(sql,rows,[{'team':t,'rate':100.0} for t in teams])
            self.assertEqual(check(h,teams[0])['status'],'proven')

    def test_strict_prefix_mandatory_when_limit_cuts_lower_tie(self):
        rows=snapshot((('Aster',1,1),('Birch',1,2),('Cedar',1,2),('Dahlia',0,1)))
        sql=SQL.replace('LIMIT 1','LIMIT 2')
        for peer in ['Birch','Cedar']:
            h=Host(sql,rows,[{'team':'Aster','rate':100.0},{'team':peer,'rate':50.0}])
            self.assertEqual(check(h,'Aster',unique=True)['status'],'proven')
        h=Host(sql,rows,[{'team':'Birch','rate':50.0},{'team':'Cedar','rate':50.0}])
        self.assertEqual(check(h,'Birch',50)['status'],'contradicted')

    def test_full_secondary_boundary_not_primary_rate_alone(self):
        rows=snapshot((('Aster',1,1),('Birch',2,2),('Cedar',2,2),('Dahlia',3,3)))
        sql=SQL.replace(' AS rate',' AS rate, COUNT(*) AS size').replace('rate DESC LIMIT 1','rate DESC, size ASC LIMIT 2')
        for peer in ['Birch','Cedar']:
            returned=[{'team':'Aster','rate':100.0,'size':1},{'team':peer,'rate':100.0,'size':2}]
            self.assertEqual(check(Host(sql,rows,returned),'Aster')['status'],'proven')
        bad=[{'team':'Aster','rate':100.0,'size':1},{'team':'Dahlia','rate':100.0,'size':3}]
        self.assertEqual(check(Host(sql,rows,bad),'Aster')['status'],'contradicted')

    def test_captured_values_keys_and_cardinality_not_relaxed(self):
        for returned in [[],[{'team':'Dune','rate':99.9}],[{'team':'Dune','rate':'100'}],
                         [{'team':'Dune','rate':100,'extra':0}],
                         [{'team':'Dune','rate':100},{'team':'Elm','rate':100}],
                         [{'team':'Absent','rate':100}]]:
            with self.subTest(returned=returned):
                self.assertEqual(check(Host(returned=returned),'Dune')['status'],'contradicted')

    def test_duplicate_rows_cannot_fill_boundary_slots(self):
        rows=snapshot((('Aster',1,1),('Birch',1,1),('Cedar',1,1)))
        h=Host(SQL.replace('LIMIT 1','LIMIT 2'),rows,[{'team':'Aster','rate':100.0}]*2)
        self.assertEqual(check(h,'Aster')['status'],'contradicted')

    def test_uncaptured_winner_and_false_uniqueness_remain_rejected(self):
        h=Host()
        self.assertEqual(check(h,'Dune')['status'],'contradicted')
        self.assertEqual(check(h,unique=True)['reason'],'false_unique_claim')

    def test_exact_near_ties_never_use_claim_or_float_tolerance(self):
        rows=snapshot((('Lower',97,129),('Higher',94,125)))
        h=Host(rows=rows)
        self.assertEqual(check(h,'Higher',75.2,True)['status'],'proven')
        fake=[{'team':'Lower','rate':100*97/129}]
        self.assertEqual(check(Host(rows=rows,returned=fake),'Lower',75.2)['status'],'contradicted')

    def test_unique_and_zero_rate_ties_still_distinguished(self):
        self.assertEqual(check(Host(rows=snapshot((('Only',0,1),))),'Only',0,True)['status'],'proven')
        h=Host(rows=snapshot((('Dune',0,1),('Elm',0,1))))
        self.assertEqual(check(h,rate=0)['status'],'proven')
        self.assertEqual(check(h,rate=0,unique=True)['status'],'contradicted')

    def test_full_result_without_order_and_nontruncating_limit_unchanged(self):
        for sql in [SQL.split(' ORDER BY')[0],SQL.replace('LIMIT 1','LIMIT 2'),SQL.replace('LIMIT 1','LIMIT 10')]:
            h=Host(sql)
            self.assertEqual(check(h,'Dune')['status'],'proven')

    def test_zero_limit_does_not_invent_capture_membership(self):
        self.assertEqual(check(Host(SQL.replace('LIMIT 1','LIMIT 0')))['status'],'insufficient')

    def test_wrong_order_population_literal_and_decorative_sql_do_not_prove(self):
        rows=snapshot((('Dune',1,2),('Elm',0,1)))
        rows.append({'id':4,'team':'Elm','status':'done','blocked':1})
        for sql in [SQL.replace('rate DESC','rate ASC'),SQL.replace(" WHERE status!='done'",''),
                    SQL.replace('100.0*SUM(blocked)/COUNT(*)','50.0'),
                    SQL.replace('100.0*SUM(blocked)/COUNT(*)','50.0+0*SUM(blocked)')]:
            self.assertNotEqual(check(Host(sql,rows),rate=50)['status'],'proven')

    def test_cte_average_and_uppercase_alias_preserve_tie_selection(self):
        for sql in [SQL.replace('100.0*SUM(blocked)/COUNT(*)','100.0*AVG(blocked)'),SQL.replace('rate','RATE'),
                    "WITH a AS (SELECT team,blocked FROM delivery_work_items WHERE status!='done') SELECT team,100.0*SUM(blocked)/COUNT(*) AS rate FROM a GROUP BY team ORDER BY rate DESC LIMIT 1"]:
            self.assertEqual(check(Host(sql))['status'],'proven')

    def test_host_bindings_identity_failure_and_snapshot_not_bypassed(self):
        a=Host();b=Host()
        self.assertEqual(check(b,expected=a.expected)['reason'],'capture_identity_mismatch')
        for field in ['query_sha256','result_sha256','snapshot_sha256','config_sha256','contract_sha256','call_id']:
            expected=dict(a.expected);expected[field]='forged'
            self.assertEqual(check(a,expected=expected)['reason'],'binding_mismatch')
        for kw in [dict(success=False),dict(complete=False)]:
            self.assertEqual(check(Host(**kw))['status'],'insufficient')
        self.assertEqual(check(a,execution_id='other')['status'],'insufficient')
        a.record=replace(a.record,snapshot_json=json.dumps(snapshot((('Dune',0,1),('Elm',0,1)))))
        self.assertEqual(check(a)['status'],'contradicted')

    def test_old_metric_and_contract_cannot_be_silently_relabelled(self):
        h=Host(config=dict(CONFIG,metric='phase3-d01-provenance-v1'))
        self.assertEqual(check(h)['reason'],'contract_mismatch')
        h=Host();h.record=replace(h.record,contract_sha256='0'*64)
        self.assertEqual(check(h,expected=v.binding(h.record))['reason'],'contract_mismatch')

if __name__=='__main__':unittest.main()
