import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.run_repeatability_pass import (
    EVAL_SCRIPT,
    PREFLIGHT_SCRIPT,
    SUMMARIZE_SCRIPT,
    run_repeatability_pass,
)


class TestRunRepeatabilityPass(unittest.TestCase):
    def test_preflight_failure_stops_before_run_one(self):
        calls = []

        def runner(script, args):
            calls.append((script, list(args)))
            if script == PREFLIGHT_SCRIPT:
                raise subprocess.CalledProcessError(returncode=2, cmd=str(script))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_result = tmp_path / "single_agent.json"
            outputs = [tmp_path / f"run{index}.json" for index in (1, 2, 3)]

            code = run_repeatability_pass(
                raw_result=raw_result,
                run_outputs=outputs,
                runner=runner,
                output_fn=lambda _line: None,
            )

            self.assertEqual(code, 2)
            self.assertEqual(calls, [(PREFLIGHT_SCRIPT, [])])
            self.assertFalse(any(path.exists() for path in outputs))

    def test_three_successful_runs_are_preserved_as_run1_run2_run3(self):
        calls = []
        eval_index = {"value": 0}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_result = tmp_path / "single_agent.json"
            outputs = [tmp_path / f"single_agent_qwen2.5_7b_run{index}.json" for index in (1, 2, 3)]
            summary_path = tmp_path / "summary.md"

            def runner(script, args):
                calls.append((script, list(args)))
                if script == EVAL_SCRIPT:
                    eval_index["value"] += 1
                    raw_result.write_text(f'{{"run": {eval_index["value"]}}}')

            code = run_repeatability_pass(
                raw_result=raw_result,
                run_outputs=outputs,
                summary_output=summary_path,
                runner=runner,
                output_fn=lambda _line: None,
            )

            self.assertEqual(code, 0)
            self.assertEqual(outputs[0].read_text(), '{"run": 1}')
            self.assertEqual(outputs[1].read_text(), '{"run": 2}')
            self.assertEqual(outputs[2].read_text(), '{"run": 3}')
            self.assertEqual(calls[0][0], PREFLIGHT_SCRIPT)
            self.assertEqual([script for script, _args in calls[1:4]], [EVAL_SCRIPT] * 3)
            self.assertEqual(calls[4][0], SUMMARIZE_SCRIPT)
            self.assertEqual(
                calls[4][1],
                [str(path) for path in outputs] + ["--output", str(summary_path)],
            )

    def test_existing_preserved_outputs_are_not_overwritten_without_force(self):
        calls = []

        def runner(script, args):
            calls.append((script, list(args)))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            outputs = [tmp_path / f"run{index}.json" for index in (1, 2, 3)]
            outputs[1].write_text("keep-me")

            code = run_repeatability_pass(
                run_outputs=outputs,
                runner=runner,
                output_fn=lambda _line: None,
            )

            self.assertEqual(code, 1)
            self.assertEqual(outputs[1].read_text(), "keep-me")
            self.assertEqual(calls, [])

    def test_failed_run_stops_later_runs_and_summary(self):
        calls = []
        eval_index = {"value": 0}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_result = tmp_path / "single_agent.json"
            outputs = [tmp_path / f"run{index}.json" for index in (1, 2, 3)]

            def runner(script, args):
                calls.append((script, list(args)))
                if script == EVAL_SCRIPT:
                    eval_index["value"] += 1
                    if eval_index["value"] == 2:
                        raise subprocess.CalledProcessError(returncode=3, cmd=str(script))
                    raw_result.write_text(f'{{"run": {eval_index["value"]}}}')

            code = run_repeatability_pass(
                raw_result=raw_result,
                run_outputs=outputs,
                runner=runner,
                output_fn=lambda _line: None,
            )

            self.assertEqual(code, 3)
            self.assertTrue(outputs[0].exists())
            self.assertFalse(outputs[1].exists())
            self.assertFalse(outputs[2].exists())
            self.assertNotIn(SUMMARIZE_SCRIPT, [script for script, _args in calls])

    def test_summary_runs_only_after_three_successful_runs(self):
        calls = []
        eval_index = {"value": 0}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_result = tmp_path / "single_agent.json"
            outputs = [tmp_path / f"run{index}.json" for index in (1, 2, 3)]

            def runner(script, args):
                calls.append((script, list(args)))
                if script == EVAL_SCRIPT:
                    eval_index["value"] += 1
                    raw_result.write_text(f'{{"run": {eval_index["value"]}}}')

            code = run_repeatability_pass(
                raw_result=raw_result,
                run_outputs=outputs,
                runner=runner,
                output_fn=lambda _line: None,
            )

            self.assertEqual(code, 0)
            summary_call_index = next(
                index for index, (script, _args) in enumerate(calls) if script == SUMMARIZE_SCRIPT
            )
            completed_eval_count = sum(
                1 for script, _args in calls[:summary_call_index] if script == EVAL_SCRIPT
            )
            self.assertEqual(completed_eval_count, 3)


if __name__ == "__main__":
    unittest.main()
