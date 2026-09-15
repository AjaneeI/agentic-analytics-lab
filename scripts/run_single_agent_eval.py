"""Run the frozen evaluation suite against the local single-agent baseline."""

from datetime import datetime, timezone
import json
from pathlib import Path

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.runner import run_suite, save_results


MODEL = "qwen2.5:7b"
DESTINATION = Path(
    "experiments/results/single_agent_qwen2.5_7b.json"
)

agent = SingleAgent(
    OllamaModelClient(model=MODEL)
)

records = run_suite(
    agent,
    "evals/questions.json",
)

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

print("=== EVALUATION SUMMARY ===")
print(json.dumps(payload["summary"], indent=2))

print("\n=== ANSWERS ===")

for result in payload["results"]:
    print()
    print(f"{result['question_id']} [{result['category']}]")
    print(f"Success: {result['success']}")
    print(f"Tool calls: {result['tool_call_count']}")
    print(f"Latency: {result['latency_seconds']}s")

    if result["answer"]:
        print(f"Answer: {result['answer']}")

    if result["error"]:
        print(f"Error: {result['error']}")

print(f"\nSaved: {DESTINATION}")
