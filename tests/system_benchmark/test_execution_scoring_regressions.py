"""Scorer defects exposed by execution-level negative controls; no model calls."""
from dataclasses import replace
from pathlib import Path
import unittest

from src.evals.system_benchmark.contracts import (
    ResponseDisposition, StructuredExpectation, SystemBenchmarkResponse,
)
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.scoring import ScoringObservation, score_response

ROOT = Path(__file__).resolve().parents[2]

class TestExecutionScoringRegressions(unittest.TestCase):
    def pair(self, case_id):
        tasks = load_tasks(ROOT / 'evals/system_benchmark/development_tasks.json')
        refs = load_references(ROOT / 'evals/system_benchmark/development_references.json')
        task = next(t for t in tasks if t.case_id == case_id)
        return task, next(r for r in refs if r.reference_solution_id == task.reference_solution_id)

    def test_extra_wrong_version_fails_even_with_correct_version(self):
        task, ref = self.pair('SB-C02')
        response = SystemBenchmarkResponse(
            ResponseDisposition.ANSWER, 'Waited more than one business day.',
            ref.required_evidence_refs + ('policy:blocker-definition@1.0#blocked-item',),
        )
        result = score_response(task, ref, response, ScoringObservation(('retrieve_policy',)))
        self.assertFalse(result.passed)
        self.assertIn('wrong_policy_version', result.reason_codes)

    def test_bool_cannot_satisfy_numeric_expectation(self):
        task, ref = self.pair('SB-A01')
        task = replace(task, expected_values=(StructuredExpectation('count', 1),))
        response = SystemBenchmarkResponse(ResponseDisposition.ANSWER, 'Data', ref.required_evidence_refs)
        result = score_response(task, ref, response, ScoringObservation(('query_clickhouse',), {'count': True}))
        self.assertFalse(result.passed)
        self.assertIn('structured_value_mismatch', result.reason_codes)

    def test_enormous_integer_is_mismatch_not_overflow(self):
        task, ref = self.pair('SB-A01')
        task = replace(task, expected_values=(StructuredExpectation('count', 1),))
        response = SystemBenchmarkResponse(ResponseDisposition.ANSWER, 'Data', ref.required_evidence_refs)
        try:
            result = score_response(task, ref, response, ScoringObservation(('query_clickhouse',), {'count': 10**400}))
        except OverflowError:
            self.fail('An out-of-range observed integer must not crash the scorer')
        self.assertFalse(result.passed)
        self.assertIn('structured_value_mismatch', result.reason_codes)
