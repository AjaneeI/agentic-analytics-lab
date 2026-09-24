import tempfile
import unittest
from pathlib import Path

from src.evals.provenance import build_benchmark_provenance


class TestBenchmarkProvenance(unittest.TestCase):
    def test_fingerprint_is_deterministic_and_commit_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("alpha")
            (root / "b.txt").write_text("beta")

            first = build_benchmark_provenance(
                repository_root=root,
                contract_paths=("a.txt", "b.txt"),
                commit_sha="abc123",
            )
            second = build_benchmark_provenance(
                repository_root=root,
                contract_paths=("b.txt", "a.txt"),
                commit_sha="abc123",
            )

            self.assertEqual(first["git_commit_sha"], "abc123")
            self.assertEqual(
                first["benchmark_contract_sha256"],
                second["benchmark_contract_sha256"],
            )
            self.assertEqual(len(first["contract_files"]), 2)

    def test_missing_contract_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                build_benchmark_provenance(
                    repository_root=tmp,
                    contract_paths=("missing.txt",),
                    commit_sha="abc123",
                )


if __name__ == "__main__":
    unittest.main()
