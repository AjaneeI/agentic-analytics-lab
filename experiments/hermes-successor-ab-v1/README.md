# Hermes successor A/B v1

This directory freezes the first successor to the failed SB-D01 comparison in
issue #73. It is experiment infrastructure, not a general Hermes integration.

## Frozen treatments

- Treatment A uses the repository's existing `BoundedLocalExecutor` with
  `hermes-local:qwen3.5-9b`, temperature 0, at most six model steps, and the
  existing `query_clickhouse` and `retrieve_policy` tool contracts.
- Treatment B uses the same local model and evidence contracts through the
  isolated Hermes profile `localbenchmark`. The parent may call
  `delegate_task` exactly once with one child. Only that delegated child may
  call the two evidence tools, once each. The child is capped at six model
  iterations and temperature 0.
- Neither treatment may retry. Model output is scored without editing or
  cleanup. Incremental paid spend must remain $0.

## Profile installation

The versioned profile contains no credentials. On the frozen host, create the
profile once and install the exact files:

```sh
hermes profile create localbenchmark --no-skills --no-alias \
  --description "Isolated zero-paid Hermes successor benchmark profile"
cp experiments/hermes-successor-ab-v1/profile/config.yaml \
  /Users/ajaneeigharo/.hermes/profiles/localbenchmark/config.yaml
mkdir -p /Users/ajaneeigharo/.hermes/profiles/localbenchmark/plugins/system-benchmark-tools
cp experiments/hermes-successor-ab-v1/plugin/system-benchmark-tools/__init__.py \
  experiments/hermes-successor-ab-v1/plugin/system-benchmark-tools/plugin.yaml \
  /Users/ajaneeigharo/.hermes/profiles/localbenchmark/plugins/system-benchmark-tools/
```

The already-tested `herdr-worker` plugin and its external one-worker manager
remain host-local. Their absolute paths, hashes, versions, and acceptance
results are pinned in `frozen-state.json`; they are not duplicated here because
they are a host-specific controller for an existing Herdr/OpenCode installation.

Validate before freezing or running:

```sh
hermes -p localbenchmark config check
hermes -p localbenchmark plugins doctor herdr-worker --ci
hermes -p localbenchmark plugins doctor system-benchmark-tools --ci
hermes -p localbenchmark fallback list
hermes -p localbenchmark tools list
hermes -p localbenchmark prompt-size --json
```

The final tool array must contain exactly `delegate_task`,
`query_clickhouse`, and `retrieve_policy`.

## One-shot execution

After the branch is committed, reviewed, tagged with the manifest's
`repository.freeze_ref`, and the successor issue records the resolved commit,
run once from that exact checkout:

```sh
python3 experiments/hermes-successor-ab-v1/run_benchmark.py \
  --output-dir experiments/results/hermes-successor-ab-v1-2026-10-05
```

The runner verifies the frozen tag, tracked-worktree state, contract hashes,
installed profile files, and tool count before each treatment. It refuses to
reuse an output directory so a failed treatment cannot be silently retried.
Raw model traffic, Hermes stdout/stderr, tool events, usage, scores, and the
comparison are preserved in the output directory.
