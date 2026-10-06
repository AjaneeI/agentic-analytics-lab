# M0 ClickHouse Runtime Diagnostic

Status: deterministic diagnosis and bounded repair complete; no Qwen or Hermes
invocation occurred during diagnosis.

## Starting evidence

Issue #89 preserved a successful parent preflight followed by a delegated-child
`query_clickhouse` failure reported only as `HTTP Error 404: Not Found`. The
exact child SQL was:

```sql
SELECT team_id, COUNT(*) as total_items, SUM(blocked) as blocked_count,
       100 * SUM(blocked) / COUNT(*) as blocked_pct
FROM agentic_analytics.delivery_work_items
GROUP BY team_id
ORDER BY blocked_pct DESC
LIMIT 1
```

## Deterministic comparison

The parent and delegated-child paths were reconstructed without invoking a
model. The installed Hermes plugin loaded the same repository
`src.tools.clickhouse_readonly.query_clickhouse` function used by the parent.

| Dimension | Parent preflight | Delegated-child reconstruction | Finding |
|---|---|---|---|
| Host | `127.0.0.1` | `127.0.0.1` | same |
| Port | `8123` | `8123` | same |
| Protocol | HTTP loopback | HTTP loopback | same |
| URL/path | `/` with the same encoded settings | same | same |
| Auth | Basic auth from `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD` | same environment-backed values | same; no credential values preserved |
| Database/schema | fully qualified `agentic_analytics.delivery_work_items` | same table | same table; child selected nonexistent `team_id` |
| Body encoding | UTF-8 POST body | UTF-8 POST body | same encoding, different SQL text |
| Query parameters | JSONEachRow, readonly and resource limits | identical ordered parameters | same |
| Timeout/retry | 15 seconds, no retry | 15 seconds, no retry | same |
| Environment | three required ClickHouse variables from the existing repository `.env` | same variables inherited by Hermes | same |
| Profile/config | not applicable to direct function call | `localbenchmark`; profile `.env` contains no ClickHouse override | no effective difference |
| Working directory | repository root | repository root | same |
| Tool wrapper | repository `query_clickhouse` | installed plugin delegates to the same repository function through `AAL_REPO_ROOT` | same |
| Request adapter | `urllib.request.urlopen` | `urllib.request.urlopen` | same |
| Python build | Homebrew Python 3.14.7 | Hermes-bundled Python 3.14.7 | build differs; exact request succeeds for valid SQL in both |

The exact failed SQL was then replayed through the bundled Python runtime. It
reproduced HTTP 404 with ClickHouse exception code 47 and the body:

```text
Unknown expression identifier `team_id` ... (UNKNOWN_IDENTIFIER)
```

The same bundled runtime returned `[{"row_count": 500}]` for the parent
preflight SQL. Therefore this was not a host, port, protocol, path, auth,
profile, adapter, or Python-runtime routing discrepancy. The deterministic
difference was the SQL request body: the parent used `count()` while the child
invented `team_id`; the real schema column is `team`.

## Root cause and repair

ClickHouse exposes query-semantic failures through HTTP status codes. The
read-only wrapper caught every exception generically and discarded the HTTP
response body and `X-ClickHouse-Exception-Code`, turning a model-generated
unknown identifier into an apparent infrastructure 404.

The bounded repair catches `HTTPError`, reads at most 4096 response bytes, and
includes the status, ClickHouse exception code, and server detail in the
raised error. It does not change authentication, retries, validator behavior,
SQL semantics, networking, agent layers, or the model-visible tool contract.

## RED to GREEN evidence

Focused RED command:

```sh
python3 -m unittest \
  tests.test_clickhouse_readonly.TestClickHouseErrorReporting -v
```

Before the repair, the regression failed because the observed message was only
`ClickHouse query failed: HTTP Error 404: Not Found`.

After the repair, the same test passed and distinguished the successful parent
response from the child `code 47` / `team_id` / `UNKNOWN_IDENTIFIER` error.
Focused verification passed 35/35 tests. The full repository suite passed
349/349 tests.

This repair fixes deterministic error classification and diagnosability. It
does not repair or normalize invalid SQL, relax validation, or predict whether
the unchanged model will choose the correct schema column in a fresh run.
