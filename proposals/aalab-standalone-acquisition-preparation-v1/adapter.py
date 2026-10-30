"""Inactive host-owned A3 bindings; unchanged standalone clients/worker/scorer."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import capture_core as core
import a3_observer as observation
from src.agents.ollama_client import OllamaModelClient
from src.tools.clickhouse_readonly import query_clickhouse
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor,_QUERY_TOOL
from src.evals.system_benchmark.runner import run_trial

CONFIG={};CONFIG_SHA='';BOUNDARY=None;ALLOWED_DELEGATES=();CHECK_SOURCES=None
FLAGS={**core.FLAGS,'live_dispatch_allowed':False}
def digest(value):return observation.sha(observation.encoded(value))
def decode_plan(raw):
    if type(raw) is not bytes or len(raw)>16384:raise ValueError('A3 bounded plan bytes required')
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('duplicate plan key')
            result[k]=v
        return result
    plan=json.loads(raw,object_pairs_hook=unique)
    if set(plan)!={'version','synthetic','live_dispatch_allowed','configuration_sha256','source_commit','invocations'}:raise ValueError('A3 closed plan required')
    if plan['version']!='A3-synthetic-plan-v1' or plan['synthetic'] is not True or plan['live_dispatch_allowed'] is not False:raise ValueError('A3 inactive synthetic plan required')
    if plan['configuration_sha256']!=CONFIG_SHA or plan['source_commit']!=CONFIG['source_commit']:raise ValueError('A3 configuration binding mismatch')
    entries=plan['invocations']
    if type(entries) is not list or not 1<=len(entries)<=2:raise ValueError('A3 two invocation bound')
    seen=set()
    for e in entries:
        if type(e) is not dict or set(e)!={'invocation_id','task_id','arm','block','session','task_sha256','reference_sha256'}:raise ValueError('A3 closed invocation required')
        if e['invocation_id'] not in ('a','b') or e['invocation_id'] in seen:raise ValueError('A3 explicit unique invocation required')
        seen.add(e['invocation_id'])
        if e['task_id'] not in ('A3-SYN-01','A3-SYN-02') or e['arm'] not in ('baseline','candidate') or e['block'] not in ('B1','B2'):raise ValueError('A3 fixture identity refused')
        if not isinstance(e['session'],str) or not 1<=len(e['session'])<=128:raise ValueError('A3 explicit session required')
        for k in ('task_sha256','reference_sha256'):
            if type(e[k]) is not str or len(e[k])!=64 or any(c not in '0123456789abcdef' for c in e[k]):raise ValueError('A3 exact commitment required')
    return plan

class AcquisitionHost:
    def __init__(self,plan_bytes,evidence_root,delegate):
        self._plan=decode_plan(plan_bytes)
        if type(delegate) not in ALLOWED_DELEGATES:raise ValueError('A3 explicit trusted in-memory delegate required')
        CHECK_SOURCES()
        self.root=Path(evidence_root).absolute();self._delegate=delegate;self._records={};self._proof={};self._sealed={};self._used={};self._reserved=[]
        if self.root.is_symlink():raise ValueError('A3 private root required')
        self.root.mkdir(parents=True,exist_ok=False,mode=0o700)
        self._binding={'version':CONFIG['version'],'source_commit':CONFIG['source_commit'],
          'configuration_sha256':CONFIG_SHA,'contract_sha256':CONFIG['contract_sha256'],
          'closure_sha256':digest(CONFIG['external_sources']),'plan_sha256':observation.sha(plan_bytes),
          'C01_package_sha256':CONFIG['C01_package_sha256'],**FLAGS}
        self._owner=digest({'binding':self._binding,'root':str(self.root)})
        self._write(self.root/'plan.json',plan_bytes);self._write(self.root/'binding.json',observation.encoded(self._binding))
    def _write(self,path,raw,*,append=False):
        path=Path(path)
        if type(raw) is not bytes or path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):raise ValueError('A3 private artifact required')
        if any(p.is_symlink() for p in path.parents if p!=self.root.parent):raise ValueError('A3 symlink refused')
        relative=path.relative_to(self.root);key=relative.parts[0]
        used=self._used.get(key,0)
        if used+len(raw)>393216:raise ValueError('A3 trial artifact ceiling')
        if append:
            if str(relative) not in self._sealed or observation.sha(path.read_bytes())!=self._sealed[str(relative)]:raise ValueError('A3 append target changed')
        with path.open('ab' if append else 'xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        self._used[key]=used+len(raw);self._sealed[str(relative)]=observation.sha(path.read_bytes())
    def _intact(self):
        return all(not(self.root/p).is_symlink() and (self.root/p).is_file() and observation.sha((self.root/p).read_bytes())==v for p,v in self._sealed.items())
    def acquisition_receipt(self,invocation_id):return copy.deepcopy(self._records[invocation_id])
    def verify_acquisition(self,invocation_id,receipt):
        try:
            return self._intact() and receipt['complete'] is True and observation.encoded(receipt)==self._proof[invocation_id] and receipt['owner']==self._owner
        except (KeyError,ValueError,TypeError,OSError):return False

def prepare_acquisition(plan_bytes,evidence_root,*,transport_delegate):
    if BOUNDARY is None or not getattr(sys,'_a3_guard_installed',False):raise RuntimeError('A3 guarded offline bootstrap required')
    return AcquisitionHost(plan_bytes,evidence_root,transport_delegate)

def run_acquired_trial(host,invocation_id,*,task,reference):
    if type(host) is not AcquisitionHost:raise ValueError('A3 host-owned context required')
    n=len(host._reserved)
    if invocation_id in host._reserved or n>=len(host._plan['invocations']) or host._plan['invocations'][n]['invocation_id']!=invocation_id:raise ValueError('A3 explicit unused invocation required')
    if BOUNDARY.active is not None or not host._intact():raise ValueError('A3 retained context invalid')
    if getattr(sys,'_a3_trial_entries',0)>=2:raise ValueError('A3 per-control trial ceiling')
    expected=host._plan['invocations'][n]
    if task.case_id!=expected['task_id'] or digest(asdict(task))!=expected['task_sha256'] or digest(asdict(reference))!=expected['reference_sha256']:raise ValueError('A3 task/reference binding mismatch')
    CHECK_SOURCES()
    out=host.root/invocation_id;out.mkdir(mode=0o700)
    host._reserved.append(invocation_id);sys._a3_trial_entries=getattr(sys,'_a3_trial_entries',0)+1
    host._write(out/'invocation-entry.json',observation.encoded({'owner':host._owner,'expected':expected,
      'flag_scope':'all records and raw reads under this invocation; inherited H1 records unmodified',**host._binding}))
    observer=observation.AcquisitionObserver(host._delegate,lambda p,b:host._write(host.root/p,b),Path(invocation_id),host._owner,invocation_id)
    session=None;row=None;failure=None;errors=[]
    try:
        model_config={'name':'A3-SYNTHETIC','base_url':'https://ollama.a3.invalid','timeout_seconds':120}
        checks={'config':{'allowed_tools':['query_clickhouse'],'model':model_config,'query_tool_sha256':digest(_QUERY_TOOL)}}
        session=core.CaptureSession(core.SyntheticRequest(CONFIG['source_commit'],CONFIG_SHA,'A3+C01-offline-only'),out,checks,
          synthetic_preflight=lambda:None,write_bounded=host._write)
        BOUNDARY.active=observer
        model=OllamaModelClient(model=model_config['name'],base_url=model_config['base_url'],timeout=120)
        def query(sql):
            if len(sql.encode())>512:raise ValueError('A3 SQL fixture ceiling')
            rows=query_clickhouse(sql)
            if len(rows)>8 or len(observation.encoded(rows))>8192:raise ValueError('A3 parsed rows ceiling')
            return rows
        wrapped=session.wrap_model(model)
        class BoundedReturn:
            def respond(self,messages,tools):
                result=wrapped.respond(messages,tools)
                if len(observation.encoded(result))>4096:raise ValueError('A3 normalized return ceiling')
                return result
        worker=BoundedLocalExecutor(model=BoundedReturn(),query_fn=session.wrap_tool('query_clickhouse',query),
          policy_fn=lambda **kw:(_ for _ in ()).throw(ValueError('A3 policy unavailable')),max_model_steps=2)
        row=run_trial(task,reference,trial_number=1,executor=session.wrap_executor(worker))
        session.safe_event('runner_return',result=row)
    except BaseException as exc:
        failure=exc
        if session:session.safe_event('runner_error',error=observation.error(exc))
    finally:BOUNDARY.active=None
    calls,capture_complete,capture_errors=observer.finish();errors.extend(capture_errors)
    if session:
        session.manifest['attempt_status']='returned' if row is not None else 'error'
        try:session.write_manifest()
        except BaseException as exc:errors.append({'stage':'h1_manifest',**observation.error(exc)})
        errors.extend(session.collector_errors)
    receipt={**host._binding,'owner':host._owner,'invocation_id':invocation_id,'expected':copy.deepcopy(expected),
      'calls':calls,'result_sha256':digest(row) if row is not None else None,
      'success':row['task_success'] if row is not None else None,'score_status':'scored' if row is not None else 'not_reached',
      'surfaced_error':observation.error(failure) if failure is not None else None,
      'complete':capture_complete and not errors,'capture_errors':errors,
      'live_effective_settings':None,'live_model_digest':None,'remote_lifetime':'unverified',
      'setting_evidence':'requested fields only; effective server application unobserved'}
    try:
        if row is not None:host._write(out/'runner-result.json',observation.encoded(row))
        host._write(out/'acquisition-receipt.json',observation.encoded(receipt))
        host._proof[invocation_id]=observation.encoded(receipt)
    except BaseException as exc:
        receipt['complete']=False;receipt['capture_errors'].append({'stage':'finalization',**observation.error(exc)})
    host._records[invocation_id]=copy.deepcopy(receipt)
    if failure is not None:raise failure
    return row
