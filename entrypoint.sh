#!/bin/bash
set -e

git config --global --add safe.directory /github/workspace
cd /github/workspace

echo "Current commit sha:" 
git rev-parse HEAD

export OPENROUTER_API_KEY="${INPUT_OPENROUTER_API_KEY:-$OPENROUTER_API_KEY}"
export OPENROUTER_MODEL="${INPUT_OPENROUTER_MODEL:-$OPENROUTER_MODEL}"
export GITHUB_TOKEN="${INPUT_GITHUB_TOKEN:-$GITHUB_TOKEN}"

auto-reviewer
