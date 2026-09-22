"""Run frozen Q1-Q6 against the oracle-metadata routed v0 architecture."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.runner import run_case, save_results
from src.routing.oracle_benchmark import OracleMetadataRoutedAgent


MODEL = "qwen2.5:7b"
QUESTIONS_PATH = Path("evals/questions.json")
DESTINATION = Path(
    "experiments/results/oracle_metadata_routed_v0_qwen2.5_7b.json"
)

questions = json.loads(QUESTIONS_PATH.read_text())

local_worker = SingleAgent(
    OllamaModelClient(model=MODEL),
    max_steps=3,
)
agent = OracleMetadataRoutedAgent(
    questions=questions,
    local_worker=local_worker,
)

records = []

print("Architecture: oracle_metadata_routed_v0", flush=True)
print(f"Local model: {MODEL}", flush=True)
print(f"Questions: {len(questions)}", flush=True)

for index, case in enumerate(questions, 1):
    print(
        f"\n=== Running {case['id']} ({index}/{len(questions)}) ===",
        flush=True,
    )

    record = run_case(agent, case)
    records.append(record)

    route = agent.route_telemetry_by_task.get(case["id"])
    print(
        f"{case['id']} complete | "
        f"route={route.route if route else 'unknown'} | "
        f"execution={record.execution_success} | "
        f"correct={record.correct} | "
        f"task_success={record.task_success} | "
        f"latency={record.latency_seconds}s | "
        f"model_calls={record.model_call_count} | "
        f"tools={record.tool_call_count}",
        flush=True,
    )

save_results(records, DESTINATION)
payload = json.loads(DESTINATION.read_text())

for result in payload["results"]:
    telemetry = agent.route_telemetry_by_task.get(result["question_id"])
    result["route_telemetry"] = (
        asdict(telemetry) if telemetry is not None else None
    )

route_records = list(agent.route_telemetry_by_task.values())
payload["routing_summary"] = {
    "router_version": "oracle-metadata-rules-v0",
    "route_counts": {
        route: sum(record.route == route for record in route_records)
        for route in ("deterministic", "local", "escalate")
    },
    "pre_execution_escalations": sum(
        record.escalation_reason is not None for record in route_records
    ),
    "worker_input_tokens": sum(
        record.worker_input_tokens for record in route_records
    ),
    "worker_output_tokens": sum(
        record.worker_output_tokens for record in route_records
    ),
}

payload["metadata"] = {
    "benchmark_schema_version": 2,
    "architecture": "oracle_metadata_routed_v0",
    "model": MODEL,
    "provider": "deterministic_plus_ollama_local",
    "api_cost_usd": 0,
    "local_compute_cost_usd": None,
    "dataset": "synthetic_delivery_seed_42",
    "questions": str(QUESTIONS_PATH),
    "run_at_utc": datetime.now(timezone.utc).isoformat(),
    "routing_source": "frozen_case_category_and_requires_tool_metadata",
    "routing_claim_boundary": (
        "This experiment uses oracle benchmark metadata and does not measure "
        "natural-language route inference."
    ),
    "cost_note": (
        "Deterministic handlers have no model API charge. Ollama has no "
        "per-request API charge. Local/runner compute cost is not estimated."
    ),
}

DESTINATION.write_text(json.dumps(payload, indent=2) + "\n")

print("\n=== EVALUATION SUMMARY ===", flush=True)
print(json.dumps(payload["summary"], indent=2), flush=True)
print("\n=== ROUTING SUMMARY ===", flush=True)
print(json.dumps(payload["routing_summary"], indent=2), flush=True)
print(f"\nSaved raw result: {DESTINATION}", flush=True)
