"""Inactive A3 observer. Replies are supplied by a separate explicit delegate.

Only client-consumed reads/context operations are forwarded. This module never
constructs an upstream reply, retains a default opener, or drains an error body.
"""
import copy
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
FLAGS={'synthetic':True,'inactive':True,'live_dispatch_allowed':False,
 'live_authentication':False,'live_qualified':False,'independence_established':False,
 'scientific_ready':False,'new_attempts':0}

def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def error(exc):
    try:message=str(exc)
    except BaseException:message='<unavailable>'
    return {'type':type(exc).__name__,'message':message[:2048]}

class AcquisitionObserver:
    def __init__(self,delegate,write,relative_root,owner,invocation_id):
        self.delegate=delegate;self.write=write;self.root=Path(relative_root)
        self.owner=owner;self.invocation_id=invocation_id
        self.calls=[];self.errors=[];self._bytes={};self._sequence={}
    def _record(self,c):
        """Secondary capture cannot replace the delegate/client outcome."""
        try:
            raw=encoded(c);index=c['call_id'];n=self._sequence.get(index,0)
            if len(raw)+self._bytes.get(index,0)>98304:raise ValueError('A3 HTTP record ceiling')
            self._sequence[index]=n+1
            self.write(self.root/(index+'-record-%02d.json'%n),raw)
            self._bytes[index]=self._bytes.get(index,0)+len(raw)
        except BaseException as exc:self.errors.append({'stage':'secondary_record',**error(exc)})
    def _metadata(self,c,response):
        try:
            status=getattr(response,'status',None)
            if status is None:status=getattr(response,'code',None)
            headers=getattr(response,'headers',None)
            items=list(headers.items()) if headers is not None else None
            if items is not None:
                items=[[str(k),str(v)] for k,v in items]
                if len(encoded(items))>4096:raise ValueError('A3 header ceiling')
            geturl=getattr(response,'geturl',None)
            url=geturl() if callable(geturl) else getattr(response,'url',None)
            if url is not None and (type(url) is not str or len(url.encode())>4096):raise ValueError('A3 final URL ceiling')
            c['response']={'status':status if type(status) is int else None,'headers':items,'final_url':url}
        except BaseException as exc:
            self.errors.append({'stage':'metadata_unavailable',**error(exc)})
    def open(self,request,*,timeout):
        if len(self.calls)>=3:raise ValueError('A3 three delegate ceiling')
        url=request.full_url
        if request.get_method()!='POST' or type(request.data) is not bytes:raise ValueError('A3 explicit POST required')
        kind='model' if url=='https://ollama.a3.invalid/api/chat' else 'query' if url.startswith('https://clickhouse.a3.invalid/?') else None
        if kind is None or timeout!={'model':120,'query':15}[kind]:raise ValueError('A3 endpoint/timeout refused')
        if sum(c['kind']==kind for c in self.calls)>={'model':2,'query':1}[kind]:raise ValueError('A3 kind call ceiling')
        requested={'url':url,'method':request.get_method(),'headers':list(request.header_items()),'body_utf8':request.data.decode(),'timeout':timeout}
        if len(encoded(requested))>8192:raise ValueError('A3 request ceiling')
        if kind=='query' and len(request.data)>512:raise ValueError('A3 scalar fixture SQL ceiling')
        index='call-'+str(len(self.calls)+1)
        c={**FLAGS,'call_id':index,'invocation_id':self.invocation_id,'owner':self.owner,'kind':kind,
           'request':requested,'stage':'request_constructed','delegate_entries':0,'response':None,
           'body_state':'unavailable','body_path':None,'body_sha256':None,'bytes_read':0,'read_calls':0,
           'upstream_error':None,'unobserved_error_body':False,'read_error':None,'close_error':None,'remote_lifetime':'unverified'}
        self.calls.append(c)
        # Required durable binding precedes the delegate. Reservation is not completion.
        entry=encoded(c)
        if len(entry)+self._bytes.get(index,0)>98304:raise ValueError('A3 HTTP record ceiling')
        self.write(self.root/(index+'-entry.json'),entry)
        self._bytes[index]=self._bytes.get(index,0)+len(entry)
        c['delegate_entries']=1;c['stage']='delegate_entered';started=time.monotonic()
        try:response=self.delegate(request,timeout=timeout)
        except BaseException as exc:
            c['stage']='delegate_error';c['upstream_error']=error(exc);self._metadata(c,exc)
            # The frozen query client may subsequently consume HTTPError.read().
            # Leave that object/behavior untouched; do not invent retained bytes.
            c['unobserved_error_body']=isinstance(exc,urllib.error.HTTPError)
            c['delegate_seconds']=time.monotonic()-started;self._record(c);raise
        c['stage']='response_obtained';c['delegate_seconds']=time.monotonic()-started
        self._metadata(c,response);self._record(c)
        return ObservedResponse(self,c,response)
    def finish(self):
        calls=copy.deepcopy(self.calls)
        complete=bool(calls) and not self.errors and all(
          c['delegate_entries']==1 and (c['body_state']=='complete' or c['upstream_error'] is not None)
          and not c['unobserved_error_body'] and c['read_error'] is None and c['close_error'] is None for c in calls)
        return calls,complete,copy.deepcopy(self.errors)

