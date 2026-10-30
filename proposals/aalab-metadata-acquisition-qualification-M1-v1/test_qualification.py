"""Twelve fixed M1 controls. No real socket, model, query or service fixture."""
import copy
import json
from pathlib import Path
import unittest
try:
    import m1_metadata as metadata
    import m1_admission as admission
    import m1_runtime as runtime
except ImportError:
    metadata=admission=runtime=None
EVIDENCE=None
BODY=b'{"version":"M1-synthetic"}'
RESPONSE=b'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: '+str(len(BODY)).encode()+b'\r\n\r\n'+BODY
WIRE=b'GET /api/version HTTP/1.0\r\nHost: 127.0.0.1:11434\r\nAccept: application/json\r\nConnection: close\r\n\r\n'
class Clock:
    def __init__(self):self.value=0.0
    def monotonic(self):return self.value
    def utc(self):return 2000000001.0
class ScriptedSocket:
    def __init__(self,owner):self.owner=owner;self.closed=False;self.timeouts=[];self.read_sizes=[];self.sent=[];self.peer=None
    def settimeout(self,value):self.timeouts.append(value)
    def connect(self,peer):self.peer=peer;self.owner.connects+=1
    def sendall(self,raw):self.sent.append(raw);self.owner.sends+=1
    def recv(self,n):
        self.read_sizes.append(n)
        if self.owner.advance:self.owner.clock.value+=self.owner.advance
        if self.owner.chunks:
            head=self.owner.chunks[0]
            if isinstance(head,BaseException):self.owner.chunks.pop(0);raise head
            result=head[:n];self.owner.chunks[0]=head[n:]
            if not self.owner.chunks[0]:self.owner.chunks.pop(0)
            return result
        return b''
    def close(self):self.closed=True
class Factory:
    def __init__(self,chunks=None,advance=0):
        self.chunks=list([RESPONSE] if chunks is None else chunks)
        self.advance=advance;self.created=0;self.connects=0;self.sends=0;self.socket=None;self.clock=Clock()
        assert sum(len(x) for x in self.chunks if isinstance(x,bytes))<=8192
    def __call__(self):
        self.created+=1;self.socket=ScriptedSocket(self);return self.socket
