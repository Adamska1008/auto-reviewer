#!/bin/bash
set -e

git config --global --add safe.directory /github/workspace
cd /github/workspace

auto-reviewer
