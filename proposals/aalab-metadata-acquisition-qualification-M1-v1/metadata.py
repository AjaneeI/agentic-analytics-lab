"""Exactly one fixed metadata transaction. No provider/model/SQL interface."""
import copy
import json
import socket
import sys
import time
import m1_admission as admission
import m1_helpers as helpers
WIRE=b'GET /api/version HTTP/1.0\r\nHost: 127.0.0.1:11434\r\nAccept: application/json\r\nConnection: close\r\n\r\n'
LIMITS={'wire_bytes':8192,'header_bytes':4096,'body_bytes':4096,'network_seconds':3.0,'operation_seconds':1.0}
class Stop(Exception):
    def __init__(self,disposition):self.disposition=disposition
class ActualClock:
    def monotonic(self):return time.monotonic()
    def utc(self):return time.time()
def bind_offline(c,factory,clock,*,limits=None):
    if c.mode!='offline' or type(factory) not in admission.FACTORY_TYPES or type(clock) not in admission.CLOCK_TYPES:raise ValueError('M1 trusted scripted boundary required')
    c._factory=factory;c._clock=clock;c._limits={}
    for k,v in (limits or {}).items():
        if k not in LIMITS or type(v) not in (int,float) or not 0<v<=LIMITS[k]:raise ValueError('M1 only tighter injected limits')
        c._limits[k]=v
def parse_headers(raw,body_limit):
    try:text=raw.decode('ascii')
    except UnicodeError:raise Stop('invalid_framing')
    lines=text[:-4].split('\r\n');parts=lines[0].split(' ',2)
    if len(parts)<2 or parts[0] not in ('HTTP/1.0','HTTP/1.1') or len(parts[1])!=3 or not parts[1].isdigit():raise Stop('invalid_framing')
    if any(ord(c)<32 and c not in '\r\n\t' or ord(c)==127 for c in text):raise Stop('invalid_framing')
    headers={}
    for line in lines[1:]:
        if ':' not in line or line.startswith((' ','\t')):raise Stop('invalid_framing')
        name,value=line.split(':',1);name=name.lower()
        if not name or any(c not in "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyz" for c in name) or name in headers:raise Stop('invalid_framing')
        headers[name]=value.strip()
    if 'transfer-encoding' in headers or 'content-encoding' in headers:raise Stop('invalid_framing')
    length=headers.get('content-length')
    if length is None or not length.isdigit() or len(length)>4:raise Stop('invalid_framing')
    length=int(length)
    if length>body_limit:raise Stop('body_cap')
    return int(parts[1]),headers,length
