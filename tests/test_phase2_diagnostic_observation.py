"""Offline regression of partial diagnostic header capture; no HTTP or benchmark."""
import importlib.util
import io
from pathlib import Path
import unittest
PATH=Path(__file__).resolve().parents[1]/'proposals/phase2-diagnostic-observation-v1/header_capture.py'
spec=importlib.util.spec_from_file_location('header_capture_candidate',PATH)
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
class Interrupted:
    def __init__(self,data,error):self.data=data;self.error=error;self.pos=0
    def read(self,n):
        if self.pos==len(self.data):raise self.error
        result=self.data[self.pos:self.pos+n];self.pos+=len(result);return result
    def readline(self,n):
        while self.pos<len(self.data):self.pos+=1
        raise self.error
class HeaderCaptureTests(unittest.TestCase):
    def test_timeout_preserves_partial_status(self):
        data=b'HTTP/1.1 200';captured=bytearray()
        with self.assertRaises(TimeoutError):candidate.read_bounded_line(Interrupted(data,TimeoutError('fixture')),captured,64)
        self.assertEqual(bytes(captured),data)
    def test_socket_error_preserves_partial_header(self):
        data=b'Content-Type: applic';captured=bytearray(b'HTTP/1.1 200 OK\r\n')
        with self.assertRaises(OSError):candidate.read_bounded_line(Interrupted(data,OSError('fixture')),captured,128)
        self.assertTrue(bytes(captured).endswith(data))
    def test_complete_line_exact(self):
        for line in [b'HTTP/1.1 200 OK\r\n',b'X: a\n',b'\r\n']:
            with self.subTest(line=line):
                buf=bytearray();self.assertEqual(candidate.read_bounded_line(io.BytesIO(line),buf,len(line)),line);self.assertEqual(bytes(buf),line)
    def test_cumulative_cap_never_reads_beyond_budget(self):
        fp=io.BytesIO(b'x'*100);buf=bytearray(b'prior')
        with self.assertRaises(RuntimeError):candidate.read_bounded_line(fp,buf,16)
        self.assertEqual(len(buf),16);self.assertEqual(fp.tell(),11)
    def test_empty_eof_is_preserved(self):
        buf=bytearray();self.assertEqual(candidate.read_bounded_line(io.BytesIO(),buf,16),b'');self.assertEqual(buf,b'')
    def test_partial_eof_is_retained_and_rejected(self):
        buf=bytearray()
        with self.assertRaises(RuntimeError):candidate.read_bounded_line(io.BytesIO(b'HTTP/1.1'),buf,16)
        self.assertEqual(buf,b'HTTP/1.1')
    def test_exhausted_cap_does_not_read(self):
        fp=io.BytesIO(b'new');buf=bytearray(b'full')
        with self.assertRaises(RuntimeError):candidate.read_bounded_line(fp,buf,4)
        self.assertEqual(fp.tell(),0);self.assertEqual(buf,b'full')
if __name__=='__main__':unittest.main()
