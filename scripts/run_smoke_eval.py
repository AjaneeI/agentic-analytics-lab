"""Fast development smoke test using Q1 and Q6 only."""

import json
from pathlib import Path

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.runner import run_case

MODEL = "qwen2.5:3b"

questions = json.loads(Path("evals/questions.json").read_text())
selected = [q for q in questions if q["id"] in {"Q1", "Q6"}]

agent = SingleAgent(
    OllamaModelClient(model=MODEL),
    max_steps=3,
)

for i, case in enumerate(selected, 1):
    print(f"\n=== Running {case['id']} ({i}/{len(selected)}) ===", flush=True)

    record = run_case(agent, case)

    print(f"Success: {record.success}", flush=True)
    print(f"Latency: {record.latency_seconds}s", flush=True)
    print(f"Tool calls: {record.tool_call_count}", flush=True)

    if record.answer:
        print(f"Answer: {record.answer}", flush=True)

    if record.error:
        print(f"Error: {record.error}", flush=True)
