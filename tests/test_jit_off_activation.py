"""Separate exact JIT-off activation from live experiment authorization offline."""
import unittest
from unittest.mock import Mock,patch
from tests import test_qualify_phase2_once as fixtures
from scripts import qualify_phase2_once as runner
from scripts import passive_capture as capture

class TestJitOffActivation(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.TestQualificationRunner('test_run_and_approval_reference_are_mandatory');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.fixture.config.update(configuration_id='phase2-runtime-schema-v1-scope-observation-v1-response-format-v1-expression-jit-off-v1',
            response_format_version='phase2-response-format-v1',response_format_activation_approval='approved',
            response_format_prompt_sha256='56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce',
            runtime_transport_version='runtime-clickhouse-expression-jit-off-v1',runtime_activation_approval='approved',
            clickhouse_request_settings_amendment={'compile_expressions':'0'},
            clickhouse_transport_sha256='aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c',
            clickhouse_client_timeout_seconds=15,
            clickhouse_fixed_request_parameters={'default_format':'JSONEachRow','readonly':'1','max_execution_time':'10','max_result_rows':'1000','result_overflow_mode':'break','max_rows_to_read':'10000','max_bytes_to_read':'10485760','max_memory_usage':'134217728','max_threads':'2','compile_expressions':'0'},
            live_treatment_a_authorization='not_granted',authorized_live_attempts=0)
        self.fixture.pin()
    def inspect(self):return runner.source_preflight(self.fixture.request)
    def test_exact_activation_ready_while_live_execution_is_blocked(self):
        inspected=self.inspect();self.assertTrue(inspected.get('activation_ready',False));self.assertEqual(inspected['execution_blockers'],['live_treatment_a_not_authorized']);self.assertFalse(inspected['execution_ready'])
    def test_activation_approval_never_reaches_task_services_model_or_output(self):
        self.assertIn('live_treatment_a_not_authorized',self.inspect()['execution_blockers'])
        with patch.object(runner,'_task_boundary',side_effect=AssertionError('must not load task')) as task:
            with self.assertRaises(capture.CaptureRefused):runner.qualify_once(self.fixture.request,self.fixture.out,model_factory=Mock(side_effect=AssertionError('must not construct model')))
        task.assert_not_called();self.assertFalse(self.fixture.out.exists())
    def test_wrong_jit_setting_blocks_activation(self):
        self.fixture.config['clickhouse_request_settings_amendment']={'compile_expressions':'1'};self.fixture.pin();self.assertIn('jit_off_transport_configuration_differs',self.inspect().get('activation_blockers',[]))
    def test_wrong_transport_pin_blocks_activation(self):
        self.fixture.config['clickhouse_transport_sha256']='0'*64;self.fixture.pin();self.assertIn('jit_off_transport_configuration_differs',self.inspect().get('activation_blockers',[]))
    def test_unapproved_activation_blocks(self):
        self.fixture.config['runtime_activation_approval']='not_granted';self.fixture.pin();self.assertIn('jit_off_transport_configuration_differs',self.inspect().get('activation_blockers',[]))
    def test_response_format_approval_is_still_required(self):
        self.fixture.config['response_format_activation_approval']='not_granted';self.fixture.pin();self.assertIn('response_format_version_or_approval_differs',self.inspect().get('activation_blockers',[]))
    def test_count_without_separate_live_approval_does_not_enable_execution(self):
        self.fixture.config['authorized_live_attempts']=1;self.fixture.pin();self.assertIn('live_treatment_a_not_authorized',self.inspect()['execution_blockers'])
    def test_changed_client_wait_blocks_activation(self):
        self.fixture.config['clickhouse_client_timeout_seconds']=16;self.fixture.pin();self.assertIn('jit_off_transport_configuration_differs',self.inspect().get('activation_blockers',[]))
    def test_changed_resource_limit_blocks_activation(self):
        self.fixture.config['clickhouse_fixed_request_parameters']['max_threads']='3';self.fixture.pin();self.assertIn('jit_off_transport_configuration_differs',self.inspect().get('activation_blockers',[]))
    def test_boolean_is_not_an_authorized_attempt_count(self):
        self.fixture.config.update(live_treatment_a_authorization='approved',authorized_live_attempts=True);self.fixture.pin();self.assertIn('live_treatment_a_not_authorized',self.inspect()['execution_blockers'])
    def test_future_separate_authorization_fixture_passes_offline_source_gate_only(self):
        self.fixture.config.update(live_treatment_a_authorization='approved',authorized_live_attempts=1);self.fixture.pin();self.assertTrue(self.inspect().get('activation_ready',False));self.assertTrue(self.inspect().get('execution_ready',False));self.assertEqual(self.inspect()['execution_blockers'],[])

if __name__=='__main__':unittest.main()