class ObservedResponse:
    def __init__(self,observer,call,upstream):
        self.observer=observer;self.call=call;self.upstream=upstream;self.reader=upstream;self.raw=bytearray();self.part=0
    def __enter__(self):
        try:self.reader=self.upstream.__enter__()
        except BaseException as exc:
            self.call['stage']='context_enter_error';self.call['upstream_error']=error(exc)
            self.observer._record(self.call);raise
        return self
    def _capture(self,raw,state):
        c=self.call;o=self.observer
        try:
            if type(raw) is not bytes:raise ValueError('A3 consumed body is not bytes')
            if len(self.raw)+len(raw)>65536:raise ValueError('A3 body ceiling')
            self.raw.extend(raw);c['bytes_read']=len(self.raw);c['body_state']=state
            name=c['call_id']+'-body'+('' if self.part==0 else '-%02d'%self.part)+'.bin';self.part+=1
            path=o.root/name
            if len(raw)+o._bytes.get(c['call_id'],0)>98304:raise ValueError('A3 HTTP record ceiling')
            # Each observed read is retained before control returns to the parser.
            o.write(path,raw);o._bytes[c['call_id']]=o._bytes.get(c['call_id'],0)+len(raw)
            c.setdefault('read_parts',[]).append({'path':str(path),'sha256':sha(raw),'bytes':len(raw)})
            c['body_path']=str(path) if len(c['read_parts'])==1 else None
            c['body_sha256']=sha(bytes(self.raw))
        except BaseException as exc:o.errors.append({'stage':'body_capture',**error(exc)})
    def read(self,*args,**kwargs):
        c=self.call;c['read_calls']+=1
        try:raw=self.reader.read(*args,**kwargs)
        except BaseException as exc:
            c['stage']='read_error';c['read_error']=error(exc);c['body_state']='partial'
            partial=getattr(exc,'partial',None)
            if type(partial) is bytes:self._capture(partial,'partial')
            self.observer._record(c);raise
        size=kwargs.get('amt',kwargs.get('size',args[0] if args else -1))
        complete=size is None or type(size) is int and size<0 or raw==b''
        self._capture(raw,'complete' if complete else 'partial')
        c['stage']='read_complete' if complete else 'read_partial';self.observer._record(c)
        return raw
    def __exit__(self,*args):
        try:return self.upstream.__exit__(*args)
        except BaseException as exc:
            self.call['close_error']=error(exc);self.observer._record(self.call);raise

class ClosedBoundary:
    """Installed by the guarded bootstrap; no saved/original network opener."""
    def __init__(self):self.active=None
    def admitted(self):return self.active is not None
    def open(self,request,*,timeout):
        if self.active is None:raise RuntimeError('A3 inactive sealed delegate required')
        return self.active.open(request,timeout=timeout)
