import socket,sys,unittest
from unittest.mock import patch
import jit_one_attempt_preflight as p
class CsvPinGuard(unittest.TestCase):
    def test_changed_seed_csv_refuses_before_source_gate(self):
        with patch.object(p,'sha',return_value='0'*64):
            with self.assertRaisesRegex(AssertionError,'seed42 CSV'):
                p.source()
    def test_original_csv_and_pinned_sources_pass(self):
        self.assertTrue(p.source()['execution_ready'])
if __name__=='__main__':
    def deny(*a,**k):raise AssertionError('No network or DNS in offline CSV pin test')
    with patch.object(socket.socket,'connect',deny),patch('socket.getaddrinfo',deny):unittest.main(verbosity=2)
