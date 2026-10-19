"""Bounded NEW synthetic controls, never full repository discovery.

This test-only entry point uses explicitly in-memory SQLite and blocks network,
process launches, filesystem databases and benchmark/runtime module imports.
"""
import argparse
import hashlib
import importlib.abc
import json
from pathlib import Path
import platform
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
observations={"memory_sqlite_connections":0,"blocked_side_effect_attempts":[]}

def guard(event,args):
    forbidden=event.startswith("socket.") or event in ("subprocess.Popen","os.system","os.posix_spawn","os.fork")
    if event=="sqlite3.connect":
        if args[0]!=":memory:":
            forbidden=True
        else:
            observations["memory_sqlite_connections"]+=1
    if forbidden:
        observations["blocked_side_effect_attempts"].append(event)
        raise RuntimeError("offline validation forbids "+event)

class NoRuntime(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=="src" or fullname.startswith("src."):
            raise ImportError("active benchmark/runtime imports are forbidden")
        return None

sys.addaudithook(guard)
sys.meta_path.insert(0,NoRuntime())
from test_verifier import FixtureHost, SQL, check, claim, population, v

def matrix():
    cases=[]
    def case(name,expected,sql=SQL,rows=None,response=None,changes=None):
        host=FixtureHost(sql=sql,rows=rows,**(changes or {}))
        result=check(host,response)
        cases.append({"id":name,"expected":expected,"actual":result["status"],"reason":result["reason"],
                      "matches_expectation":result["status"]==expected,"query":sql,
                      "snapshot_sha256":host.expected["snapshot_sha256"],"result":result,
                      "origin":"new_synthetic_sqlite_fixture"})
    case("P01-canonical-limit","proven")
    case("P02-full-teams","proven",SQL.split(" ORDER BY")[0])
    case("P03-avg","proven",SQL.replace("100.0 * SUM(blocked) / COUNT(*)","100.0 * AVG(blocked)"))
    case("P04-case","proven",SQL.replace("SUM(blocked)","SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END)"))
    case("P05-projection-cte","proven","WITH active AS (SELECT team, blocked FROM delivery_work_items WHERE status!='done') SELECT team, 100.0*SUM(blocked)/COUNT(*) AS rate FROM active GROUP BY team ORDER BY rate DESC LIMIT 1")
    case("P06-counts-cte","proven","WITH counts AS (SELECT team, SUM(blocked) AS b, COUNT(*) AS n FROM delivery_work_items WHERE status!='done' GROUP BY team) SELECT team, 100.0*b/n AS rate FROM counts ORDER BY rate DESC LIMIT 1")
    case("P07-not-in","proven",SQL.replace("status != 'done'","status NOT IN ('done')"))
    case("P08-negation","proven",SQL.replace("status != 'done'","NOT(status='done')"))
    case("N01-literal","contradicted",SQL.replace("100.0 * SUM(blocked) / COUNT(*)","75.0"))
    case("N02-decorative","contradicted",SQL.replace("100.0 * SUM(blocked) / COUNT(*)","75.0+0*SUM(blocked)"))
    case("N03-reciprocal","contradicted",SQL.replace("100.0 * SUM(blocked) / COUNT(*)","100.0*COUNT(*)/SUM(blocked)"))
    case("N04-wrong-denominator","contradicted",SQL.replace("100.0 * SUM(blocked) / COUNT(*)","100.0*SUM(blocked)/SUM(blocked)"))
    case("N05-wrong-case-population","contradicted",SQL.replace("'done'","'Done'"))
    case("N06-no-filter","contradicted",SQL.replace(" WHERE status != 'done'",""))
    case("N07-picked-team","contradicted",SQL.replace("status != 'done'","status!='done' AND team='Amber'"))
    case("N08-ascending","contradicted",SQL.replace("blocked_pct DESC","blocked_pct ASC"))
    case("N09-literal-case","contradicted",SQL.replace("100.0 * SUM(blocked) / COUNT(*)","CASE WHEN 1=1 THEN 75.0 ELSE SUM(blocked) END"))
    case("N10-fabricated-result","contradicted",changes={"captured_rows":[{"team":"Amber","blocked_pct":75.1}]})
    case("N11-wrong-team-claim","contradicted",response=claim("Birch",40))
    case("N12-wrong-rate-claim","contradicted",response=claim(rate=74.7))
    case("I01-function-outside-grammar","insufficient",SQL.replace("SUM(blocked)","TOTAL(blocked)"))
    case("I02-equivalent-not-not-outside-grammar","insufficient",SQL.replace("status != 'done'","NOT NOT(status!='done')"))
    case("I03-failed-current-call","insufficient",changes={"success":False})
    case("I04-incomplete-result","insufficient",changes={"complete":False})
    case("I05-unimplemented-live-origin","insufficient",changes={"origin":"live_host"})
    case("I06-empty","insufficient",rows=[])
    for name,extra,winner,rate in [
        ("M01-active-blocked",[{"id":100,"team":"Amber","status":"todo","blocked":1}],"Amber",80),
        ("M02-active-unblocked",[{"id":100,"team":"Amber","status":"todo","blocked":0}],"Amber",60),
        ("M03-competitor-flip",[{"id":100+i,"team":"Birch","status":"todo","blocked":1} for i in range(8)],"Birch",1000/13),
        ("M04-excluded-completed",[{"id":100,"team":"Absent","status":"done","blocked":1}],"Amber",75),
    ]:
        case(name,"proven",rows=population()+extra,response=claim(winner,rate))
    case("M05-row-permutation","proven",rows=list(reversed(population())))
    case("M06-duplication","proven",rows=population()+[dict(r,id=r["id"]+100) for r in population()])
    tied=population()+[{"id":100+i,"team":"Birch","status":"todo","blocked":1} for i in range(7)]
    case("M07-exact-tie-acknowledged","proven",rows=tied,response=claim(unique_winner=False))
    case("M08-exact-tie-false-unique","contradicted",rows=tied)
    host=FixtureHost()
    for field in ("query_sha256","result_sha256","snapshot_sha256","config_sha256","source_commit","execution_id","call_id","metric_version","task_id","contract_sha256"):
        expected=dict(host.expected);expected[field]="wrong"
        result=check(host,expected=expected)
        cases.append({"id":"B-"+field,"expected":"contradicted","actual":result["status"],"reason":result["reason"],"matches_expectation":result["status"]=="contradicted","origin":"host_binding_mutation"})
    false_acceptances=[c["id"] for c in cases if c["expected"]!="proven" and c["actual"]=="proven"]
    false_rejections=[c["id"] for c in cases if c["expected"]=="proven" and c["actual"]!="proven"]
    return {"cases":cases,"case_count":len(cases),"false_acceptances":false_acceptances,"supported_valid_false_rejections":false_rejections,
            "reason_or_outcome_mismatches":[c["id"] for c in cases if not c["matches_expectation"]]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite validation evidence")
    suite=unittest.defaultTestLoader.loadTestsFromName("test_verifier.ProvenanceControls")
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    controls=matrix()
    report={"status":"inactive_synthetic_validation_only","python":platform.python_version(),
            "unit_tests":result.testsRun,"unit_failures":len(result.failures),"unit_errors":len(result.errors),
            "controls":controls,"side_effect_guard":observations,
            "candidate_source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob("*")) if p.is_file() and p.suffix in (".py",".json")},
            "live_qualified":False,"phase3_accepted":False,"new_treatment_a_attempts":0,
            "passed":result.wasSuccessful() and not controls["reason_or_outcome_mismatches"] and not observations["blocked_side_effect_attempts"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report,handle,indent=2,sort_keys=True);handle.write("\n")
    print(json.dumps({key:report[key] for key in ("python","unit_tests","passed")}))
    print(json.dumps({key:controls[key] for key in ("case_count","false_acceptances","supported_valid_false_rejections","reason_or_outcome_mismatches")}))
    raise SystemExit(0 if report["passed"] else 1)

if __name__=="__main__":
    main()
