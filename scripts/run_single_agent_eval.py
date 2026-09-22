"""Run the frozen evaluation suite against the Qwen 2.5 7B single-agent baseline."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.runner import run_case, save_results


MODEL = "qwen2.5:7b"
QUESTIONS_PATH = Path("evals/questions.json")
DESTINATION = Path("experiments/results/single_agent_qwen2.5_7b.json")

questions = json.loads(QUESTIONS_PATH.read_text())

agent = SingleAgent(
    OllamaModelClient(model=MODEL),
    max_steps=3,
)

records = []

print(f"Model: {MODEL}", flush=True)
print(f"Questions: {len(questions)}", flush=True)

for index, case in enumerate(questions, 1):
    print(
        f"\n=== Running {case['id']} ({index}/{len(questions)}) ===",
        flush=True,
    )

    record = run_case(agent, case)
    records.append(record)

    print(
        f"{case['id']} complete | "
        f"execution={record.execution_success} | "
        f"correct={record.correct} | "
        f"task_success={record.task_success} | "
        f"latency={record.latency_seconds}s | "
        f"model_calls={record.model_call_count} | "
        f"tools={record.tool_call_count}",
        flush=True,
    )

    if record.failure_type:
        print(f"Failure type: {record.failure_type}", flush=True)
    if record.error:
        print(f"Error: {record.error}", flush=True)

save_results(records, DESTINATION)

payload = json.loads(DESTINATION.read_text())

payload["metadata"] = {
    "benchmark_schema_version": 2,
    "architecture": "single_agent",
    "model": MODEL,
    "provider": "ollama_local",
    "api_cost_usd": 0,
    "local_compute_cost_usd": None,
    "dataset": "synthetic_delivery_seed_42",
    "questions": str(QUESTIONS_PATH),
    "run_at_utc": datetime.now(timezone.utc).isoformat(),
    "cost_note": (
        "Ollama has no per-request API charge. Local hardware/electricity "
        "cost is not estimated by this benchmark."
    ),
}

DESTINATION.write_text(json.dumps(payload, indent=2) + "\n")

print("\n=== EVALUATION SUMMARY ===", flush=True)
print(json.dumps(payload["summary"], indent=2), flush=True)

print("\n=== CASE RESULTS ===", flush=True)

for result in payload["results"]:
    print(f"\n{result['question_id']} [{result['category']}]", flush=True)
    print(f"Execution: {result['execution_success']}", flush=True)
    print(f"Correct: {result['correct']}", flush=True)
    print(f"Task success: {result['task_success']}", flush=True)
    print(f"Evidence: {result['evidence_quality']}", flush=True)
    print(f"Tool calls: {result['tool_call_count']}", flush=True)
    print(f"Model calls: {result['model_call_count']}", flush=True)
    print(f"Latency: {result['latency_seconds']}s", flush=True)
    print(
        f"Tokens: in={result['input_tokens']} out={result['output_tokens']}",
        flush=True,
    )

    if result["answer"]:
        print(f"Answer: {result['answer']}", flush=True)
    if result["unsupported_claims"]:
        print(
            "Unsupported claims: " + "; ".join(result["unsupported_claims"]),
            flush=True,
        )
    if result["error"]:
        print(f"Error: {result['error']}", flush=True)

print(f"\nSaved local raw result: {DESTINATION}", flush=True)
print(
    "Review the JSON before overriding .gitignore or publishing it.",
    flush=True,
)
