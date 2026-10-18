"""Synthetic owned processes only. No live resource commands, SQL or models."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('resource_containment',HERE/'containment.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def held(path):
    with path.open('a+b') as stream:
        try:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(stream,fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True


def clean_owned(pids):
    for pid in pids:
        try: os.kill(pid,signal.SIGKILL)
        except ProcessLookupError: pass


class ContainmentTests(unittest.TestCase):
    def test_outer_timeout_terminates_active_command_and_grandchild(self):
        with tempfile.TemporaryDirectory() as folder:
            ids=Path(folder)/'owned-pids.json'
            command_lock=Path(folder)/'command.lock'
            child_lock=Path(folder)/'child.lock'
            child_ready=Path(folder)/'child.ready'
            child_code=("import fcntl,time;from pathlib import Path;"
                f"f=open({str(child_lock)!r},'w');fcntl.flock(f,fcntl.LOCK_EX);"
                f"Path({str(child_ready)!r}).write_text('ready');time.sleep(30)")
            command=("import os,subprocess,sys,json,time,fcntl;from pathlib import Path;"
                f"f=open({str(command_lock)!r},'w');fcntl.flock(f,fcntl.LOCK_EX);"
                f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
                f"deadline=time.monotonic()+2\nwhile not Path({str(child_ready)!r}).exists() and time.monotonic()<deadline:time.sleep(.005)\n"
                f"Path({str(ids)!r}).write_text(json.dumps([os.getpid(),child.pid]));time.sleep(30)")
            worker=("import importlib.util;"
                f"s=importlib.util.spec_from_file_location('c',{str(HERE/'containment.py')!r});"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                f"m.bounded_process({[sys.executable,'-c',command]!r},10,64)")
            pids=[]
            try:
                result=module.run_owned_worker([sys.executable,'-B','-c',worker],.8)
                self.assertTrue(ids.exists(),'synthetic descendants were not started; no containment evidence')
                pids=json.loads(ids.read_text())
                self.assertEqual(result['state'],'time_limit')
                self.assertTrue(child_ready.exists(),'grandchild did not acquire its synthetic lifetime lock')
                self.assertFalse(held(command_lock) or held(child_lock),'owned command/grandchild survived outer timeout')
                self.assertTrue(result['group_termination_confirmed'])
            finally:
                if ids.exists():pids=json.loads(ids.read_text())
                clean_owned(pids)

    def test_normal_worker_exit_also_cleans_abandoned_owned_child(self):
        with tempfile.TemporaryDirectory() as folder:
            ids=Path(folder)/'pid.json'
            child_lock=Path(folder)/'child.lock'
            child_code=("import fcntl,time;from pathlib import Path;"
                f"f=open({str(child_lock)!r},'w');fcntl.flock(f,fcntl.LOCK_EX);"
                f"Path({str(ids)!r}).write_text(str(__import__('os').getpid()));time.sleep(30)")
            worker=("import subprocess,sys,time;from pathlib import Path;"
                f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
                f"deadline=time.monotonic()+2\nwhile not Path({str(ids)!r}).exists() and time.monotonic()<deadline:time.sleep(.005)")
            pid=None
            try:
                result=module.run_owned_worker([sys.executable,'-c',worker],1)
                pid=int(ids.read_text())
                self.assertEqual(result['returncode'],0)
                self.assertFalse(held(child_lock),'abandoned owned child survived normal worker exit')
                self.assertTrue(result['group_termination_confirmed'])
            finally:
                if ids.exists():clean_owned([int(ids.read_text())])

    def test_per_command_timeout_preserves_returned_prefix(self):
        result=module.bounded_process([sys.executable,'-u','-c','import time;print("prefix",flush=True);time.sleep(5)'],.3,64)
        self.assertEqual(result['termination'],'time_limit')
        self.assertEqual(result['stdout'],b'prefix\n')
        self.assertLess(result['elapsed_seconds'],.5)

    def test_output_cap_retains_exact_prefix(self):
        result=module.bounded_process([sys.executable,'-c','import sys;sys.stdout.buffer.write(b"x"*2048)'],1,64)
        self.assertEqual(result['termination'],'output_limit')
        self.assertEqual(result['stdout'],b'x'*64)
        self.assertEqual(result['stderr'],b'')

    def test_worker_launch_failure_has_no_owned_group(self):
        result=module.run_owned_worker(['/definitely-missing-owned-synthetic-command'],1)
        self.assertEqual(result['state'],'launch_failed')
        self.assertIsNone(result['returncode'])
        self.assertTrue(result['group_termination_confirmed'])

    def test_first_error_stops_before_next_synthetic_source(self):
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/'must-not-exist'
            commands=[{'argv':[sys.executable,'-c','import sys;sys.stderr.write("fixture-error");sys.exit(7)'],'seconds':1,'cap':64},
                {'argv':[sys.executable,'-c',f'from pathlib import Path;Path({str(marker)!r}).touch()'],'seconds':1,'cap':64}]
            records,state=module.collect_sources(commands)
            self.assertEqual(state,'stopped_at_first_failed_source')
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]['returncode'],7)
            self.assertEqual(records[0]['stderr'],b'fixture-error')
            self.assertFalse(marker.exists())

    def test_command_launch_failure_is_terminal_without_second_source(self):
        records,state=module.collect_sources([
            {'argv':['/definitely-missing-owned-synthetic-command'],'seconds':1,'cap':64},
            {'argv':[sys.executable,'-c','raise AssertionError("must not launch")'],'seconds':1,'cap':64}])
        self.assertEqual(state,'stopped_at_first_failed_source')
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['termination'],'launch_failed')

    def test_unconfirmed_group_cleanup_never_reports_success(self):
        class Child:
            pid=999999
            def wait(self,timeout):return 0
        with patch.object(module.subprocess,'Popen',return_value=Child()), patch.object(module.os,'killpg'):
            result=module.run_owned_worker(['scripted-worker'],.01)
        self.assertFalse(result['group_termination_confirmed'])
        self.assertFalse(result['success'])


if __name__=='__main__':unittest.main()
