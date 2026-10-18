"""Run existing suite or candidate probes with live sockets and DNS denied."""
import argparse,os,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('repository',type=Path);p.add_argument('--focused',action='store_true');a=p.parse_args();r=a.repository.resolve();os.chdir(r);sys.path.insert(0,str(r))
def deny(*args,**kwargs):raise AssertionError('No live network, inference or SQL is authorized in timeout proposal tests')
with patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny),patch('socket.create_connection',deny),patch('socket.getaddrinfo',deny):
 suite=unittest.defaultTestLoader.discover('proposals/runtime-clickhouse-expression-jit-off-v1' if a.focused else 'tests',pattern='test_candidate_transport.py' if a.focused else 'test*.py')
 result=unittest.TextTestRunner(verbosity=2 if a.focused else 1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
