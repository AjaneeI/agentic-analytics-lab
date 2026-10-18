"""Actual client serialization under a fake HTTP transport; no live inference."""

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_schema_wire_delivery as wire


ROOT = Path(__file__).resolve().parents[2]


class TestWireGuards(unittest.TestCase):
    def test_dns_and_private_or_heldout_file_reads_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rejected = []
            # The outer deny prevents DNS even if the guard under test breaks.
            with patch.object(socket, 'getaddrinfo', side_effect=RuntimeError('outer offline guard')):
                with wire.offline_guards(root, rejected):
                    with self.assertRaises(wire.WireDeliveryMismatch):
                        socket.getaddrinfo('wire-fixture.invalid', 443)
                    for relative in ('evals/heldout_tasks.json', '.env', 'private/context.json'):
                        with self.subTest(relative=relative):
                            with self.assertRaises(wire.WireDeliveryMismatch):
                                (root / relative).read_text()
            self.assertEqual(len(rejected), 4)


class TestSchemaWireDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        available = subprocess.run(['git', 'cat-file', '-e', wire.APPROVED_COMMIT + '^{commit}'],
                                   cwd=ROOT, capture_output=True)
        if available.returncode:
            raise unittest.SkipTest('approved 644a68d source object unavailable; audit cannot substitute runtime/proposal expectations')

    def test_real_request_bytes_deliver_approved_tools_and_prompt_for_all_16_cases(self):
        report = wire.audit(ROOT, model_id='supplied-offline-wire-model')
        self.assertEqual(report['capture_count'], 16)
        self.assertTrue(report['wire_schema_delivery_verified'])
        self.assertFalse(report['runtime_equivalence_verified'])
        self.assertFalse(report['comparative_evaluation_approved'])
        self.assertEqual(report['rejected_attempts'], [])
        self.assertEqual(report['live_model_calls'], 0)
        self.assertEqual(report['external_database_calls'], 0)
        self.assertFalse(report['heldout_access'])
        self.assertEqual({row['lane'] for row in report['captures']}, {
            'strong_single', 'oracle_routed', 'natural_language_routed', 'simple_heuristic_routed'})
        self.assertEqual({row['probe_capability'] for row in report['captures']},
                         {'structured', 'documents', 'multi_source', 'none'})
        for row in report['captures']:
            with self.subTest(lane=row['lane'], profile=row['probe_capability']):
                payload = json.loads(row['request_data_utf8'])
                self.assertEqual(row['url'], 'http://127.0.0.1:11434/api/chat')
                self.assertEqual(row['method'], 'POST')
                self.assertEqual(payload['model'], 'supplied-offline-wire-model')
                self.assertEqual(payload['options'], {'temperature': 0, 'num_predict': 128, 'num_ctx': 2048})
                self.assertEqual(payload['keep_alive'], '30m')
                self.assertFalse(payload['stream'])
                self.assertTrue(row['wire_tool_schema_and_descriptions_match'])
                self.assertTrue(row['wire_messages_match'])
                self.assertTrue(row['hidden_metadata_canaries_absent'])
                self.assertEqual(row['evidence_tool_calls'], 0)
        self.assertEqual(report['phase2_qualification_source_request']['options'],
                         {'temperature': 0, 'num_predict': 512, 'num_ctx': 65536})
        self.assertFalse(report['wire_options_equal_phase2_qualification_source'])

    def test_audit_detects_actual_wire_tool_serialization_regression(self):
        from src.agents.ollama_client import OllamaModelClient
        with patch.object(OllamaModelClient, '_convert_tools', return_value=[]):
            with self.assertRaisesRegex(wire.WireDeliveryMismatch, 'wire tools'):
                wire.audit(ROOT)

    def test_audit_detects_actual_wire_prompt_serialization_regression(self):
        from src.agents.ollama_client import OllamaModelClient
        with patch.object(OllamaModelClient, '_convert_messages', return_value=[{'role': 'system', 'content': 'wrong fixture prompt'}]):
            with self.assertRaisesRegex(wire.WireDeliveryMismatch, 'wire messages'):
                wire.audit(ROOT)

    def test_cli_records_offline_status_and_does_not_overwrite_output(self):
        script = ROOT / 'scripts/audit_schema_wire_delivery.py'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'wire.json'
            command = [sys.executable, '-B', str(script), '--repository', str(ROOT), '--output', str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stderr)
            before = output.read_bytes()
            report = json.loads(before)
            self.assertEqual(report['status'], 'offline_wire_delivery_verified_not_runtime_equivalence')
            self.assertEqual(report['capture_count'], 16)
            refused = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 1)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
