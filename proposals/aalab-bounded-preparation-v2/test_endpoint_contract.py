"""Deterministic synthetic metadata controls; no benchmark outcomes or execution."""
import copy
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from types import ModuleType
import unittest
from unittest.mock import patch


def synthetic_metadata():
    expected = []
    for family in 'ABCDEFGH':
        for repeat in (1, 2, 3):
            for arm in ('baseline', 'candidate'):
                expected.append(dict(task_id=f'SYN-V2-{family}', task_version='synthetic-v2',
                    family=family, arm=arm, repeat_id=repeat, block_id=f'paired-{repeat}',
                    n_family=1, synthetic=True, metadata_approved=True))
    observed = [dict((k, row[k]) for k in IDENTITY) |
                dict(status='scored_success', scored=True, success=True) for row in expected]
    return expected, observed


UNSET = object()

IDENTITY = ('task_id', 'task_version', 'family', 'arm', 'repeat_id', 'block_id')


def load_evaluator():
    retained = sys.modules.get('endpoint_contract')
    if retained is not None:
        return retained.evaluate_metadata
    source = Path(__file__).with_name('endpoint_contract.py')
    if not source.exists():
        return None
    module = ModuleType('inactive_endpoint_contract')
    module.__file__ = str(source)
    exec(compile(source.read_bytes(), str(source), 'exec'), module.__dict__)
    return module.evaluate_metadata


