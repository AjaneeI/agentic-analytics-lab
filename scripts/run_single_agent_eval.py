"""Run the full frozen evaluation suite against the 7B single-agent baseline."""

from datetime import datetime, timezone
import json
from pathlib import Path

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.runner import run_case, save_results


MODEL = "qwen2.5:7b"
QUESTIONS_PATH = Path("evals/questions.json")
DESTINATION = Path(
    "experiments/results/single_agent_qwen2.5_7b.json"
)

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
        f"success={record.success} | "
        f"latency={record.latency_seconds}s | "
        f"tools={record.tool_call_count}",
        flush=True,
    )

    if record.error:
        print(f"Error: {record.error}", flush=True)

save_results(records, DESTINATION)

payload = json.loads(DESTINATION.read_text())

payload["metadata"] = {
    "architecture": "single_agent",
    "model": MODEL,
    "provider": "ollama_local",
    "api_cost_usd": 0,
    "dataset": "synthetic_delivery_seed_42",
    "run_at_utc": datetime.now(timezone.utc).isoformat(),
}

DESTINATION.write_text(
    json.dumps(payload, indent=2) + "\n"
)

print("\n=== EVALUATION SUMMARY ===", flush=True)
print(json.dumps(payload["summary"], indent=2), flush=True)

print("\n=== ANSWERS ===", flush=True)

for result in payload["results"]:
    print(
        f"\n{result['question_id']} [{result['category']}]",
        flush=True,
    )
    print(f"Success: {result['success']}", flush=True)
    print(f"Tool calls: {result['tool_call_count']}", flush=True)
    print(f"Latency: {result['latency_seconds']}s", flush=True)

    if result["answer"]:
        print(f"Answer: {result['answer']}", flush=True)

    if result["error"]:
        print(f"Error: {result['error']}", flush=True)

print(f"\nSaved: {DESTINATION}", flush=True)
