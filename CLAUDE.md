# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto Code Reviewer - A GitHub Action that automatically reviews Python code changes using LLM and posts comments to commits. Uses DeepSeek V3.2 via OpenRouter API for intelligent code reviews.

## Development Commands

```bash
# Install dependencies (uses UV package manager)
uv sync

# Run the reviewer directly
uv run main.py

# Build Docker image
docker build -t auto-reviewer .

# Run locally with Docker
docker run --rm \
  -e OPENROUTER_API_KEY=your_key \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOSITORY=owner/repo \
  -e GITHUB_SHA=abc123 \
  auto-reviewer
```

## Architecture

Single-file Python application ([main.py](main.py)) with clear separation of concerns:

1. **GitHubClient** - HTTP client wrapper for posting commit comments via GitHub API
2. **Git Functions** - Subprocess wrappers for getting current commit SHA and git diff (Python files only: `*.py`)
3. **Template Functions** - Loads Jinja2 templates from `prompts/` directory using `importlib.resources`
4. **Main Flow**:
   - Validates environment variables
   - Gets git diff between `BASE_REF` (default: `HEAD~1`) and current HEAD
   - Renders Jinja2 template with diff content
   - Applies "Prompt Repetition" technique (duplicates prompt for better LLM results)
   - Calls OpenRouter API via OpenAI client
   - Prints review to stdout and posts to GitHub commit

## Key Files

- [main.py](main.py) - All application logic in a single file
- [prompts/simple.j2](prompts/simple.j2) - Jinja2 template for LLM prompt (outputs structured review in Chinese)
- [action.yml](action.yml) - GitHub Action metadata defining inputs/outputs
- [Dockerfile](Dockerfile) - Multi-stage build using `ghcr.io/astral-sh/uv` base image

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `OPENROUTER_API_KEY` | Yes | - | OpenRouter API key |
| `GITHUB_TOKEN` | No | - | GitHub token for posting comments |
| `GITHUB_REPOSITORY` | No | - | Repository in `owner/repo` format |
| `GITHUB_API_URL` | No | `https://api.github.com` | GitHub API endpoint |
| `OPENROUTER_MODEL` | No | `deepseek/deepseek-v3.2` | Model to use |
| `BASE_REF` | No | `HEAD~1` | Base reference for diff |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Design Notes

- Only reviews Python files (`*.py` filter in git diff command)
- Skips review if no Python changes detected
- Uses loguru for colored console output
- Template resources loaded via Python's `importlib.resources` (not file paths)
- The prompt is duplicated before sending to LLM (paper: "Prompt Repetition Improves Non-Reasoning LLMs")
