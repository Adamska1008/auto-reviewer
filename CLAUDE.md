# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto Code Reviewer - A GitHub Action that automatically reviews code changes using any LLM provider (OpenAI, OpenRouter, etc.) and posts comments to commits.

## Development Commands

```bash
# Install dependencies (uses UV package manager)
uv sync

# Run the reviewer directly
uv run auto-reviewer

# Build Docker image
docker build -t auto-reviewer .

# Run locally with Docker
docker run --rm \
  -e AUTO_REVIEWER_API_KEY=your_key \
  -e AUTO_REVIEWER_BASE_URL=https://api.openai.com/v1 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOSITORY=owner/repo \
  auto-reviewer
```

## Architecture

Modular Python package (`auto_reviewer/`) with clear separation of concerns:

- **[config.py](auto_reviewer/config.py)** - Environment variables and logging setup
- **[github.py](auto_reviewer/github.py)** - `GitHubClient` class for posting commit comments
- **[git.py](auto_reviewer/git.py)** - Git operations (diff, commit SHA, author, message)
- **[template.py](auto_reviewer/template.py)** - Jinja2 template loading and rendering
- **[llm.py](auto_reviewer/llm.py)** - LLM API calls via OpenAI client
- **[main.py](auto_reviewer/main.py)** - Main entry point, orchestrates all modules

**Main Flow:**
1. Validate environment variables
2. Get git diff between `HEAD~1` and HEAD
3. Render Jinja2 template with diff content
4. Apply "Prompt Repetition" technique (duplicates prompt)
5. Call LLM API
6. Print review to stdout and post to GitHub commit

## Key Files

- [auto_reviewer/prompts/simple.j2](auto_reviewer/prompts/simple.j2) - Jinja2 template for LLM prompt
- [action.yml](action.yml) - GitHub Action metadata
- [entrypoint.sh](entrypoint.sh) - Docker entrypoint, maps action inputs to env vars
- [Dockerfile](Dockerfile) - Multi-stage build using `ghcr.io/astral-sh/uv`

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `AUTO_REVIEWER_API_KEY` | Yes | - | LLM API key |
| `AUTO_REVIEWER_BASE_URL` | Yes | - | LLM API base URL |
| `AUTO_REVIEWER_MODEL` | No | `gpt-4.1` | Model to use |
| `AUTO_REVIEWER_FILE_PATTERNS` | No | `*.py` | Comma-separated file patterns to review |
| `GITHUB_TOKEN` | No | - | GitHub token for posting comments |
| `GITHUB_REPOSITORY` | No | - | Repository in `owner/repo` format |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Design Notes

- File patterns configurable via `AUTO_REVIEWER_FILE_PATTERNS` (supports `*.py,*.js,*.ts` etc.)
- Skips review if no matching files changed
- Template resources loaded via `importlib.resources` from `auto_reviewer.prompts` package
- Prompt duplicated before sending to LLM (paper: "Prompt Repetition Improves Non-Reasoning LLMs")
