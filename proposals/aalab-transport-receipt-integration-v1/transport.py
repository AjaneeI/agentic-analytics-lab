"""Closed synthetic HTTP boundary. Never retains or delegates to a real opener."""
import base64
import copy
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request

MODEL_URL='https://ollama.h2.invalid/api/chat'
QUERY_BASE='https://clickhouse.h2.invalid/'
QUERY_SETTINGS={'default_format':'JSONEachRow','readonly':'1','max_execution_time':'10',
 'max_result_rows':'1000','result_overflow_mode':'break','max_rows_to_read':'10000',
 'max_bytes_to_read':'10485760','max_memory_usage':'134217728','max_threads':'2'}
QUERY_URL=QUERY_BASE+'?'+urllib.parse.urlencode(QUERY_SETTINGS)
SYNTHETIC_AUTH='Basic '+base64.b64encode(b'H2_SYNTHETIC_USER:H2_SYNTHETIC_PASSWORD').decode('ascii')

def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def error(exc):return {'type':type(exc).__name__,'message':str(exc)[:512]}

def decode_fixture(raw,configuration_sha256,identities):
    if type(raw) is not bytes or len(raw)>16384:raise ValueError('bounded fixture bytes required')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('duplicate fixture key')
            result[k]=v
        return result
    value=json.loads(raw.decode(),object_pairs_hook=pairs,
       parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite fixture')))
    if type(value) is not dict or set(value)!={'version','configuration_sha256','invocations'}:raise ValueError('fixture fields')
    if value['version']!='H2-fake-http-v1' or value['configuration_sha256']!=configuration_sha256:raise ValueError('fixture configuration')
    entries=value['invocations']
    if type(entries) is not list or not 1<=len(entries)<=2:raise ValueError('fixture invocation bound')
    if any(type(e) is not dict or set(e)!={'invocation_id','calls'} for e in entries):raise ValueError('fixture identity fields')
    if [e['invocation_id'] for e in entries]!=identities:raise ValueError('fixture/plan invocation mismatch')
    for entry in entries:
        calls=entry['calls']
        if type(calls) is not list or not 1<=len(calls)<=3:raise ValueError('fake call bound')
        for n,c in enumerate(calls):
            if type(c) is not dict or c.get('kind')!=('model','query','model')[n]:raise ValueError('closed fake call sequence')
            required={'kind','sql'} if c['kind']=='query' else {'kind'}
            if set(c) not in (required|{'body'},required|{'error'}):raise ValueError('fake body/error fields')
            if 'body' in c and (type(c['body']) is not str or len(c['body'].encode())>2048):raise ValueError('response byte cap')
            if 'error' in c and (type(c['error']) is not str or not 1<=len(c['error'].encode())<=256):raise ValueError('error byte cap')
            if c['kind']=='query' and (type(c['sql']) is not str or len(c['sql'].encode())>512 or not re.fullmatch(r'SELECT [0-9]{1,4} AS h2_[a-z_]{1,30}',c['sql'])):raise ValueError('fresh scalar SQL fixture required')
    return value

class ClosedTransport:
    def __init__(self):self.active=None;self.enabled=True;self.accepted_calls=0
    def installed(self):
        return self.enabled and urllib.request.urlopen==self.open and getattr(sys,'_h2_guard_installed',False)
    def admitted(self):return self.installed() and self.active is not None
    def begin(self,owner,invocation,specs,write):
        if not self.installed() or self.active is not None:raise RuntimeError('H2 sealed interceptor unavailable')
        self.active={'owner':owner,'invocation':invocation,'specs':copy.deepcopy(specs),'write':write,'calls':[],'reserved':0}
    def finish(self,owner):
        state=self.active
        if state is None or state['owner']!=owner:raise RuntimeError('H2 sealed owner mismatch')
        self.active=None
        return copy.deepcopy(state['calls']),len(state['calls'])==state['reserved']==len(state['specs'])
    def open(self,request,timeout=None,**kwargs):
        state=self.active
        if not self.admitted() or kwargs or state['reserved']>=len(state['specs']):raise RuntimeError('H2 sealed fake request refused')
        if type(request) is not urllib.request.Request or request.get_method()!='POST':raise RuntimeError('H2 closed POST request required')
        index=state['reserved'];spec=state['specs'][index]
        expected=MODEL_URL if spec['kind']=='model' else QUERY_URL
        if request.full_url!=expected:raise RuntimeError('H2 unknown destination; no delegate fallback')
        body=request.data
        if type(body) is not bytes or len(body)>8192:raise ValueError('H2 request byte cap')
        headers=dict(request.header_items())
        if spec['kind']=='model':
            payload=json.loads(body)
            if timeout!=120 or payload.get('model')!='H2-OFFLINE' or payload.get('stream') is not False or payload.get('keep_alive')!='30m' or payload.get('options')!={'temperature':0,'num_predict':128,'num_ctx':2048}:raise ValueError('pinned model request mismatch')
        else:
            if timeout!=15 or body.decode()!=spec['sql'] or headers.get('Authorization')!=SYNTHETIC_AUTH:raise ValueError('pinned query request mismatch')
        state['reserved']+=1
        token=sha(encoded({'owner':state['owner'],'invocation':state['invocation'],'call':index+1}))
        request_copy={'method':'POST','url':request.full_url,'headers':headers,
          'redacted_headers':{k:('[SYNTHETIC AUTH REDACTED]' if k.lower()=='authorization' else v) for k,v in headers.items()},
          'body_sha256':sha(body),'body_utf8':body.decode(),'timeout_seconds':timeout}
        record={'token':token,'ordinal':index+1,'kind':spec['kind'],'request':request_copy,
          'boundary_error':None,'response_sha256':None,'start_monotonic':time.monotonic()}
        prefix='call-'+str(index+1)
        write=state['write']
        write(prefix+'-request.json',encoded(request_copy));write(prefix+'-request-body.bin',body)
        boundary_error=None
        if 'error' in spec:
            boundary_error=RuntimeError(spec['error']);record['boundary_error']=error(boundary_error)
        else:
            response=spec['body'].encode();write(prefix+'-response.bin',response)
            record['response_sha256']=sha(response)
        record['end_monotonic']=time.monotonic()
        write(prefix+'-boundary.json',encoded(record))
        state['calls'].append(record);self.accepted_calls+=1
        if boundary_error is not None:raise boundary_error
        return io.BytesIO(response)
