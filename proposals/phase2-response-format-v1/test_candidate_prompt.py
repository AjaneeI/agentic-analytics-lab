"""Run only in baseline RED or patched offline checkout; never do inference."""
import hashlib
import io
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from src.agents.ollama_client import OllamaModelClient
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor, _SYSTEM_PROMPT
from src.tools.policy_retrieval import PolicyEvidence

ROOT = Path(__file__).resolve().parents[2]
GUIDANCE = '''Response field types:
- disposition: one of "answer", "clarify", "unsupported", "handoff".
- answer_text: a non-empty JSON string.
- uncertainty: a JSON string or JSON null.
- clarification: a JSON object or JSON null.
- handoff: a JSON object or JSON null.
Use JSON null (without quotation marks) for clarification or handoff when inapplicable.
Do not substitute strings, booleans, arrays, or numbers for those object-or-null fields.'''


def denied(*args, **kwargs):
    raise AssertionError('Offline candidate checks forbid live network and service calls')


class TestCandidatePrompt(unittest.TestCase):
    def setUp(self):
        for name in ['socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection',
                     'socket.getaddrinfo', 'urllib.request.urlopen']:
            self.enterContext(patch(name, side_effect=denied))

    def test_explicit_field_type_guidance_is_delivered(self):
        self.assertIn(GUIDANCE, _SYSTEM_PROMPT)

    def test_original_prompt_prefix_and_no_answers_are_preserved(self):
        self.assertTrue(_SYSTEM_PROMPT.endswith(GUIDANCE))
        original = _SYSTEM_PROMPT[:-len(GUIDANCE)].rstrip()
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         json.loads((ROOT/'proposals/phase2-response-format-v1/manifest.json').read_text())['baseline_prompt_sha256'])
        for forbidden in ['17.8', '20.9', 'REF-D01', 'development_references', 'FixtureTeam']:
            self.assertNotIn(forbidden, GUIDANCE)

    def test_real_client_fake_http_preserves_tools_options_and_runtime_evidence(self):
        task = next(t for t in load_tasks(ROOT/'evals/system_benchmark/development_tasks.json') if t.case_id == 'SB-D01')
        sql = "SELECT team, 100.0 * SUM(blocked) / COUNT(*) AS blocked_pct FROM agentic_analytics.delivery_work_items WHERE status != 'done' GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"
        final = json.dumps({'disposition':'answer','answer_text':'Offline fixture response.',
            'uncertainty':None,'clarification':None,'handoff':None,
            'evidence_refs':['model:forged'],'observed_tools':['shell'],'observed_values':{'team':'Forged'}})
        replies = [
            {'message':{'tool_calls':[{'function':{'name':'query_clickhouse','arguments':{'sql':sql}}}]}},
            {'message':{'tool_calls':[{'function':{'name':'retrieve_policy','arguments':{'query':'offline policy definition'}}}]}},
            {'message':{'content':final}},
        ]
        requests, calls = [], []
        def http(request, timeout):
            body = json.loads(request.data)
            self.assertIn(GUIDANCE, body['messages'][0]['content'])
            self.assertEqual(body['messages'][0], {'role':'system','content':_SYSTEM_PROMPT})
            self.assertEqual(body['model'], 'hermes-local:qwen3.5-9b')
            self.assertEqual(body['options'], {'temperature':0,'num_predict':512,'num_ctx':65536})
            self.assertEqual(body['keep_alive'], '30m')
            self.assertFalse(body['stream'])
            self.assertNotIn('format', body)
            self.assertEqual(timeout, 120)
            self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
            self.assertEqual(request.method, 'POST')
            self.assertEqual([t['function']['name'] for t in body['tools']], ['query_clickhouse','retrieve_policy'])
            tool = body['tools'][0]['function']
            normalized = {'name':tool['name'],'description':tool['description'],'input_schema':tool['parameters']}
            self.assertEqual(hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                             '0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9')
            requests.append(body)
            return io.BytesIO(json.dumps(replies.pop(0)).encode())
        def query(actual):
            self.assertEqual(actual, sql)
            calls.append('query_clickhouse')
            return [{'team':'FixtureTeam','blocked_pct':12.5}]
        def policy(**kwargs):
            self.assertEqual(kwargs, {'query':'offline policy definition'})
            calls.append('retrieve_policy')
            return [PolicyEvidence(document_id='fixture-policy', document_version='1.0',
                effective_date='2026-01-01', section_id='definition',
                excerpt='Offline definition.', status='current')]
        with patch('urllib.request.urlopen', side_effect=http):
            execution = BoundedLocalExecutor(model=OllamaModelClient(model='hermes-local:qwen3.5-9b'),
                query_fn=query, policy_fn=policy)(task,1,None)
        self.assertEqual(len(requests),3)
        self.assertEqual(calls,['query_clickhouse','retrieve_policy'])
        self.assertEqual(execution.model_calls,3)
        self.assertEqual(execution.observation.tool_calls,tuple(calls))
        self.assertEqual(execution.observation.structured_values['team'],'FixtureTeam')
        self.assertEqual(execution.observation.structured_values['blocked_pct'],12.5)
        self.assertEqual(execution.observation.structured_values['scope'],'active_work_items')
        self.assertEqual(execution.response.evidence_refs,('structured:delivery_work_items','policy:fixture-policy@1.0#definition'))
        self.assertEqual(execution.response.clarification,None)
        self.assertEqual(execution.response.handoff,None)
        for body in requests:
            text=json.dumps(body['messages'][:2])
            for canary in ['REF-D01','20.9','17.8','model:forged']:
                self.assertNotIn(canary,text)


if __name__=='__main__':
    unittest.main()
