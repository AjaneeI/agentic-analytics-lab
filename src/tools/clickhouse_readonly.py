"""Minimal read-only ClickHouse query tool for Agentic Analytics Lab."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any


CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://127.0.0.1:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

_ALLOWED_TABLE = "agentic_analytics.delivery_work_items"

_ALLOWED_START = re.compile(
    r"^\s*(SELECT|WITH|DESCRIBE|DESC|EXPLAIN)\b",
    re.IGNORECASE,
)

_MUTATING = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|CREATE|RENAME|"
    r"OPTIMIZE|SYSTEM|GRANT|REVOKE|ATTACH|DETACH"
    r")\b",
    re.IGNORECASE,
)

_IDENTIFIER_PART = r'(?:`[^`]+`|"[^"]+"|[A-Za-z_][\w$]*)'
_IDENTIFIER = rf"{_IDENTIFIER_PART}(?:\s*\.\s*{_IDENTIFIER_PART})?"
_TABLE_REFERENCE = re.compile(
    rf"\b(?:FROM|JOIN)\s+({_IDENTIFIER})",
    re.IGNORECASE,
)
_TABLE_FUNCTION_REFERENCE = re.compile(
    r"\b(?:FROM|JOIN)\s+[A-Za-z_][\w$]*\s*\(",
    re.IGNORECASE,
)
_CTE_NAME = re.compile(
    rf"(?:\bWITH\b|,)\s*({_IDENTIFIER_PART})\s+AS\s*\(",
    re.IGNORECASE,
)
_DESCRIBE_TARGET = re.compile(
    rf"^\s*(?:DESCRIBE|DESC)\s+(?:TABLE\s+)?({_IDENTIFIER})\s*$",
    re.IGNORECASE,
)

_BLOCKER_RATE_ALIAS = re.compile(
    r"\bAS\s+(?:`blocker_rate`|\"blocker_rate\"|blocker_rate\b)",
    re.IGNORECASE,
)

_COUNT_ALL = r"count\s*\(\s*(?:\*)?\s*\)"
_SUM_BLOCKED = r"sum\s*\(\s*(?:`blocked`|\"blocked\"|blocked)\s*\)"

_BLOCKER_RATE_COMPLEMENT = re.compile(
    rf"""
    (?:
        \(\s*{_COUNT_ALL}\s*-\s*{_SUM_BLOCKED}\s*\)
        |
        {_COUNT_ALL}\s*-\s*{_SUM_BLOCKED}
    )
    \s*/\s*
    {_COUNT_ALL}
    """,
    re.IGNORECASE | re.VERBOSE,
)

_BLOCKER_RATE_AVG_COMPLEMENT = re.compile(
    r"""
    \b(?:1(?:\.0)?|100(?:\.0)?)\s*-\s*
    avg\s*\(\s*(?:`blocked`|"blocked"|blocked)\s*\)
    """,
    re.IGNORECASE | re.VERBOSE,
)


class QueryRejected(ValueError):
    pass


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql.strip()


def _normalize_identifier(identifier: str) -> str:
    parts = re.split(r"\s*\.\s*", identifier)
    normalized = [part.strip().strip('`"').lower() for part in parts]
    return ".".join(normalized)


def _validate_table_scope(sql: str) -> None:
    describe_match = _DESCRIBE_TARGET.match(sql)
    if describe_match:
        target = _normalize_identifier(describe_match.group(1))
        if target != _ALLOWED_TABLE:
            raise QueryRejected(
                f"Only {_ALLOWED_TABLE} may be described."
            )
        return

    if re.match(r"^\s*(?:DESCRIBE|DESC)\b", sql, re.IGNORECASE):
        raise QueryRejected(
            f"DESCRIBE must target {_ALLOWED_TABLE}."
        )

    if _TABLE_FUNCTION_REFERENCE.search(sql):
        raise QueryRejected("ClickHouse table functions are not allowed.")

    cte_names = {
        _normalize_identifier(match.group(1))
        for match in _CTE_NAME.finditer(sql)
    }

    for match in _TABLE_REFERENCE.finditer(sql):
        target = _normalize_identifier(match.group(1))
        if target in cte_names:
            continue
        if target != _ALLOWED_TABLE:
            raise QueryRejected(
                f"Only {_ALLOWED_TABLE} may be queried."
            )


def _validate_clickhouse_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme == "https":
        return

    if parsed.scheme != "http":
        raise RuntimeError("CLICKHOUSE_URL must use http or https.")

    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(
            "Non-local CLICKHOUSE_URL values must use HTTPS."
        )


def _expression_before_alias(sql: str, alias_start: int) -> str:
    depth = 0

    for index in range(alias_start - 1, -1, -1):
        char = sql[index]

        if char == ")":
            depth += 1
        elif char == "(" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            return sql[index + 1 : alias_start].strip()

    prefix = sql[:alias_start]
    select_matches = list(re.finditer(r"\bSELECT\b", prefix, re.IGNORECASE))

    if select_matches:
        return prefix[select_matches[-1].end() :].strip()

    return prefix.strip()


def _validate_metric_semantics(sql: str) -> None:
    for match in _BLOCKER_RATE_ALIAS.finditer(sql):
        expression = _expression_before_alias(sql, match.start())

        if (
            _BLOCKER_RATE_COMPLEMENT.search(expression)
            or _BLOCKER_RATE_AVG_COMPLEMENT.search(expression)
        ):
            raise QueryRejected(
                "blocker_rate must measure blocked items, not non-blocked items."
            )


def validate_read_only(sql: str) -> str:
    cleaned = _strip_comments(sql)

    if not cleaned:
        raise QueryRejected("Query is empty.")

    if not _ALLOWED_START.match(cleaned):
        raise QueryRejected("Only approved read-only analytical statements are allowed.")

    if _MUTATING.search(cleaned):
        raise QueryRejected("Mutation or administrative keyword detected.")

    # Allow only one statement. A trailing semicolon is fine.
    statement = cleaned.rstrip().rstrip(";").strip()
    if ";" in statement:
        raise QueryRejected("Multiple SQL statements are not allowed.")

    _validate_table_scope(statement)
    _validate_metric_semantics(statement)

    return statement


def query_clickhouse(sql: str) -> list[dict[str, Any]]:
    statement = validate_read_only(sql)
    _validate_clickhouse_url(CLICKHOUSE_URL)

    params = urllib.parse.urlencode(
        {
            "default_format": "JSONEachRow",
            "readonly": "1",
            "max_execution_time": "10",
            "max_result_rows": "1000",
            "result_overflow_mode": "break",
            "max_rows_to_read": "10000",
            "max_bytes_to_read": str(10 * 1024 * 1024),
            "max_memory_usage": str(128 * 1024 * 1024),
            "max_threads": "2",
        }
    )

    request = urllib.request.Request(
        f"{CLICKHOUSE_URL}/?{params}",
        data=statement.encode("utf-8"),
        method="POST",
    )

    credentials = f"{CLICKHOUSE_USER}:{CLICKHOUSE_PASSWORD}".encode("utf-8")
    request.add_header(
        "Authorization",
        "Basic " + base64.b64encode(credentials).decode("ascii"),
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"ClickHouse query failed: {exc}") from exc

    rows = []
    for line in body.splitlines():
        if line.strip():
            rows.append(json.loads(line))

    return rows


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python -m src.tools.clickhouse_readonly "SELECT ..."'
        )

    sql = sys.argv[1]

    try:
        rows = query_clickhouse(sql)
    except QueryRejected as exc:
        print(f"REJECTED: {exc}")
        raise SystemExit(2)

    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
