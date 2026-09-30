import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectContextProtocolTests(unittest.TestCase):
    def test_required_context_files_exist(self):
        for name in ("AGENTS.md", "PROJECT.md", "STATUS.md", "DECISIONS.md"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_context_check_script_passes(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_project_context.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
