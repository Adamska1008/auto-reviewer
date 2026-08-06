# Qwen3.5 9B end-to-end token benchmark

Run date: 2026-08-05

This pilot compares the complete model usage of auto-reviewer with a fresh
`pi-code-agent` review of the same historical commit. Pi usage is summed over
every model turn, including all turns before and after tool calls.

## Configuration

- Model: `qwen/qwen3.5-9b@4bit` in LM Studio
- API identifier: `auto-review-bench-qwen-max`
- Context window: 262,144 tokens (the model's native maximum)
- Maximum output setting: 262,144 tokens
- Thinking: enabled; hidden reasoning is included in usage
- Repetitions: one run per arm per commit
- Pi session: fresh session with `read`, `grep`, `find`, `ls`, and `bash`
- Auto-reviewer: current `-U10` diff plus AST parent-scope prompt

## Results

| Commit | Changed lines | Auto tokens | Pi tokens | Pi model calls | Pi tool calls | Reduction |
|---|---:|---:|---:|---:|---:|---:|
| `55f38295ae1b` | 3 | 10,696 | 346,627 | 30 | 29 | 96.91% |
| `2307f04f256b` | 9 | 11,783 | 596,920 | 44 | 43 | 98.03% |
| `0b394479e5fa` | 44 | 16,338 | 331,783 | 37 | 36 | 95.08% |
| `1d00eb626e13` | 121 | 21,841 | 149,573 | 15 | 14 | 85.40% |
| `94dddfcb04ab` | 229 | 7,831 | 1,261,622 | 27 | 26 | 99.38% |
| **Total** | **406** | **68,489** | **2,686,525** | **153** | **148** | **97.45%** |

Additional observations:

- Median per-case reduction: 96.91%.
- Range: 85.40% to 99.38%.
- Pi used 39.23 times as many total tokens.
- Input tokens were 19,012 for auto-reviewer versus 2,646,744 for Pi, a
  99.28% reduction. Repeated agent context dominates Pi's usage.
- Auto-reviewer output tokens were 49,477 versus 39,781 for Pi; the total
  saving therefore did not come from forcing a shorter completion.
- Wall time was similar: 1,050.8 seconds for auto-reviewer versus 1,024.7
  seconds for Pi. This run demonstrates token reduction, not a speedup.
- All ten runs completed without API errors or output-limit truncation and
  produced non-empty review text.

## Manual quality sanity check

The ten outputs were manually compared with the actual commit diffs. This was
not a blind evaluation and the commits do not provide a seeded-defect oracle,
so the assessment is directional rather than a precision/recall benchmark.

| Commit | Assessment | Evidence |
|---|---|---|
| `55f38295ae1b` | Auto-reviewer better | Its summary stayed on the three-line subprocess fix. Pi attributed initial-commit features from earlier commits to this change. |
| `2307f04f256b` | Auto-reviewer better | It identified the redundant double diff call. Pi labeled several pre-existing or speculative AST/file errors as new critical issues. |
| `0b394479e5fa` | Auto-reviewer better | It caught the real removal of `GITHUB_SHA` targeting. Pi reported a Dockerfile regression even though this commit did not change the Dockerfile. |
| `1d00eb626e13` | Mixed | Both found the unvalidated `PUSH_COMMITS_COUNT`. Auto-reviewer added an incorrect `CalledProcessError.stdout` compatibility claim; Pi mostly summarized the implementation rather than reviewing it. |
| `94dddfcb04ab` | Mixed | Both found the repeated parser construction/caching issue. Both also added weak or incorrect secondary findings. Pi's summary covered all three added languages more completely. |

Strict output-format adherence was 3/5 for auto-reviewer and 0/5 for Pi. The
main Pi violations were conversational filler, unsupported labels such as
`[Bug]`/`[Documentation]`, and non-list summaries. Auto-reviewer duplicated
items in one case and omitted the required summary in another.

Overall, this small manual check did not show a quality collapse that would
explain the 97.45% token reduction. It also does not prove quality parity:
both approaches hallucinated or overstated some findings, and a defensible
quality claim needs seeded defects, clean controls, blind scoring, and repeated
runs.

## Reproduction

The exact pilot command was:

```bash
lms load qwen/qwen3.5-9b \
  --context-length 262144 \
  --parallel 1 \
  --identifier auto-review-bench-qwen-max \
  --yes

uv run python benchmarks/run_benchmark.py \
  --timeout 1800 \
  --output benchmarks/results/qwen-max-5case.jsonl \
  --commits 55f38295ae1b 2307f04f256b 0b394479e5fa \
  1d00eb626e13 94dddfcb04ab
```

Machine-readable output is stored in `benchmarks/results/` locally. This
directory is ignored because responses and run artifacts can be large.

This is a five-case, single-run pilot on one Python repository. The result is
strong evidence for this workload, but it is not yet a cross-repository or
multi-run confidence interval.
