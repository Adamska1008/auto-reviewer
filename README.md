# Auto Code Reviewer

Automatically review your code changes using LLM and post comments to commits.

## Features

- **Multi-language Support**: AST-based code analysis using tree-sitter for Python, Go, and Rust
- **Rich Context Awareness**: Extracts parent scope information (functions, classes, etc.) for better review accuracy
- **Flexible LLM Integration**: Supports any LLM provider (OpenAI, OpenRouter, etc.)
- **Automated Workflow**: Posts review comments directly to commits
- **Multi-commit Handling**: Automatically handles multiple commits in a single push
- **Docker-based GitHub Action**: Fast and lightweight deployment

## Token Usage Benchmark

In a five-commit end-to-end pilot, auto-reviewer used **97.45% fewer total
tokens** than asking `pi-code-agent` to review the same commits directly.

| Workflow | Input Tokens | Output Tokens | Total Tokens | Model Calls |
| --- | ---: | ---: | ---: | ---: |
| Auto-reviewer | 19,012 | 49,477 | 68,489 | 5 |
| `pi-code-agent` | 2,646,744 | 39,781 | 2,686,525 | 153 |

Both workflows used the same local `qwen/qwen3.5-9b@4bit` model through LM
Studio with thinking enabled and its native 262,144-token context window. Pi
ran in fresh sessions with repository inspection tools, and its usage was
summed across every model turn. All runs produced non-empty reviews without
API errors or output-limit truncation.

A manual diff-by-diff quality check found auto-reviewer more relevant in three
of the five cases and mixed results in the other two. Auto-reviewer followed
the requested output format in three cases versus zero for Pi, but both
workflows produced some false positives. The pilot therefore shows a large
token reduction without an obvious quality collapse; it does not establish
formal precision, recall, or quality equivalence.

This is a single-run pilot on five historical Python commits in this
repository, not a cross-repository quality or performance claim. See the
[full benchmark report](benchmarks/RESULTS.md) for per-commit results,
methodology, limitations, and reproduction commands.

## Usage

### Basic Example

Create `.github/workflows/auto-review.yml` in your repository:

```yaml
name: Auto Code Review

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions: # this is essential for posting comments
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - uses: Adamska1008/auto-reviewer@preview
        with:
          api_key: ${{ secrets.AUTO_REVIEWER_API_KEY }}
          base_url: <YOUR_BASE_URL> # optional, default is https://api.openai.com/v1
          model: <YOUR_MODEL>       # optional, default is gpt-4.1
          file_patterns: "*.py,*.js,*.ts" # optional, default is *.py
          language: English # optional, default is Chinese
```

### Setup

1. Add your LLM API key and base URL to repository secrets:
   - Go to Settings → Secrets and variables → Actions
   - Create secrets named `AUTO_REVIEWER_API_KEY`

2. Add the workflow file to `.github/workflows/`

## Inputs

| Input                | Required | Default                       | Description                                                          |
| -------------------- | -------- | ----------------------------- | -------------------------------------------------------------------- |
| `api_key`            | Yes      | -                             | Your LLM API key                                                     |
| `base_url`           | No       | -                             | LLM API base URL                                                     |
| `model`              | No       | `gpt-4.1`                     | LLM model to use                                                     |
| `file_patterns`      | No       | `*.py`                        | File patterns to review (comma-separated, supports *.py, *.go, *.rs) |
| `language`           | No       | `Chinese`                     | Output language for review                                           |
| `github_token`       | No       | `${{ github.token }}`         | GitHub token for posting comments                                    |
| `push_commits_count` | No       | Auto-detected from push event | Number of commits in this push (automatically detected)              |

## Supported Languages

The reviewer uses tree-sitter for AST-based code analysis and currently supports:

- **Python** (`*.py`, `*.pyi`) - Full function, class, and comprehension scope detection
- **Go** (`*.go`) - Function, method, type, and interface scope detection
- **Rust** (`*.rs`) - Function, struct, enum, trait, impl, and closure scope detection

More languages can be easily added through the extensible language handler system.

## Development

### Local Testing

```bash
# Build the Docker image
docker build -t auto-reviewer .

# Run locally (requires environment variables)
docker run --rm \
  -e AUTO_REVIEWER_API_KEY=your_key \
  -e AUTO_REVIEWER_BASE_URL=https://api.openai.com/v1 \
  -e AUTO_REVIEWER_FILE_PATTERNS="*.py,*.js" \
  -e AUTO_REVIEWER_LANGUAGE=English \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOSITORY=owner/repo \
  auto-reviewer
```

### Using UV directly

```bash
# Install dependencies
uv sync

# Run the script
uv run auto-reviewer
```

## License

MIT