def raw(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def plan():return {'version':'M1-plan-v1','operation_id':'M1-SYN-01','endpoint':'http://127.0.0.1:11434/api/version','mode':'offline','configuration_sha256':admission.CONFIG_SHA}
def receipts(owner=True):
    # Registered by the trusted OFFLINE host, never admitted as real authority.
    approval=runtime.INPUTS.issue('approval',{'source':'scripted:M1-approval','message_id':'M1-AUTH-01','text':'M1-I and conditional M1-O','package_sha256':admission.CONFIG['package_sha256']})
    consent=None
    if owner:consent=runtime.INPUTS.issue('owner',{'source':'scripted:M1-owner','message_id':'M1-OWNER-01','text':'One GET http://127.0.0.1:11434/api/version in the stated window. No conflicting hold.',
      'route':'http://127.0.0.1:11434/api/version','window_start':2000000000.0,'window_end':2000000060.0,'permission_source':'scripted policy; offline only','incompatible_hold':False})
    return approval,consent
class M1Controls(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(metadata,'M1 fixed metadata admission and acquisition is not implemented')
        self.root=Path(EVIDENCE)/self._testMethodName;self.root.mkdir(exist_ok=False)
    def tearDown(self):
        if hasattr(self,'root'):self.assertLessEqual(sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file()),262144)
    def prepare(self,factory=None,owner=True,p=None,limits=None):
        self.factory=factory if factory is not None else Factory()
        a,o=receipts(owner)
        c=admission.prepare_metadata_qualification(raw(p or plan()),self.root/'capture',approval_receipt=a,owner_receipt=o)
        metadata.bind_offline(c,self.factory,self.factory.clock,limits=limits)
        return c
    def result(self,c):
        r=metadata.qualify_version_once(c);self.assertFalse(r['live_qualified']);self.assertEqual(r['scientific_replicates'],0)
        self.assertEqual(r,metadata.metadata_receipt(c));return r
    def test_01_fixed_wire_actual_scripted_response(self):
        c=self.prepare();r=self.result(c)
        self.assertEqual(r['disposition'],'version_response_observed');self.assertTrue(r['capture_complete'])
        self.assertEqual(r['observed_version'],'M1-synthetic');self.assertEqual(self.factory.created,1)
        self.assertEqual(self.factory.connects,1);self.assertEqual(self.factory.sends,1)
        self.assertEqual(self.factory.socket.peer,('127.0.0.1',11434));self.assertEqual(self.factory.socket.sent,[WIRE])
        self.assertEqual((c.root/r['wire_path']).read_bytes(),RESPONSE);self.assertTrue(self.factory.socket.closed)
        self.assertIsNone(r['effective_model_digest']);self.assertEqual(r['remote_handler_lifetime'],'unverified')
    def test_02_wrong_endpoint_refuses_before_socket(self):
        p=plan();p['endpoint']='http://127.0.0.1:11434/api/tags';factory=Factory()
        with self.assertRaisesRegex(ValueError,'endpoint'):self.prepare(factory,p=p)
        self.assertEqual(factory.created,0)
    def test_03_missing_current_owner_refuses_before_socket(self):
        c=self.prepare(owner=False);r=self.result(c)
        self.assertEqual(r['disposition'],'BLOCKED_ADMISSION');self.assertEqual(self.factory.created,0)
        self.assertFalse(r['capture_complete']);self.assertFalse(r['allowance_consumed'])
    def test_04_required_entry_write_failure_no_socket(self):
        c=self.prepare();original=c.write
        def failed(name,data):
            if name=='RESERVED.json':raise OSError('M1 authored required sink failure')
            return original(name,data)
        c.write=failed;r=self.result(c)
        self.assertEqual(self.factory.created,0);self.assertEqual(r['disposition'],'entry_record_failed')
        self.assertFalse(r['capture_complete'])
    def test_05_partial_read_error_keeps_prefix_no_retry(self):
        prefix=b'HTTP/1.0 200 OK\r\nContent-Length: 25\r\n\r\n{"ver'
        c=self.prepare(Factory([prefix,OSError('M1 scripted read failure')]))
        r=self.result(c);self.assertEqual(r['disposition'],'transport_error');self.assertFalse(r['capture_complete'])
        self.assertEqual((c.root/r['wire_path']).read_bytes(),prefix);self.assertEqual(self.factory.created,1)
        self.assertEqual(self.factory.connects,1);self.assertTrue(self.factory.socket.closed)
    def test_06_tight_wire_cap_preserves_partial(self):
        c=self.prepare(limits={'wire_bytes':48});r=self.result(c)
        self.assertEqual(r['disposition'],'wire_cap');self.assertFalse(r['capture_complete'])
        self.assertEqual(r['received_bytes'],48);self.assertLessEqual(max(self.factory.socket.read_sizes),48)
    def test_07_tight_header_cap_before_parse(self):
        c=self.prepare(limits={'header_bytes':24});r=self.result(c)
        self.assertEqual(r['disposition'],'header_cap');self.assertFalse(r['capture_complete'])
        self.assertIsNone(r['observed_version']);self.assertLessEqual(r['received_bytes'],24)
    def test_08_ambiguous_declared_length_ineligible(self):
        response=b'HTTP/1.0 200 OK\r\nContent-Length: 2\r\nContent-Length: 3\r\n\r\n{}'
        c=self.prepare(Factory([response]));r=self.result(c)
        self.assertEqual(r['disposition'],'invalid_framing');self.assertFalse(r['capture_complete'])
        self.assertIsNone(r['observed_version']);self.assertEqual(self.factory.sends,1)
    def test_09_redirect_terminal_without_follow(self):
        response=b'HTTP/1.0 302 Found\r\nLocation: /api/tags\r\nContent-Length: 0\r\n\r\n'
        c=self.prepare(Factory([response]));r=self.result(c)
        self.assertEqual(r['disposition'],'non_200');self.assertEqual(r['http_status'],302)
        self.assertEqual(self.factory.created,1);self.assertEqual(self.factory.connects,1);self.assertEqual(self.factory.sends,1)
    def test_10_network_deadline_not_reset_on_progress(self):
        c=self.prepare(Factory([RESPONSE],advance=3.1));r=self.result(c)
        self.assertEqual(r['disposition'],'network_deadline');self.assertFalse(r['capture_complete'])
        self.assertEqual(self.factory.created,1);self.assertTrue(self.factory.socket.closed)
    def test_11_consumed_reservation_no_second_socket(self):
        ledger=getattr(admission,'authorization_ledger_path',None)
        self.assertIsNotNone(ledger,'M1 fixed cross-invocation ledger path is not exposed to integrity checks')
        self.assertEqual(ledger(),runtime.ROOT.parents[1]/'outputs'/admission.CONFIG['evidence_directory_slug']/admission.CONFIG['authorization_ledger_name'])
        c=self.prepare();first=self.result(c)
        with self.assertRaisesRegex(ValueError,'consumed'):metadata.qualify_version_once(c)
        self.assertEqual(self.factory.created,1);self.assertEqual(metadata.metadata_receipt(c),first)
    def test_12_owned_cleanup_unconfirmed_is_terminal(self):
        class Handle:
            returncode=None
            def poll(self):return None
        killed=[]
        r=runtime.terminal_disposition(Handle(),elapsed=10.01,kill=lambda:killed.append('owned-only'))
        self.assertEqual(killed,['owned-only']);self.assertFalse(r['cleanup_confirmed'])
        self.assertEqual(r['disposition'],'STOP_CLEANUP_UNCONFIRMED')
