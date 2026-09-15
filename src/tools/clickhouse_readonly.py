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

_ALLOWED_START = re.compile(
    r"^\s*(SELECT|WITH|SHOW|DESCRIBE|DESC|EXPLAIN)\b",
    re.IGNORECASE,
)

_MUTATING = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|CREATE|RENAME|"
    r"OPTIMIZE|SYSTEM|GRANT|REVOKE|ATTACH|DETACH"
    r")\b",
    re.IGNORECASE,
)


class QueryRejected(ValueError):
    pass


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql.strip()


def validate_read_only(sql: str) -> str:
    cleaned = _strip_comments(sql)

    if not cleaned:
        raise QueryRejected("Query is empty.")

    if not _ALLOWED_START.match(cleaned):
        raise QueryRejected("Only read-only analytical statements are allowed.")

    if _MUTATING.search(cleaned):
        raise QueryRejected("Mutation or administrative keyword detected.")

    # Allow only one statement. A trailing semicolon is fine.
    statement = cleaned.rstrip().rstrip(";").strip()
    if ";" in statement:
        raise QueryRejected("Multiple SQL statements are not allowed.")

    return statement


def query_clickhouse(sql: str) -> list[dict[str, Any]]:
    statement = validate_read_only(sql)

    params = urllib.parse.urlencode(
        {
            "default_format": "JSONEachRow",
            "readonly": "1",
            "max_execution_time": "10",
            "max_result_rows": "1000",
            "result_overflow_mode": "break",
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