def qualify_version_once(c):
    if type(c) is not admission.Context:raise ValueError('M1 host context required')
    if c._started:raise ValueError('M1 invocation consumed; no retry')
    c._started=True
    if c.mode=='offline' and c._factory is None:raise ValueError('M1 explicit offline socket required')
    clock=c._clock if c.mode=='offline' else ActualClock();limits={**LIMITS,**c._limits}
    now=clock.utc();ok,reason=c.admitted(now)
    r={**c.binding,'disposition':'BLOCKED_ADMISSION','admission_reason':reason,'allowance_consumed':False,
      'socket_created':False,'connect_attempts':0,'request_attempts':0,'http_status':None,'headers':None,
      'received_bytes':0,'wire_path':None,'wire_sha256':None,'capture_complete':False,'metadata_qualified':False,
      'observed_version':None,'effective_model_digest':None,'effective_server_settings':None,
      'remote_handler_lifetime':'unverified','local_socket_closed':None,'transport_error':None,'capture_errors':[],
      'admission_utc_epoch':now,'network_seconds':None,'completion_basis':None}
    if not ok:return _finish(c,r)
    try:c.reserve(now)
    except BaseException as exc:
        r['allowance_consumed']=c._reserved
        r['disposition']='entry_record_failed';r['capture_errors'].append(helpers.error(exc));return _finish(c,r)
    r['allowance_consumed']=True
    sock=None;data=bytearray();body_start=None;length=None;status=None;headers=None;complete=False
    started=clock.monotonic();deadline=started+limits['network_seconds']
    def remaining():
        t=deadline-clock.monotonic()
        if t<=0:raise Stop('network_deadline')
        return min(limits['operation_seconds'],t)
    try:
        remaining()
        if c.mode=='real':sys._m1_native_context=c
        sock=c._factory() if c.mode=='offline' else socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        r['socket_created']=True;sock.settimeout(remaining());r['connect_attempts']=1;sock.connect(('127.0.0.1',11434))
        sock.settimeout(remaining());r['request_attempts']=1;sock.sendall(WIRE)
        while True:
            remaining()
            if body_start is None:
                room=min(limits['header_bytes']-len(data),limits['wire_bytes']-len(data))
                if room<=0:raise Stop('header_cap' if len(data)>=limits['header_bytes'] else 'wire_cap')
            else:
                received=len(data)-body_start
                if received>length:raise Stop('invalid_framing')
                if received==length:complete=True;break
                room=min(length-received,limits['wire_bytes']-len(data))
                if room<=0:raise Stop('wire_cap')
            sock.settimeout(remaining());chunk=sock.recv(min(1024,int(room)))
            if type(chunk) is not bytes or len(chunk)>min(1024,int(room)):raise Stop('transport_contract_error')
            data.extend(chunk);remaining()
            if not chunk:raise Stop('partial_eof')
            if body_start is None and b'\r\n\r\n' in data:
                body_start=data.index(b'\r\n\r\n')+4
                if body_start>limits['header_bytes']:raise Stop('header_cap')
                status,headers,length=parse_headers(bytes(data[:body_start]),limits['body_bytes'])
        r['disposition']='response_complete';r['completion_basis']='exact declared Content-Length; no invented EOF or extra drain'
    except Stop as exc:r['disposition']=exc.disposition
    except BaseException as exc:r['disposition']='transport_error';r['transport_error']=helpers.error(exc)
    finally:
        if sock is not None:
            try:sock.close();r['local_socket_closed']=True
            except BaseException as exc:r['local_socket_closed']=False;r['capture_errors'].append({'stage':'close',**helpers.error(exc)})
        r['network_seconds']=clock.monotonic()-started
        if c.mode=='real':sys._m1_native_context=None
    r['http_status']=status;r['headers']=headers;r['received_bytes']=len(data)
    # Preserve actual consumed prefix before interpreting JSON, including failures.
    try:c.write('wire.bin',bytes(data));r['wire_path']='wire.bin';r['wire_sha256']=helpers.sha(bytes(data))
    except BaseException as exc:r['capture_errors'].append({'stage':'wire_record',**helpers.error(exc)})
    r['capture_complete']=complete and not r['capture_errors']
    if complete:
        if status!=200:r['disposition']='non_200'
        else:
            def unique(pairs):
                result={}
                for k,v in pairs:
                    if k in result:raise ValueError('duplicate JSON key')
                    result[k]=v
                return result
            def invalid_constant(value):raise ValueError('nonstandard JSON constant')
            try:
                value=json.loads(bytes(data[body_start:]).decode('utf-8'),object_pairs_hook=unique,parse_constant=invalid_constant)
                if type(value) is not dict or type(value.get('version')) is not str or not value['version'].strip():raise ValueError('version field missing')
            except (ValueError,UnicodeError):r['disposition']='invalid_json'
            else:r['observed_version']=value['version'];r['disposition']='version_response_observed';r['metadata_qualified']=r['capture_complete']
    return _finish(c,r)
def _finish(c,r):
    try:c.write('metadata-receipt.json',helpers.encoded(r))
    except BaseException as exc:
        r['capture_complete']=False;r['metadata_qualified']=False;r['capture_errors'].append({'stage':'receipt_record',**helpers.error(exc)})
    c._record=copy.deepcopy(r);return copy.deepcopy(r)
def metadata_receipt(c):
    if type(c) is not admission.Context or c._record is None:raise ValueError('M1 recorded context required')
    r=copy.deepcopy(c._record)
    if not c.intact():r['capture_complete']=False;r['metadata_qualified']=False;r['capture_errors'].append({'stage':'retained_integrity','type':'IntegrityError'})
    return r
