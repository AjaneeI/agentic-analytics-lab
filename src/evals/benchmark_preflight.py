"""Read-only benchmark environment preflight checks."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Callable

from src.tools.clickhouse_readonly import query_clickhouse


EXPECTED_ROW_COUNT = 500
TABLE_NAME = "agentic_analytics.delivery_work_items"
REQUIRED_ENV_VARS = (
    "CLICKHOUSE_URL",
    "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD",
)
_ROW_COUNT_SQL = (
    "SELECT count() AS row_count "
    f"FROM {TABLE_NAME}"
)


QueryFn = Callable[[str], list[dict[str, Any]]]


def missing_clickhouse_env_vars(
    env: Mapping[str, str] | None = None,
) -> list[str]:
    values = os.environ if env is None else env
    return [name for name in REQUIRED_ENV_VARS if not values.get(name)]


def _failure(message: str) -> tuple[int, str]:
    return (
        1,
        "\n".join(
            [
                f"FAIL: {message}",
                "Do not treat this attempt as benchmark performance evidence.",
            ]
        ),
    )


def _extract_row_count(rows: list[dict[str, Any]]) -> int:
    if len(rows) != 1 or "row_count" not in rows[0]:
        raise RuntimeError("Unexpected ClickHouse result shape.")

    try:
        return int(rows[0]["row_count"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Row count result was not numeric.") from exc


def _classify_connection_error(exc: Exception) -> str:
    text = str(exc).lower()

    if "401" in text or "unauthorized" in text:
        return "ClickHouse authentication failed during preflight."

    if any(
        marker in text
        for marker in (
            "timed out",
            "connection refused",
            "name or service not known",
            "temporary failure in name resolution",
            "network is unreachable",
            "failed to establish",
            "connection reset",
        )
    ):
        return "Could not reach ClickHouse during preflight."

    return "Read-only ClickHouse preflight query failed."


def run_preflight(
    env: Mapping[str, str] | None = None,
    query_fn: QueryFn = query_clickhouse,
) -> tuple[int, str]:
    missing = missing_clickhouse_env_vars(env)
    if missing:
        return _failure(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Load the local ignored .env into this shell first "
            "(for example: set -a; source .env; set +a)."
        )

    try:
        rows = query_fn(_ROW_COUNT_SQL)
        row_count = _extract_row_count(rows)
    except Exception as exc:
        return _failure(_classify_connection_error(exc))

    if row_count != EXPECTED_ROW_COUNT:
        return _failure(
            f"Expected {EXPECTED_ROW_COUNT} synthetic rows in {TABLE_NAME}, "
            f"but found {row_count}."
        )

    return (
        0,
        "PASS: Benchmark preflight ready. Authenticated read-only access "
        f"to {TABLE_NAME} returned {EXPECTED_ROW_COUNT} rows.",
    )
