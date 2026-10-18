"""Actual model-facing payload parity for existing System Benchmark paths."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest

from src.evals.system_benchmark.contracts import CapabilityProfile
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
from src.evals.system_benchmark.routing import oracle_route
from tests.system_benchmark.test_local_worker import ScriptedModel, final_payload

ROOT = Path(__file__).resolve().parents[2]


class TestSchemaDelivery(unittest.TestCase):
    def test_query_tool_payload_is_identical_across_existing_capability_paths(self):
        task = next(t for t in load_tasks(ROOT / 'evals/system_benchmark/development_tasks.json')
                    if t.case_id == 'SB-D01')
        payloads = []
        surfaces = {}
        for profile in CapabilityProfile:
            decision = replace(oracle_route(task), capability_profile=profile)
            class Capture(ScriptedModel):
                def respond(self, messages, tools):
                    surfaces[profile.value] = tools
                    return super().respond(messages, tools)
            model = Capture([{'type': 'final', 'content': final_payload()}])
            BoundedLocalExecutor(model=model, route_fn=lambda t: decision)(task, 1, None)
            query = [tool for tool in surfaces[profile.value] if tool['name'] == 'query_clickhouse']
            if profile in (CapabilityProfile.STRUCTURED, CapabilityProfile.MULTI_SOURCE):
                self.assertEqual(len(query), 1)
                payloads.append(json.dumps(query[0], sort_keys=True))
            else:
                self.assertEqual(query, [])
        self.assertEqual(payloads[0], payloads[1])
        self.assertIn('work_item_id String', payloads[0])
        self.assertIn('provenance, not a column', payloads[0])
        self.assertNotIn('17.8', payloads[0])
        self.assertEqual([t['name'] for t in surfaces['none']], [])
        self.assertEqual([t['name'] for t in surfaces['documents']], ['retrieve_policy'])


if __name__ == '__main__':
    unittest.main()
