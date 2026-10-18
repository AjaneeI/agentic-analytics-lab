"""Existing strict parser behavior, using fabricated offline envelopes only."""
import json
import unittest

from src.evals.system_benchmark.local_worker import LocalWorkerError, _parse_final_response


class TestResponseFormatContract(unittest.TestCase):
    def parse(self, **extra):
        payload = {'disposition': 'answer', 'answer_text': 'Offline fixture response.'}
        payload.update(extra)
        return _parse_final_response(json.dumps(payload), evidence_refs=('runtime:fixture',))

    def test_optional_fields_omitted_remain_none(self):
        response = self.parse()
        self.assertIsNone(response.uncertainty)
        self.assertIsNone(response.clarification)
        self.assertIsNone(response.handoff)

    def test_explicit_null_fields_remain_none(self):
        response = self.parse(uncertainty=None, clarification=None, handoff=None)
        self.assertIsNone(response.clarification)
        self.assertIsNone(response.handoff)

    def test_objects_are_preserved_without_coercion_or_new_schema(self):
        clarification = {'question': 'Offline clarification.'}
        handoff = {'fixture': {'nested': True}}
        response = self.parse(clarification=clarification, handoff=handoff)
        self.assertEqual(response.clarification, clarification)
        self.assertEqual(response.handoff, handoff)
        self.assertEqual(self.parse(clarification={}, handoff={}).handoff, {})

    def test_clarification_rejects_all_non_object_non_null_types(self):
        for value in ['null', 'none', '', 'Offline string', True, False, [], [None], 0, 1.5]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(LocalWorkerError, '^clarification must be an object or null$'):
                    self.parse(clarification=value)

    def test_handoff_rejects_all_non_object_non_null_types(self):
        for value in ['null', 'none', '', 'Offline string', True, False, [], [None], 0, 1.5]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(LocalWorkerError, '^handoff must be an object or null$'):
                    self.parse(handoff=value)

    def test_uncertainty_preserves_string_or_null_boundary(self):
        self.assertEqual(self.parse(uncertainty='Offline uncertainty.').uncertainty, 'Offline uncertainty.')
        for value in [{}, [], True, 1]:
            with self.subTest(value=value), self.assertRaisesRegex(LocalWorkerError, 'uncertainty must be a string or null'):
                self.parse(uncertainty=value)

    def test_all_existing_dispositions_remain_parseable(self):
        for disposition in ['answer', 'clarify', 'unsupported', 'handoff']:
            with self.subTest(disposition=disposition):
                self.assertEqual(self.parse(disposition=disposition).disposition.value, disposition)

    def test_evidence_refs_remain_runtime_generated(self):
        response = self.parse(evidence_refs=['model:forged'], observed_tools=['shell'], observed_values={'fake': 99})
        self.assertEqual(response.evidence_refs, ('runtime:fixture',))

    def test_answer_and_disposition_validation_remain_strict(self):
        for value in ['', ' ', None, 1]:
            with self.subTest(value=value), self.assertRaisesRegex(LocalWorkerError, 'answer_text must be a non-empty string'):
                self.parse(answer_text=value)
        with self.assertRaisesRegex(LocalWorkerError, 'invalid response disposition'):
            self.parse(disposition='invented')


if __name__ == '__main__':
    unittest.main()
