# Auto Code Reviewer

Automatically review your Python code changes using LLM and post comments to commits.

## Features

- Uses DeepSeek V3.2 via OpenRouter for intelligent code reviews
- Posts review comments directly to commits
- Docker-based GitHub Action
- Fast and lightweight

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
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - uses: your-username/auto_reviewer@v1
        with:
          openrouter_api_key: ${{ secrets.OPENROUTER_API_KEY }}
```

### Setup

1. Add your OpenRouter API key to repository secrets:
   - Go to Settings → Secrets and variables → Actions
   - Create a new secret named `OPENROUTER_API_KEY`

2. Add the workflow file to `.github/workflows/`

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `openrouter_api_key` | Yes | - | Your OpenRouter API key |
| `github_token` | No | `${{ github.token }}` | GitHub token for posting comments |
| `base_ref` | No | `HEAD~1` | Base reference for diff |
| `model` | No | `deepseek/deepseek-v3.2` | OpenRouter model to use |

## Development

### Local Testing

```bash
# Build the Docker image
docker build -t auto-reviewer .

# Run locally (requires environment variables)
docker run --rm \
  -e OPENROUTER_API_KEY=your_key \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOSITORY=owner/repo \
  -e GITHUB_SHA=abc123 \
  auto-reviewer
```

### Using UV directly

```bash
# Install dependencies
uv sync

# Run the script
uv run main.py
```

## License

MIT
