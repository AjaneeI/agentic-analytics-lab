"""Evaluate the deterministic control-plane router against routing fixtures."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.routing_eval import evaluate_routing, load_routing_fixtures


DEFAULT_FIXTURES = Path("evals/routing_fixtures.json")


def main() -> None:
    fixtures = load_routing_fixtures(DEFAULT_FIXTURES)
    result = evaluate_routing(fixtures)

    print(f"Routing fixtures: {result.total}")
    print(f"Correct routes: {result.correct}")
    print(f"Accuracy: {result.accuracy:.1%}")
    print(f"False-cheap routes: {result.false_cheap_routes}")
    print(f"Unnecessary escalations: {result.unnecessary_escalations}")

    if result.mismatches:
        for mismatch in result.mismatches:
            print(
                "MISMATCH "
                f"{mismatch.fixture_id}: "
                f"expected={mismatch.expected_route.value} "
                f"actual={mismatch.actual_route.value}"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
