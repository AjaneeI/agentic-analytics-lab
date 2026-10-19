"""Inspected guarded corrections and stale config preflight only."""
import importlib.util
import json
from pathlib import Path
ROOT=Path('/Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration/work/phase3-d01-capture-integration-v1')
HERE=ROOT/'proposals/phase3-d01-capture-integration-v1'
spec=importlib.util.spec_from_file_location('_guarded_capture_runner',HERE/'run_validation.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
t=runner.test_capture
results=[]
before=runner.upstream.observations['memory_sqlite_connections']
try:t.SyntheticCaptureSession(t.fixture(),json.loads((HERE/'synthetic-config.json').read_text()))
except ValueError as e:
    assert str(e)=='adapter source fingerprint mismatch'
    assert runner.upstream.observations['memory_sqlite_connections']==before==0
    results.append({'probe':'stale-config','exception':str(e),'memory_connections':0})
else:raise AssertionError('stale config accepted')
config=json.loads((HERE/'synthetic-config-v2.json').read_text())
with t.SyntheticCaptureSession(t.fixture(),config) as h:
    sql='SELECT \ud800 AS bad'
    try:h.query(sql)
    except UnicodeEncodeError:
        assert not h.calls and not h._records and not h._expected
        event=h.events[0]
        assert event.error_type=='UnicodeEncodeError' and event.execute_attempts==0
        assert event.query_sha256 is None and json.loads(event.rejected_query_json)==sql
        results.append({'probe':'lone-surrogate','passed':True,'events':1,'calls':0,'records':0,'expected':0,'lossless_rejected_query':True})
    else:raise AssertionError('invalid UTF8 accepted')
class CancelledConnection:
    def execute(self,sql):raise KeyboardInterrupt('synthetic execute cancellation')
    def close(self):pass
with t.SyntheticCaptureSession(t.fixture(),config) as h:
    original=h._connection;h._connection=CancelledConnection()
    try:h.query(t.SQL)
    except KeyboardInterrupt:
        event=h.events[0];record=h.resolve(h.calls[0].execution_id)
        assert event.error_type=='KeyboardInterrupt' and event.error_message=='synthetic execute cancellation'
        assert not record.success and not record.complete and event.execute_attempts==1
        verdict=h.verify(t.claim(h.calls[0]),call=h.calls[0])
        assert verdict['reason']=='execution_not_successful' and not verdict['live_qualified']
        results.append({'probe':'execute-cancellation','passed':True,'error_type':event.error_type,'error_message':event.error_message,'verdict':verdict})
    else:raise AssertionError('cancellation swallowed')
    finally:h._connection=original
print(json.dumps({'results':results,'guard':runner.upstream.observations},indent=2))
