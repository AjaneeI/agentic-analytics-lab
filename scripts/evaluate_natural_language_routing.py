"""Evaluate the lexical natural-language routing baseline on the dev set."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.natural_language_routing import (
    evaluate_natural_language_routing,
    load_natural_language_fixtures,
)
from src.routing.natural_language_baseline import classify_natural_language


DEFAULT_FIXTURES = Path("evals/natural_language_routing_dev.json")


def main() -> None:
    fixtures = load_natural_language_fixtures(DEFAULT_FIXTURES)
    result = evaluate_natural_language_routing(
        fixtures,
        classify_natural_language,
    )

    print(f"Natural-language routing fixtures: {result.total}")
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
                f"actual={mismatch.actual_route.value} "
                f"prompt={mismatch.prompt!r}"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
