import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT / "experiments" / "hermes-successor-ab-v1" / "frozen-state.json"
)


class TestHermesSuccessorManifest(unittest.TestCase):
    def test_manifest_freezes_required_benchmark_and_runtime_controls(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "hermes-successor-ab-v1")
        self.assertEqual(
            payload["repository"]["remediation_commits"],
            [
                "84263bfdadfd3f07a81ed7133456287e687146ba",
                "f596b5bebba5538d4eae09eee90b0861ab2d1b29",
            ],
        )
        self.assertEqual(payload["runtime"]["hermes"]["version"], "0.21.5+4410.g2ec7703")
        self.assertEqual(payload["runtime"]["model"]["name"], "hermes-local:qwen3.5-9b")
        self.assertEqual(payload["runtime"]["model"]["ollama_id"], "0df9cd2e3545")
        self.assertEqual(payload["runtime"]["context_length"], 65536)
        self.assertEqual(payload["runtime"]["opencode_version"], "2.0.20")
        self.assertEqual(payload["runtime"]["herdr_version"], "0.9.3")
        self.assertEqual(
            payload["repository"]["freeze_ref"],
            "refs/tags/hermes-successor-ab-v1.1",
        )
        self.assertEqual(
            payload["installed_state"]["visible_tools"],
            ["delegate_task", "query_clickhouse", "retrieve_policy"],
        )

        enforcement = payload["one_worker_enforcement"]
        self.assertEqual(enforcement["max_concurrent_children"], 1)
        self.assertFalse(enforcement["opencode_parallel_enabled"])
        self.assertEqual(enforcement["acceptance"]["deterministic_tests"], "10/10 passed")
        self.assertEqual(enforcement["acceptance"]["second_external_submit"], "worker_busy_exit_75")
        self.assertEqual(enforcement["acceptance"]["native_overlap"], "action_block")
        self.assertEqual(enforcement["acceptance"]["legitimate_worker"], "succeeded_exit_0")
        self.assertEqual(
            {asset["sha256"] for asset in enforcement["assets"]},
            {
                "42e236276edf0542c5ee4bcee83328f5f6e6d6b790a858a6345d184e3605bbae",
                "c2872f780794a7ba7edb00960d3ab7fb681754c18a016461a7d9161545e568b5",
                "d83b861f38e71a8ac1419c9d3fe18c51456ac4206b7a56b81e1480aed50fe969",
                "0a0e1c934ec7df3150814954c3b121e49b9eb0e7f150e25b83f28d9edad491fb",
            },
        )

        benchmark = payload["benchmark"]
        self.assertEqual(benchmark["task_id"], "SB-D01")
        self.assertEqual(
            benchmark["task"],
            "Identify the highest blocker-rate team and interpret it using the KPI definition without claiming causality.",
        )
        self.assertEqual(benchmark["treatment_order"], ["direct", "hermes"])
        self.assertEqual(benchmark["allowed_tools"], ["query_clickhouse", "retrieve_policy"])
        self.assertEqual(benchmark["response_contract"], "SystemBenchmarkResponse")
        self.assertEqual(benchmark["retry_policy"], "one_attempt_per_treatment_no_retries")
        self.assertEqual(benchmark["incremental_paid_spend_usd"], 0)
        self.assertEqual(benchmark["context_length"], 65536)
        self.assertEqual(benchmark["scorer"]["function"], "score_response")
        self.assertEqual(benchmark["scorer"]["reference_solution_id"], "REF-D01")
        self.assertEqual(
            benchmark["acceptance"],
            "existing deterministic scorer passes without manual output editing",
        )

    def test_manifest_hashes_the_contract_files_and_m0_probe(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["contract_sha256"],
            {
                "evals/system_benchmark/development_references.json": "24c73b0bb8af0bf7ccb0fd0e8c21d5b05ff523108e00d14770c668965b2aea74",
                "evals/system_benchmark/development_tasks.json": "d44f465672ca7428198d9af74c21dbe4e621750c1f2f60b45af69f278bb5b835",
                "experiments/hermes-successor-ab-v1/README.md": "bbe98c86df5c536e858a84b9fbef385be0b6961fce178642eb52ec8b9e7e8cf6",
                "experiments/hermes-successor-ab-v1/plugin/system-benchmark-tools/__init__.py": "68757db3f161e254750342e579f5f801e44fc5770690e5c62b0afe026102c290",
                "experiments/hermes-successor-ab-v1/plugin/system-benchmark-tools/plugin.yaml": "55206585af6581ce45b98bd67aad8edcfd27f7f46bbb4e02e12efb6db64110e0",
                "experiments/hermes-successor-ab-v1/profile/config.yaml": "b89cd933ca4b6531f3217832d5b1fac69d379235ef80b95e159982fe79fe8efc",
                "experiments/hermes-successor-ab-v1/run_benchmark.py": "881993b25f8d2e9aaa3bd1befde26c802d9600f36e2f09c60dd39fa179bb3c8b",
                "src/agents/single_agent.py": "2a6aed58041b95ceaef5a32431bded19322a81e5f2981a77e0caceb5a4df5793",
                "src/evals/system_benchmark/contracts.py": "dc3b26987725833d4a64f8b925e0813c79ee9dc7b7f600793a81a92f5773f1ed",
                "src/evals/system_benchmark/local_worker.py": "e2a5599d7a3c7ceb0a9378cdf818880d76ad264d996a0b6e5ab3392170199d7f",
                "src/evals/system_benchmark/scoring.py": "6d3d9c8743fabade1090a7cd9a8c428fb7bbcb5c2b5c605451ac1a6860029f7a",
                "src/tools/clickhouse_readonly.py": "9df96245e7e08d0f46d63e6b80aca9c9485075c39974de50a19ab436b76790b9",
                "src/tools/policy_retrieval.py": "551951170007f33fe898a6e8fe2e18fd17aa9ea7834ad992686fbeafbcd03e27",
            },
        )
        self.assertEqual(
            payload["m0_tool_contract_gate"],
            {
                "accepted_attempts": 3,
                "attempts": 3,
                "passed": True,
                "raw_report_path": "experiments/results/clickhouse-tool-contract-v1-2026-10-05.json",
                "raw_report_sha256": "18ff7dedf8417f150bc078197f0fb9cb9c9366b52877aec6d88d5eafef489399",
                "retries": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
