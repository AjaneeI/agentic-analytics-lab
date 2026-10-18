"""Offline activation guards only; no live service or experimental execution."""
import unittest
from unittest.mock import Mock, patch
from tests import test_qualify_phase2_once as fixtures
from scripts import qualify_phase2_once as runner
from scripts import passive_capture as capture


class TestResponseFormatActivation(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TestQualificationRunner('test_run_and_approval_reference_are_mandatory')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.config.update(
            configuration_id='phase2-runtime-schema-v1-scope-observation-v1-response-format-v1',
            response_format_version='phase2-response-format-v1',
            response_format_activation_approval='approved',
            response_format_prompt_sha256='56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce')
        self.fixture.pin()

    def test_exact_approved_response_format_configuration_passes_source_checks(self):
        self.assertEqual(runner.source_preflight(self.fixture.request)['execution_blockers'], [])

    def test_pending_response_format_approval_refuses_before_runtime_or_services(self):
        self.fixture.config['response_format_activation_approval']='not_granted'
        self.fixture.pin()
        self.assertIn('response_format_version_or_approval_differs',runner.source_preflight(self.fixture.request)['execution_blockers'])
        with patch.object(runner,'_task_boundary',side_effect=AssertionError('must not enter runtime')) as task:
            with self.assertRaises(capture.CaptureRefused):
                runner.qualify_once(self.fixture.request,self.fixture.out,model_factory=Mock(side_effect=AssertionError('must not construct model')))
        task.assert_not_called()
        self.assertFalse(self.fixture.out.exists())

    def test_prompt_hash_mismatch_refuses(self):
        self.fixture.config['response_format_prompt_sha256']='0'*64
        self.fixture.pin()
        self.assertIn('response_format_prompt_sha256_differs',runner.source_preflight(self.fixture.request)['execution_blockers'])

    def test_wrong_response_format_version_refuses(self):
        self.fixture.config['response_format_version']='unapproved-version'
        self.fixture.pin()
        self.assertIn('response_format_version_or_approval_differs',runner.source_preflight(self.fixture.request)['execution_blockers'])
