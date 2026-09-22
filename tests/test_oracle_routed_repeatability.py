import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.run_oracle_routed_repeatability import (
    EVAL_SCRIPT,
    PREFLIGHT_SCRIPT,
    SUMMARIZE_SCRIPT,
    run_oracle_routed_repeatability_pass,
)


class TestOracleRoutedRepeatability(unittest.TestCase):
    def test_preflight_failure_stops_before_first_routed_run(self):
        calls = []

        def runner(script, args):
            calls.append((script, list(args)))
            if script == PREFLIGHT_SCRIPT:
                raise subprocess.CalledProcessError(
                    returncode=2,
                    cmd=str(script),
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            outputs = [tmp / f"run{index}.json" for index in (1, 2, 3)]

            code = run_oracle_routed_repeatability_pass(
                raw_result=tmp / "raw.json",
                run_outputs=outputs,
                runner=runner,
                output_fn=lambda _line: None,
            )

        self.assertEqual(code, 2)
        self.assertEqual(calls, [(PREFLIGHT_SCRIPT, [])])

    def test_three_runs_are_preserved_then_summarized(self):
        calls = []
        run_index = {"value": 0}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raw = tmp / "raw.json"
            outputs = [tmp / f"run{index}.json" for index in (1, 2, 3)]
            summary = tmp / "summary.md"

            def runner(script, args):
                calls.append((script, list(args)))
                if script == EVAL_SCRIPT:
                    run_index["value"] += 1
                    raw.write_text(
                        f'{{"run": {run_index["value"]}}}'
                    )

            code = run_oracle_routed_repeatability_pass(
                raw_result=raw,
                run_outputs=outputs,
                summary_output=summary,
                runner=runner,
                output_fn=lambda _line: None,
            )

            self.assertEqual(code, 0)
            self.assertEqual(
                [path.read_text() for path in outputs],
                ['{"run": 1}', '{"run": 2}', '{"run": 3}'],
            )
            self.assertEqual(calls[0][0], PREFLIGHT_SCRIPT)
            self.assertEqual(
                [script for script, _args in calls[1:4]],
                [EVAL_SCRIPT] * 3,
            )
            self.assertEqual(calls[4][0], SUMMARIZE_SCRIPT)
            self.assertEqual(
                calls[4][1],
                [str(path) for path in outputs]
                + [
                    "--output",
                    str(summary),
                    "--title",
                    "Oracle-Metadata Routed Repeatability Summary",
                ],
            )

    def test_existing_runs_require_force(self):
        calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            outputs = [tmp / f"run{index}.json" for index in (1, 2, 3)]
            outputs[0].write_text("preserve")

            code = run_oracle_routed_repeatability_pass(
                run_outputs=outputs,
                runner=lambda script, args: calls.append((script, args)),
                output_fn=lambda _line: None,
            )

        self.assertEqual(code, 1)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
