"""Two bounded failure-evidence probes; import original runner guard first."""
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path('/Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration/work/phase3-d01-capture-integration-v1')
HERE=ROOT/'proposals/phase3-d01-capture-integration-v1'
spec=importlib.util.spec_from_file_location('_guarded_capture_runner',HERE/'run_validation.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
t=runner.test_capture
results=[]
with t.SyntheticCaptureSession(t.fixture(),t.CONFIG) as h:
    try:h.query('SELECT \ud800 AS bad')
    except BaseException as e:
        token=h.calls[0]
        results.append({'probe':'lone-surrogate','raised':type(e).__name__,'message':str(e),'event_count':len(h.events),'capture_present':h.resolve(token.execution_id) is not None})
        try:h.verify(t.claim(token),call=token)
        except BaseException as verify_error:results[-1]['verification_raised']=type(verify_error).__name__
class CancelledConnection:
    def execute(self,sql):raise KeyboardInterrupt('synthetic execute cancellation')
    def close(self):pass
with t.SyntheticCaptureSession(t.fixture(),t.CONFIG) as h:
    original=h._connection
    h._connection=CancelledConnection()
    try:h.query(t.SQL)
    except BaseException as e:
        token=h.calls[0];event=h.events[0];record=h.resolve(token.execution_id)
        results.append({'probe':'execute-cancellation','raised':type(e).__name__,'event_count':len(h.events),'capture_present':record is not None,'success':record.success,'complete':record.complete,'error_type':event.error_type,'error_message':event.error_message,'verification':h.verify(t.claim(token),call=token)})
    finally:
        h._connection=original
print(json.dumps({'results':results,'guard':runner.upstream.observations},indent=2))
