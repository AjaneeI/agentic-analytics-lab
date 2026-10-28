"""Inactive host-only S2 linkage; trusted fixture Python, untrusted agent JSON."""
from dataclasses import asdict
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import time
from capture_core import CaptureSession, SyntheticRequest, _canonical, _error, _public
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor, _QUERY_TOOL
from src.evals.system_benchmark.runner import run_trial

CONFIG={}
CONFIG_SHA=''
SCORER_SHA=''
FLAGS={'synthetic':True,'inactive':True,'live_qualified':False,'live_authentication':False,
    'independence_established':False,'scientific_ready':False,'new_attempts':0}

def sha(b):return hashlib.sha256(b).hexdigest()
def duplicate_safe(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate JSON key')
        result[k]=v
    return result

def plan_decode(raw):
    if type(raw) is not bytes or len(raw)>32768:raise ValueError('bounded plan bytes required')
    p=json.loads(raw.decode('utf-8'),object_pairs_hook=duplicate_safe,
        parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite plan')))
    if type(p) is not dict or set(p)!={'version','synthetic','campaign_id','source_commit','configuration_sha256','shared_sources','invocations'}:raise ValueError('plan fields')
    if p['version']!='H1-synthetic-plan-v1' or p['synthetic'] is not True:raise ValueError('synthetic-only plan')
    if p['source_commit']!=CONFIG['source_commit'] or p['configuration_sha256']!=CONFIG_SHA:raise ValueError('source/config mismatch')
    if type(p['campaign_id']) is not str or not re.fullmatch('[A-Za-z0-9-]{1,64}',p['campaign_id']):raise ValueError('campaign identity')
    if type(p['invocations']) is not list or not 1<=len(p['invocations'])<=8:raise ValueError('invocation bound')
    ids=set();cells=set()
    for e in p['invocations']:
        if type(e) is not dict or set(e)!={'invocation_id','task_id','arm','block','order','session','task_sha256','reference_sha256','planned_start'}:raise ValueError('identity fields')
        if type(e['invocation_id']) is not str or not re.fullmatch('[A-Za-z0-9-]{1,64}',e['invocation_id']) or e['invocation_id'] in ids:raise ValueError('invocation identity')
        if e['task_id'] not in ('H1-SYN-01','H1-SYN-02') or e['arm'] not in ('baseline','candidate') or e['block'] not in ('B1','B2') or e['order'] not in ('AB','BA'):raise ValueError('fixture identity')
        if type(e['session']) is not str or not re.fullmatch('[A-Za-z0-9-]{1,64}',e['session']):raise ValueError('session identity')
        if any(type(e[k]) is not str or not re.fullmatch('[0-9a-f]{64}',e[k]) for k in ('task_sha256','reference_sha256')):raise ValueError('artifact commitment')
        if type(e['planned_start']) is not str or len(e['planned_start'])>64:raise ValueError('planned field bound')
        cell=(e['task_id'],e['block'],e['arm'])
        if cell in cells:raise ValueError('duplicate planned cell')
        ids.add(e['invocation_id']);cells.add(cell)
    pairs={}
    for e in p['invocations']:pairs.setdefault((e['task_id'],e['block']),[]).append(e)
    for pair in pairs.values():
        if len(pair)==2:
            expected=['baseline','candidate'] if pair[0]['order']=='AB' else ['candidate','baseline']
            if [e['arm'] for e in pair]!=expected or any(e['order']!=pair[0]['order'] or e['session']!=pair[0]['session'] for e in pair):raise ValueError('paired order/session mismatch')
    if type(p['shared_sources']) is not list or len(p['shared_sources'])>8:raise ValueError('dependence ledger bound')
    for e in p['shared_sources']:
        if type(e) is not dict or set(e)!={'source','blocks','dependence'} or type(e['source']) is not str or not 1<=len(e['source'])<=64 or type(e['blocks']) is not list or not 1<=len(e['blocks'])<=2 or any(x not in ('B1','B2') for x in e['blocks']) or e['dependence'] not in ('unknown','dependent'):raise ValueError('dependence ledger')
    return p

class Host:
    def __init__(self,raw,root):
        self._plan=plan_decode(raw);self._plan_raw=raw;self.plan_sha=sha(raw)
        self.root=Path(root).absolute();self.root.mkdir(parents=True,exist_ok=False)
        self._reserved=[];self._records={};self._proof={};self._bytes={};self._objects=[];self._busy=False
        self._write(self.root/'plan.json',raw)
    def _write(self,path,data,*,append=False):
        path=Path(path)
        if type(data) is not bytes or not path.resolve().is_relative_to(self.root.resolve()) or path.is_symlink():raise ValueError('private bounded artifact required')
        scope=path.parent;used=self._bytes.get(scope,0)
        if used+len(data)>65536:raise ValueError('H1 invocation artifact cap')
        self._bytes[scope]=used+len(data)
        with path.open('ab' if append else 'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    def receipt(self,i):return copy.deepcopy(self._records[i])
    def artifact(self,i,name):
        if i not in self._proof or name not in self._proof[i]['files']:raise ValueError('unknown artifact')
        return self.root/i/name
    def _plan_intact(self):
        p=self.root/'plan.json'
        return not p.is_symlink() and p.is_file() and sha(p.read_bytes())==self.plan_sha
    def verify(self,i,receipt):
        try:
            if not self._plan_intact():return False
            proof=self._proof[i]
            if not receipt['complete'] or _canonical(receipt)!=proof['receipt']:return False
            return all(not (self.root/i/name).is_symlink() and (self.root/i/name).is_file() and sha((self.root/i/name).read_bytes())==value for name,value in proof['files'].items())
        except (KeyError,TypeError,ValueError,OSError):return False
    def design_evidence(self):
        return {**FLAGS,'shared_sources':copy.deepcopy(self._plan['shared_sources']),
            'observed_invocations':list(self._records),'state_boundary':'fresh scripted Python objects only; persistent state unknown'}

def prepare_host(plan_bytes,evidence_root):return Host(plan_bytes,evidence_root)

def run_captured_trial(host,invocation_id,*,task,reference,scripted_model_factory,rows_callback_factory):
    if type(host) is not Host or host._busy:raise ValueError('host-only sequential context required')
    index=len(host._reserved)
    if index>=len(host._plan['invocations']):raise ValueError('no unused planned invocation')
    e=host._plan['invocations'][index]
    if invocation_id!=e['invocation_id'] or invocation_id in host._reserved:raise ValueError('explicit unused planned identity required')
    def preflight():
        if not host._plan_intact() or sha(host._plan_raw)!=host.plan_sha or plan_decode(host._plan_raw)!=host._plan:raise ValueError('sealed plan changed')
        if task.case_id!=e['task_id'] or sha(_canonical(asdict(task)))!=e['task_sha256'] or sha(_canonical(asdict(reference)))!=e['reference_sha256']:raise ValueError('task/reference binding mismatch')
    preflight()
    out=host.root/invocation_id;out.mkdir(exist_ok=False)
    host._write(out/'binding.json',_canonical({'plan_sha256':host.plan_sha,'identity':e,'configuration_sha256':CONFIG_SHA,**FLAGS}))
    host._reserved.append(invocation_id);host._busy=True
    session=None;result=None;error=None;stage='pre_invocation';started=time.monotonic()
    receipt={**FLAGS,'complete':False,'identity':copy.deepcopy(e),'plan_sha256':host.plan_sha,
        'configuration_sha256':CONFIG_SHA,'source_commit':CONFIG['source_commit'],'scorer_sha256':SCORER_SHA,
        'score_status':'not_reached','success':None,'result_sha256':None,'failure_stage':None,
        'start_monotonic':started,'actual_start':CaptureSession.utc(),'events':[],'collector_errors':[],
        'live_effective_settings':'unavailable: scripted-only harness'}
    try:
        checks={'config':{'allowed_tools':['query_clickhouse'],'query_tool_sha256':sha(_canonical(_QUERY_TOOL)),
            'model':{'name':'H1-scripted','base_url':'offline:','timeout_seconds':0}},'plan_sha256':host.plan_sha}
        session=CaptureSession(SyntheticRequest(CONFIG['source_commit'],CONFIG_SHA),out,checks,
            synthetic_preflight=preflight,write_bounded=host._write)
        model=scripted_model_factory();callback=rows_callback_factory()
        if any(model is x or callback is x for x in host._objects) or model is callback:raise ValueError('fresh logical instances required')
        host._objects.extend([model,callback]);receipt.update(model_instance=f'model-{index+1}',callback_instance=f'callback-{index+1}')
        class BoundModel:
            model='H1-scripted';base_url='offline:';timeout=0
            def respond(self,messages,tools):
                value=model.respond(messages,tools)
                if len(_canonical(value))>4096:raise ValueError('scripted return cap')
                return value
        def bounded_rows(sql):
            value=callback(sql)
            if type(value) is not list or len(value)>8 or any(type(r) is not dict for r in value) or len(_canonical(value))>8192:raise ValueError('ordinary row payload cap')
            return value
        def deny_policy(**kw):raise RuntimeError('policy retrieval denied in H1')
        worker=BoundedLocalExecutor(model=session.wrap_model(BoundModel()),query_fn=session.wrap_tool('query_clickhouse',bounded_rows),policy_fn=deny_policy,max_model_steps=2)
        stage='worker_or_runner'
        result=run_trial(task,reference,trial_number=1,executor=session.wrap_executor(worker))
        receipt.update(score_status='observed',success=result['task_success'],result_sha256=sha(_canonical(result)))
        session.safe_event('runner_return',result=result)
        try:
            host._write(out/'runner-result.json',_canonical(result))
        except BaseException as artifact_error:
            session.collector_errors.append({'stage':'runner_artifact',**_error(artifact_error)})
    except BaseException as exc:
        error=exc
        if session is not None:
            session.safe_event('runner_error',error=_error(exc))
            if session.worker_returned:
                receipt.update(score_status='unknown',failure_stage='runner_or_scorer')
            elif session.worker_error is not None:receipt['failure_stage']='worker'
            else:receipt['failure_stage']='pre_invocation'
        else:receipt['failure_stage']=stage
    finally:
        receipt['end_monotonic']=time.monotonic()
        try:
            if session is not None:
                session.write_manifest()
                receipt['durable_wrapper_entries']=session.worker_entries
                receipt['worker_delegate_entered']=session.worker_delegate_entered
                receipt['worker_returned']=session.worker_returned
                receipt['collector_errors']=copy.deepcopy(session.collector_errors)
                events=[json.loads(line) for line in session.event_path.read_bytes().splitlines()]
                receipt['events']=[x['event'] for x in events]
                receipt['complete']=not session.collector_errors
            files={p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
            receipt['artifacts']=files
            host._write(out/'receipt.json',_canonical(receipt))
            proof={'receipt':_canonical(receipt),'files':dict(files,**{'receipt.json':sha(_canonical(receipt))})}
            host._proof[invocation_id]=proof
        except BaseException as final_error:
            receipt['complete']=False;receipt['collector_errors'].append({'stage':'finalization',**_error(final_error)})
        host._records[invocation_id]=copy.deepcopy(receipt);host._busy=False
    if error is not None:raise error
    return result
