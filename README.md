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
    permissions: # this is essential for posting comments
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - uses: Adamska1008/auto-reviewer@v1
        with:
          api_key: ${{ secrets.AUTO_REVIEWER_API_KEY }}
          base_url: <YOUR_BASE_URL> # default openai
          model: <YOUR_MODEL> # default gpt-4.1
```

### Setup

1. Add your LLM API key and base URL to repository secrets:
   - Go to Settings → Secrets and variables → Actions
   - Create secrets named `AUTO_REVIEWER_API_KEY` and `AUTO_REVIEWER_BASE_URL`

2. Add the workflow file to `.github/workflows/`

## Inputs

| Input          | Required | Default               | Description                       |
| -------------- | -------- | --------------------- | --------------------------------- |
| `api_key`      | Yes      | -                     | Your LLM API key                  |
| `base_url`     | Yes      | -                     | LLM API base URL                  |
| `model`        | No       | `gpt-4.1`             | LLM model to use                  |
| `github_token` | No       | `${{ github.token }}` | GitHub token for posting comments |
| `base_ref`     | No       | `HEAD~1`              | Base reference for diff           |

## Development

### Local Testing

```bash
# Build the Docker image
docker build -t auto-reviewer .

# Run locally (requires environment variables)
docker run --rm \
  -e AUTO_REVIEWER_API_KEY=your_key \
  -e AUTO_REVIEWER_BASE_URL=https://api.openai.com/v1 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOSITORY=owner/repo \
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
