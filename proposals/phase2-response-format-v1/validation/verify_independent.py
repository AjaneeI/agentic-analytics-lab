#!/usr/bin/env python3
"""Offline whole-proposal source/guard/evidence review; no inference or scoring."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
from unittest.mock import Mock,patch
sys.dont_write_bytecode=True
ROOT=Path('/Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration')
p=ROOT/'work/phase2-response-format-proposal';c=ROOT/'work/phase2-response-format-validation';base='57c3007a25af4ff21bec42138aa1df7268ee7d95'
proposal='1eca40abc6656a37588f812f853cd4001c14c8ac';candidate='d4922de83113fa5477aaadfca8f110e600770eb5';rel='proposals/phase2-response-format-v1';worker='src/evals/system_benchmark/local_worker.py'
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())
for root,head in ((p,proposal),(c,candidate)):
 assert git(root,'rev-parse','HEAD')==head and not git(root,'status','--porcelain')
def tree(root,rev):
 raw=git(root,'ls-tree','-r',rev,'--','src','scripts','evals','configurations')
 return {line.split('\t',1)[1]:line.split('\t',1)[0] for line in raw.splitlines()}
before=tree(p,base);prop=tree(p,'HEAD');cand=tree(c,'HEAD')
assert len(before)==87 and before==prop
assert set(cand)==set(before) and [name for name in before if cand[name]!=before[name]]==[worker]
assert git(p,'rev-parse',base+':DECISIONS.md')==git(p,'rev-parse','HEAD:DECISIONS.md')
manifest=load(p/rel/'manifest.json')
assert sha(p/rel/'candidate.patch')==manifest['candidate_patch_sha256']
assert sha(p/worker)==manifest['baseline_worker_sha256'] and sha(c/worker)==manifest['candidate_worker_sha256']
def prompt(tree):
 n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_SYSTEM_PROMPT' for t in n.targets))
 assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='strip'
 return n,n.value.func.value.value.strip()
t1=ast.parse((p/worker).read_text());t2=ast.parse((c/worker).read_text());n1,s1=prompt(t1);n2,s2=prompt(t2)
assert s2.startswith(s1+'\n\nResponse field types:')
assert len(s2[len(s1):].splitlines())==10 # Leading newline plus nine added source lines.
assert hashlib.sha256(s1.encode()).hexdigest()==manifest['baseline_prompt_sha256']
assert hashlib.sha256(s2.encode()).hexdigest()==manifest['candidate_prompt_sha256']
assert (p/rel/'candidate-system-prompt.txt').read_bytes()==s2.encode()
n2.value=copy.deepcopy(n1.value)
assert ast.dump(t1,include_attributes=False)==ast.dump(t2,include_attributes=False)
with tempfile.TemporaryDirectory() as td:
 temp=Path(td);(temp/worker).parent.mkdir(parents=True);(temp/worker).write_bytes((p/worker).read_bytes())
 subprocess.check_call(['git','apply','--check',str(p/rel/'candidate.patch')],cwd=temp)
 subprocess.check_call(['git','apply',str(p/rel/'candidate.patch')],cwd=temp)
 assert (temp/worker).read_bytes()==(c/worker).read_bytes()
subprocess.check_call(['git','diff','--check',base,'HEAD','--','.',':(exclude)'+rel+'/candidate.patch'],cwd=p)
assert (p/rel/'configuration.proposal.json').read_bytes()==(c/rel/'configuration.proposal.json').read_bytes()
assert sha(p/rel/'configuration.proposal.json')==manifest['candidate_configuration_sha256']
config=load(p/rel/'configuration.proposal.json');old=load(p/'configurations/phase2-runtime-schema-v1-scope-observation-v1.approved.json')
for key in ('model','limits','allowed_tools','query_tool_sha256','schema_version','scope_observation_version','task_id'):
 assert config[key]==old[key]
assert config['response_format_activation_approval']=='not_granted'
assert manifest['activation_authorized'] is False and manifest['live_attempts_authorized']==0
sys.path.insert(0,str(c))
from scripts import passive_capture as capture
from scripts import qualify_phase2_once as runner
assert not any(name.startswith('src.') for name in sys.modules)
assert capture.contract_fingerprint(c)['benchmark_contract_sha256']==manifest['candidate_contract_fingerprint']
assert capture.contract_fingerprint(p)['benchmark_contract_sha256']==manifest['baseline_contract_fingerprint']
def deny(*args,**kwargs):raise AssertionError('independent proposal review forbids runtime/model/services')
probes={name:Mock(side_effect=deny) for name in ('model_factory','query_fn','policy_fn','service_json_get','service_query_fn','os_snapshot')}
request=capture.CaptureRequest(c,candidate,c/rel/'configuration.proposal.json',sha(c/rel/'configuration.proposal.json'),True,'offline inactive-proposal refusal probe only')
with patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny),patch('socket.create_connection',deny),patch('socket.getaddrinfo',deny),patch('urllib.request.urlopen',deny),patch.object(runner,'_task_boundary',side_effect=deny),patch.object(runner,'service_preflight',side_effect=deny),patch.object(capture,'capture_once',side_effect=deny):
 inspected=runner.source_preflight(request)
 assert inspected['execution_blockers']==['configuration_scope_version_or_standalone_boundary_differs','runtime_offline_validity_gate_not_passed']
 with tempfile.TemporaryDirectory() as td:
  out=Path(td)/'must-not-exist'
  try:runner.qualify_once(request,out,**probes)
  except capture.CaptureRefused as error:refusal=str(error)
  else:raise AssertionError('inactive candidate unexpectedly permitted execution')
  assert not out.exists()
 for probe in probes.values():probe.assert_not_called()
assert not any(name.startswith('src.') for name in sys.modules)
seals={}
for name,count in [('treatment-a-20261017',20),('treatment-a-scope-v1-20261017',4)]:
 folder=ROOT/'outputs'/name;expected=load(folder/'sha256.json');assert len(expected)==count
 assert all(sha(folder/key)==value for key,value in expected.items())
 seals[name]={'count':count,'all_match':True,'sha256':expected,'manifest_sha256':sha(folder/'sha256.json')}
verification=load(p/rel/'validation/verification.json')
assert all(sha(p/rel/'validation'/name)==digest for name,digest in verification['logs_sha256'].items())
for name in ['proposal-python311-full.txt','proposal-python312-full.txt','validation-python311-full.txt','validation-python312-full.txt']:
 text=(p/rel/'validation'/name).read_text();assert 'Ran 359 tests' in text and 'OK' in text
brief_path=p/'docs/phase3-phase4-decision-brief-2026-10-17.md';brief=brief_path.read_text()
rows=[line for line in brief.splitlines() if line.startswith('| `') or re.match(r'^\| (R-\d\d|P4-\d\d)',line)]
assert len(rows)==30
for row in rows:
 cells=[s.strip() for s in row.strip('|').split('|')];assert len(cells)==6 and all(cells),row
phase3=load(ROOT/'work/phase3/experiments/evaluator-validation-20261017/audit.json')
ids=[re.search(r'`([^`]+)`',row).group(1) for row in rows[:9]]
assert ids==phase3['unresolved_control_ids']
assert re.findall(r'^\| (R-\d\d)',brief,re.M)==[f'R-{i:02}' for i in range(1,10)]
assert re.findall(r'^\| (P4-\d\d)',brief,re.M)==[f'P4-{i:02}' for i in range(1,13)]
sim=load(ROOT/'work/phase4/experiments/phase4-calibration-20261017/existing-interval-simulation.json')
scenarios={row['scenario']['name']:row['summary'] for row in sim['scenarios']}
assert scenarios['family_shock']['zero_exclusion_rate']['rate']==.21
assert scenarios['run_shock']['zero_exclusion_rate']['count']==203
assert scenarios['positive_effect']['zero_exclusion_rate']['rate']==.51
assert scenarios['positive_effect']['two_sided_null_false_positive'] is None
assert 'No recommendation below is enacted' in brief and 'none is granted here' in brief
assert not git(p,'status','--porcelain') and not git(c,'status','--porcelain')
report={'proposal_commit':proposal,'candidate_validation_commit':candidate,'parent_execution_commit':base,'production_files_unchanged_on_proposal':87,'only_candidate_production_difference':worker,'only_candidate_AST_difference':'_SYSTEM_PROMPT assignment value','patch_check_and_temporary_apply_identical_to_candidate':True,'diff_whitespace_check_excludes_unified_patch_context_only':True,'manifest':manifest,'inactive_actual_guard':{'blockers':inspected['execution_blockers'],'refusal':refusal,'runtime_imports':False,'services_constructors_workers_output_folders':0},'experiment_integrity':seals,'recorded_full_suite_logs_verified':verification['full_suites'],'recorded_log_sha256_all_match':True,'decision_brief':{'rows':30,'phase3_exact_ids':ids,'runtime_ids':[f'R-{i:02}' for i in range(1,10)],'phase4_ids':[f'P4-{i:02}' for i in range(1,13)],'all_six_columns_nonempty':True,'DECISIONS_md_unchanged':True,'stored_phase4_numbers_crosschecked_no_simulation':True,'sha256':sha(brief_path)},'artifact_sha256':{str(path.relative_to(p)):sha(path) for path in (p/rel).rglob('*') if path.is_file()},'verification_script_sha256':sha(Path(__file__))}
print(json.dumps(report,sort_keys=True))
