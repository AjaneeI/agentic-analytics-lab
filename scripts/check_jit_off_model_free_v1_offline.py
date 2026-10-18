"""Exercise the exact validation harness with fabricated HTTP, sockets denied."""
import importlib.util,io,json,socket,sys,tempfile
from pathlib import Path
from unittest.mock import patch
b=Path(sys.argv[1]).resolve();r=b/'work/jit-off-model-free-validation';spec=importlib.util.spec_from_file_location('h',r/'scripts/validate_jit_off_model_free_v1.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
modules={'baseline':h.load_transport(b/'work/clickhouse-timeout-proposal',h.PROPOSAL_PIN,h.BASE_SHA,'baseline_fake'),
 'candidate':h.load_transport(b/'work/clickhouse-timeout-validation',h.CANDIDATE_PIN,h.CANDIDATE_SHA,'candidate_fake')}
for case in h.PLAN:
 assert 'agentic_analytics' not in case['sql'] and 'delivery_work_items' not in case['sql'] and 'SETTINGS ' not in case['sql']
def deny(*a,**k):raise AssertionError('offline socket forbidden')
summary=[]
with patch.object(socket.socket,'connect',deny),patch('socket.getaddrinfo',deny),patch('socket.create_connection',deny):
 for scenario in ['success','wrong-jit','wrong-limit','bad-value','timeout']:
  calls=[]
  def fake(request,*,timeout):
   from urllib.parse import parse_qs,urlsplit
   params=parse_qs(urlsplit(request.full_url).query);lane='candidate' if 'compile_expressions' in params else 'baseline';case=h.PLAN[len(calls)];calls.append(case['id'])
   if scenario=='timeout':raise TimeoutError('fixture timeout')
   if case['kind']=='settings':
    row={k:v for k,v in h.PARAMETERS.items() if k!='default_format'};row.update(server_version='26.8.4.11',compile_expressions='0' if lane=='candidate' else '1')
    if scenario=='wrong-jit':row['compile_expressions']='1'
    if scenario=='wrong-limit':row['max_threads']='3'
    rows=[row]
   else:
    rows=h.EXPECTED_SCALAR if case['kind']=='scalar' else h.EXPECTED_AGGREGATE
    if scenario=='bad-value':rows=[dict(rows[0],affine=999),*rows[1:]]
   response=io.BytesIO(('\n'.join(json.dumps(x) for x in rows)+'\n').encode());response.status=200;response.headers={'X-ClickHouse-Query-Id':'fixture-only'};return response
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'evidence';status=h.execute(out,modules,expected_script_commit='offline-fixture',transport=fake);m=json.loads((out/'manifest.json').read_text())
   assert (status.startswith('passed'))==(scenario=='success'),(scenario,status,(out/'error.json').read_text() if (out/'error.json').exists() else '')
   expected=6 if scenario=='success' else (3 if scenario=='bad-value' else 1)
   assert len(calls)==expected and m['SQL_attempts']==expected,(scenario,calls)
   assert m['retries']==0 and m['Treatment_A_entries']==0
   assert (out/'wire-captures.json').exists() and (out/'events.jsonl').exists()
   try:h.execute(out,modules,expected_script_commit='duplicate',transport=fake)
   except FileExistsError:pass
   else:raise AssertionError('duplicate directory was not refused')
   summary.append({'scenario':scenario,'SQL_fixture_calls':len(calls),'status':status,'duplicate_out_refused':True})
 for actual in [[{'x':float('nan')}],[{'x':True}],[{'x':'1'}]]:
  try:h.check_rows(actual,[{'x':1}])
  except AssertionError:pass
  else:raise AssertionError('invalid numeric fixture accepted')
print(json.dumps({'offline_scenarios':summary,'finite_numeric_rejections':3,'model_calls':0,'live_SQL_calls':0,'sockets_DNS_denied':True},indent=2))
