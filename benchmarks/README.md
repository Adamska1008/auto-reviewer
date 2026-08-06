# End-to-end token benchmark

This benchmark compares the complete token usage of the current auto-reviewer
with a fresh `pi-code-agent` review of the same historical commit. Pi usage is
summed across every model turn, including turns that invoke tools.

Prerequisites:

- LM Studio server on `http://127.0.0.1:1234/v1`
- `qwen/qwen3.5-9b` loaded as `auto-review-bench-qwen-max` with its native
  262144-token context
- `pi` and `uv` available on `PATH`

Load the benchmark model at its native context limit:

```bash
lms load qwen/qwen3.5-9b \
  --context-length 262144 \
  --parallel 1 \
  --identifier auto-review-bench-qwen-max \
  --yes
```

Both arms use Qwen's native thinking mode and configure the model/context
limits to 262144 tokens. Hidden reasoning reported by LM Studio is included in
total usage.

Smoke test:

```bash
uv run python benchmarks/run_benchmark.py --limit 1
```

Default 15-commit benchmark:

```bash
uv run python benchmarks/run_benchmark.py
```

Raw JSONL and summary JSON files are written under `benchmarks/results/`.
