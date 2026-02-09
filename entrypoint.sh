#!/bin/bash
set -e

git config --global --add safe.directory /github/workspace
cd /github/workspace

echo "Current commit sha:" 
git rev-parse HEAD

export AUTO_REVIEWER_API_KEY="${INPUT_API_KEY:-$AUTO_REVIEWER_API_KEY}"
export AUTO_REVIEWER_BASE_URL="${INPUT_BASE_URL:-$AUTO_REVIEWER_BASE_URL}"
export AUTO_REVIEWER_MODEL="${INPUT_MODEL:-$AUTO_REVIEWER_MODEL}"
export GITHUB_TOKEN="${INPUT_GITHUB_TOKEN:-$GITHUB_TOKEN}"

auto-reviewer