class MetadataContractTests(unittest.TestCase):
    def setUp(self):
        # Guards are installed before importing the candidate. Any actual call fails.
        self.guards = [patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')),
                       patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')),
                       patch.object(subprocess, 'Popen', side_effect=AssertionError('subprocess forbidden')),
                       patch.object(subprocess, 'run', side_effect=AssertionError('subprocess forbidden')),
                       patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL forbidden'))]
        for guard in self.guards:
            guard.start()
            self.addCleanup(guard.stop)
        self.evaluate = load_evaluator()
        self.assertIsNotNone(self.evaluate, 'inactive metadata contract has not been implemented')
        self.expected, self.observed = synthetic_metadata()

    def assert_withheld(self, expected=UNSET, observed=UNSET):
        result = self.evaluate(self.expected if expected is UNSET else expected,
                               self.observed if observed is UNSET else observed)
        self.assertFalse(result['eligible_for_primary'])
        self.assertIsNone(result['aggregate'])
        self.assertFalse(result['live_qualified'])
        self.assertTrue(result['inactive'])
        self.assertTrue(result['reasons'])
        return result

    def test_complete_synthetic_metadata_is_valid_but_computes_no_estimate(self):
        before = copy.deepcopy((self.expected, self.observed))
        result = self.evaluate(self.expected, self.observed)
        self.assertTrue(result['metadata_valid'])
        self.assertTrue(result['eligible_for_primary'])
        self.assertEqual(result['weights'], {f'SYN-V2-{f}': {'numerator': 1, 'denominator': 8} for f in 'ABCDEFGH'})
        self.assertIsNone(result['aggregate'])
        self.assertTrue(result['inactive'])
        self.assertFalse(result['live_qualified'])
        self.assertEqual(before, (self.expected, self.observed))

    def test_imbalanced_complete_families_use_symbolic_task_weights(self):
        expected, observed = synthetic_metadata()
        extra = [dict(r, task_id='SYN-V2-A-extra') for r in expected if r['family'] == 'A']
        for r in expected + extra:
            if r['family'] == 'A':
                r['n_family'] = 2
        expected += extra
        observed += [dict((k, r[k]) for k in IDENTITY) | dict(status='scored_failure', scored=True, success=False) for r in extra]
        result = self.evaluate(expected, observed)
        self.assertTrue(result['eligible_for_primary'])
        self.assertEqual(result['weights']['SYN-V2-A'], {'numerator': 1, 'denominator': 16})
        self.assertEqual(result['weights']['SYN-V2-A-extra'], {'numerator': 1, 'denominator': 16})
        self.assertIsNone(result['aggregate'])

    def test_all_unscored_statuses_remain_null_and_withhold(self):
        for status in ('not_started', 'started_timeout', 'transport_error', 'worker_error', 'contract_error', 'scorer_error'):
            with self.subTest(status=status):
                rows = copy.deepcopy(self.observed)
                rows[0].update(status=status, scored=False, success=None)
                if status == 'started_timeout':
                    rows[0].update(elapsed_seconds=15.0, stage='response', artifact_available=False)
                result = self.assert_withheld(observed=rows)
                self.assertEqual(result['status_counts'][status], 1)
                self.assertEqual(result['unscored_count'], 1)
                self.assertEqual(rows[0]['success'], None)

    def test_timeout_preserves_actual_interpretable_boolean(self):
        for value in (True, False):
            rows = copy.deepcopy(self.observed)
            rows[0].update(status='started_timeout', scored=True, success=value,
                           elapsed_seconds=15, stage='post-response', artifact_available=True)
            result = self.evaluate(self.expected, rows)
            self.assertTrue(result['eligible_for_primary'])
            self.assertEqual(rows[0]['success'], value)
            self.assertEqual(result['scored_count'], 48)
            self.assertIsNone(result['aggregate'])

    def test_scored_false_is_not_missing(self):
        self.observed[0].update(status='scored_failure', success=False)
        self.assertTrue(self.evaluate(self.expected, self.observed)['eligible_for_primary'])

    def test_missing_duplicate_extra_and_unknown_identities_withhold(self):
        self.assert_withheld(observed=self.observed[:-1])
        self.assert_withheld(observed=self.observed + [self.observed[0].copy()])
        self.assert_withheld(expected=self.expected + [self.expected[0].copy()])
        for key, value in [('task_id', 'EXTRA'), ('family', 'Z'), ('arm', 'third'), ('task_version', 'other'), ('block_id', 'unmatched'), ('repeat_id', 9)]:
            with self.subTest(key=key):
                rows = copy.deepcopy(self.observed)
                rows[0][key] = value
                self.assert_withheld(observed=rows)

    def test_host_roster_missing_family_or_pair_is_invalid(self):
        for missing in ('B', 'F'):
            expected = [r for r in self.expected if r['family'] != missing]
            observed = [r for r in self.observed if r['family'] != missing]
            self.assert_withheld(expected=expected, observed=observed)
        self.assert_withheld(expected=self.expected[:-1], observed=self.observed[:-1])

    def test_host_roster_misaligned_blocks_and_family_count_rejected(self):
        for key, value in [('block_id', 'other-block'), ('family', 'B'), ('task_version', 'other'), ('n_family', 2)]:
            expected = copy.deepcopy(self.expected)
            expected[0][key] = value
            self.assert_withheld(expected=expected)

    def test_types_boolean_counts_and_undeclared_fields_are_invalid(self):
        for key, value in [('repeat_id', True), ('repeat_id', 0), ('n_family', True), ('n_family', 0), ('task_id', 7), ('synthetic', 1), ('metadata_approved', False), ('unexpected', 'field')]:
            expected = copy.deepcopy(self.expected)
            expected[0][key] = value
            self.assert_withheld(expected=expected)
        for key, value in [('repeat_id', True), ('scored', 1), ('success', 1), ('status', 'unknown'), ('unexpected', 'field')]:
            observed = copy.deepcopy(self.observed)
            observed[0][key] = value
            self.assert_withheld(observed=observed)
        for value in (None, {}, 'rows', [None], [True]):
            self.assert_withheld(expected=value)
            self.assert_withheld(observed=value)
        self.assert_withheld(expected=[])

    def test_status_score_contradictions_and_timeout_metadata_rejected(self):
        for changes in [dict(status='scored_success', success=False), dict(status='scored_failure', success=True),
                        dict(scored=False), dict(success=None), dict(status='transport_error'),
                        dict(status='started_timeout'),
                        dict(status='started_timeout', elapsed_seconds=True, stage='wait', artifact_available=True),
                        dict(status='started_timeout', elapsed_seconds=-1, stage='wait', artifact_available=True),
                        dict(status='started_timeout', elapsed_seconds=float('nan'), stage='wait', artifact_available=True),
                        dict(status='started_timeout', elapsed_seconds=15, stage='', artifact_available=True),
                        dict(status='started_timeout', elapsed_seconds=15, stage='wait', artifact_available=False)]:
            observed = copy.deepcopy(self.observed)
            observed[0].update(changes)
            self.assert_withheld(observed=observed)

    def test_same_task_arm_repeat_cannot_appear_in_two_blocks(self):
        expected = copy.deepcopy(self.expected)
        observed = copy.deepcopy(self.observed)
        alternate = dict(expected[0], block_id='alternate')
        # Arrange the original last: an overwrite-based pair check would miss it.
        expected.insert(0, alternate)
        observed.insert(0, dict(observed[0], block_id='alternate'))
        self.assert_withheld(expected=expected, observed=observed)

    def test_root_retained_source_module_takes_precedence(self):
        retained = ModuleType('endpoint_contract')
        retained.evaluate_metadata = lambda expected, observed: {'retained': True}
        with patch.dict(sys.modules, {'endpoint_contract': retained}):
            self.assertIs(load_evaluator(), retained.evaluate_metadata)

    def test_standalone_fallback_compiles_fresh_source_bytes(self):
        source_bytes = b'def evaluate_metadata(expected, observed): return "fresh_source_bytes"'
        with patch.dict(sys.modules):
            sys.modules.pop('endpoint_contract', None)
            with patch.object(Path, 'exists', return_value=True), patch.object(Path, 'read_bytes', autospec=True, return_value=source_bytes) as read_source:
                evaluator = load_evaluator()
                read_source.assert_called_once()
                self.assertEqual(evaluator(None, None), 'fresh_source_bytes')

    def test_oversized_timeout_numeric_is_withheld_without_exception(self):
        rows = copy.deepcopy(self.observed)
        rows[0].update(status='started_timeout', scored=True, success=True,
                       elapsed_seconds=10**400, stage='response', artifact_available=True)
        result = self.assert_withheld(observed=rows)
        self.assertIn('invalid_timeout_metadata:0', result['reasons'])

    def test_no_silent_repair_or_default_replacement(self):
        rows = copy.deepcopy(self.observed)
        del rows[0]['success']
        result = self.assert_withheld(observed=rows)
        self.assertNotIn('success', rows[0])
        self.assertEqual(result['weights'], {})
        self.assertEqual(result['new_attempts'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
