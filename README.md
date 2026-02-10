# Auto Code Reviewer

Automatically review your code changes using LLM and post comments to commits.

## Features

- Supports any LLM provider (OpenAI, OpenRouter, etc.)
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
          base_url: <YOUR_BASE_URL> # optional, default is https://api.openai.com/v1
          model: <YOUR_MODEL>       # optional, default is gpt-4.1
          file_patterns: "*.py,*.js,*.ts" # optional, default is *.py
```

### Setup

1. Add your LLM API key and base URL to repository secrets:
   - Go to Settings → Secrets and variables → Actions
   - Create secrets named `AUTO_REVIEWER_API_KEY` and `AUTO_REVIEWER_BASE_URL`

2. Add the workflow file to `.github/workflows/`

## Inputs

| Input           | Required | Default               | Description                         |
| --------------- | -------- | --------------------- | ----------------------------------- |
| `api_key`       | Yes      | -                     | Your LLM API key                    |
| `base_url`      | Yes      | -                     | LLM API base URL                    |
| `model`         | No       | `gpt-4.1`             | LLM model to use                    |
| `file_patterns` | No       | `*.py`                | File patterns to review (comma-separated) |
| `github_token`  | No       | `${{ github.token }}` | GitHub token for posting comments   |
| `base_ref`      | No       | `HEAD~1`              | Base reference for diff            |

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
