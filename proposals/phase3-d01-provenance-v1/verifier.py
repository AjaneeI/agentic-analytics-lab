"""Inactive D01 offline reference verifier; no runtime/scorer/SQL imports.

Only `claim` is claimant-controlled. `resolver` and `expected` are separately
host-owned inputs; object identity cannot be reconstructed from a JSON envelope.
This candidate accepts only explicitly synthetic captures. No live adapter or
host authentication is provided. A malicious host/Python caller is out of scope.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import json
import math
import re
from pathlib import Path

from sql_proof import prove, Unsupported, Contradiction

VERSION="phase3-d01-provenance-v1"
CONTRACT_PATH=Path(__file__).with_name("contract.json")

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

@dataclass(frozen=True)
class HostCapture:
    execution_id: str
    call_id: str
    query: str
    result_json: str
    snapshot_json: str
    config_json: str
    source_commit: str
    metric_version: str
    task_id: str
    contract_sha256: str
    origin: str
    success: bool
    complete: bool

def capture(*,execution_id,call_id,query,rows,snapshot,config,origin,success,complete):
    """Host-side fixture adapter boundary: freeze independently captured bytes.

    Does not execute SQL, authenticate its caller, deserialize agent evidence or
    claim a live execution. The test-only resolver supplies actual SQLite runs.
    """
    return HostCapture(execution_id,call_id,query,canonical(rows),canonical(snapshot),
                       canonical(config),config.get("source_commit"),config.get("metric"),config.get("task_id"),
                       hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),origin,success,complete)

def binding(record):
    """Host-owned expected commitment; obtain independently, never from a claim."""
    return {"capture_ref":record,"execution_id":record.execution_id,"call_id":record.call_id,
            "source_commit":record.source_commit,"metric_version":record.metric_version,"task_id":record.task_id,
            "query_sha256":digest(record.query),"result_sha256":digest(record.result_json),
            "snapshot_sha256":digest(record.snapshot_json),"config_sha256":digest(record.config_json),
            "contract_sha256":record.contract_sha256}

def outcome(status,reason,**details):
    return {"status":status,"reason":reason,"live_qualified":False,**details}

def snapshot_valid(rows):
    if not isinstance(rows,list) or len(rows)>10000:
        return False
    ids=set()
    for row in rows:
        if not isinstance(row,dict) or not all(k in row for k in ("id","team","status","blocked")):
            return False
        if type(row["id"]) is not int or row["id"] in ids:
            return False
        ids.add(row["id"])
        if not isinstance(row["team"],str) or not row["team"] or not isinstance(row["status"],str) or not row["status"]:
            return False
        if type(row["blocked"]) is not int or row["blocked"] not in (0,1):
            return False
    return True

def finite_number(value):
    if type(value) not in (int,float):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError,ValueError,TypeError):
        return False

def same_value(actual,expected):
    if isinstance(expected,F):
        try:
            return finite_number(actual) and math.isclose(actual,float(expected),rel_tol=1e-12,abs_tol=1e-12)
        except (OverflowError,ValueError,TypeError):
            return False
    return type(actual) is type(expected) and actual==expected

def verify(claim,*,resolver,expected):
    if not isinstance(claim,dict) or not callable(getattr(resolver,"resolve",None)):
        return outcome("insufficient","untrusted_capture")
    try:
        record=resolver.resolve(claim.get("execution_id"))
    except Exception:
        return outcome("insufficient","untrusted_capture")
    if type(record) is not HostCapture or not isinstance(expected,dict):
        return outcome("insufficient","untrusted_capture")
    if (not isinstance(record.query,str) or not isinstance(record.source_commit,str)
        or not re.fullmatch(r"[0-9a-f]{40}",record.source_commit)
        or any(not isinstance(x,str) or not x for x in (record.execution_id,record.call_id,record.result_json,record.snapshot_json,record.config_json))
        or sum(len(x) for x in (record.query,record.result_json,record.snapshot_json,record.config_json))>2*1024*1024):
        return outcome("insufficient","invalid_capture")
    try:
        config=json.loads(record.config_json)
    except (ValueError,TypeError,RecursionError):
        return outcome("insufficient","invalid_capture")
    if not isinstance(config,dict) or any(config.get(k)!=value for k,value in (("source_commit",record.source_commit),("metric",record.metric_version),("task_id",record.task_id))) or not isinstance(config.get("version"),str) or not config["version"]:
        return outcome("insufficient","invalid_capture")
    if "capture_ref" not in expected:
        return outcome("insufficient","missing_binding")
    if record is not expected["capture_ref"]:
        return outcome("contradicted","capture_identity_mismatch")
    actual=binding(record)
    for field,value in actual.items():
        if field not in expected:
            return outcome("insufficient","missing_binding",field=field)
        if expected[field]!=value:
            return outcome("contradicted","binding_mismatch",field=field)
    contract=json.loads(CONTRACT_PATH.read_text())
    if record.contract_sha256!=hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest() or record.metric_version!=contract["version"] or record.task_id!=contract["task"] or contract["state"]!="inactive_proposal":
        return outcome("contradicted","contract_mismatch")
    if record.origin!="synthetic_sqlite":
        return outcome("insufficient","unsupported_origin")
    if record.success is not True:
        return outcome("insufficient","execution_not_successful")
    if record.complete is not True:
        return outcome("insufficient","incomplete_result")
    try:
        snapshot=json.loads(record.snapshot_json);result=json.loads(record.result_json)
    except (ValueError,TypeError,RecursionError):
        return outcome("insufficient","invalid_snapshot")
    if not snapshot_valid(snapshot):
        return outcome("insufficient","invalid_snapshot")
    counts={}
    for row in snapshot:
        if row["status"]!="done":
            b,n=counts.get(row["team"],(0,0));counts[row["team"]]=(b+row["blocked"],n+1)
    if not counts:
        return outcome("insufficient","no_eligible_population")
    try:
        relation,team_column,metric_column=prove(record.query,snapshot)
    except Contradiction as error:
        return outcome("contradicted",str(error))
    except (Unsupported,ValueError,TypeError,IndexError,KeyError,RecursionError,ZeroDivisionError):
        return outcome("insufficient","unsupported_sql")
    if not isinstance(result,list) or len(result)>1000 or len(result)!=len(relation.rows):
        return outcome("contradicted","captured_result_mismatch")
    # SQL identifier matching only. Preserve original captured bytes and values;
    # reject collisions instead of overwriting or coercing result data.
    normalized=[]
    for row in result:
        if not isinstance(row,dict) or any(not isinstance(key,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",key) for key in row):
            return outcome("contradicted","captured_result_mismatch")
        keys=[key.lower() for key in row]
        if len(set(keys))!=len(keys):
            return outcome("contradicted","captured_result_mismatch")
        normalized.append(dict(zip(keys,row.values())))
    result=normalized
    if any(not isinstance(row,dict) or not isinstance(row.get(team_column),str) or not row[team_column] for row in result):
        return outcome("contradicted","captured_result_mismatch")
    if len({row[team_column] for row in result})!=len(result):
        return outcome("contradicted","captured_result_mismatch")
    observed={row[team_column]:row for row in result}
    for expected_row in relation.rows:
        key=expected_row[team_column].value
        row=observed.get(key)
        if row is None or row.keys()!=expected_row.keys() or any(not same_value(row[name],cell.value) for name,cell in expected_row.items()):
            return outcome("contradicted","captured_result_mismatch")
    if not isinstance(claim.get("team"),str) or not finite_number(claim.get("blocked_pct")) or type(claim.get("unique_winner")) is not bool:
        return outcome("contradicted","invalid_claim")
    maximum=max(F(b,n) for b,n in counts.values())
    winners=sorted(team for team,(b,n) in counts.items() if F(b,n)==maximum)
    if claim["team"] not in winners:
        return outcome("contradicted","claim_team_not_winner",winners=winners)
    # The claim must bind to a row from THIS successful capture, never stale state.
    if claim["team"] not in observed:
        return outcome("contradicted","captured_result_mismatch")
    b,n=counts[claim["team"]]
    if abs(F(str(claim["blocked_pct"]))-100*F(b,n))>F(str(contract["claim_tolerance_percentage_points"])):
        return outcome("contradicted","claim_rate_mismatch")
    if claim["unique_winner"] and len(winners)!=1:
        return outcome("contradicted","false_unique_claim",winners=winners)
    return outcome("proven","fixture_computation_proven",winners=winners,numerator=b,denominator=n,
                   percentage_exact=str(100*F(b,n)),capture_origin=record.origin,
                   contract_sha256=record.contract_sha256,query_sha256=actual["query_sha256"])
