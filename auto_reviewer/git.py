"""Git utilities for getting commit info and diffs."""

import os
import subprocess
from loguru import logger

from auto_reviewer import config


def get_current_commit_sha() -> str:
    """Get current commit SHA."""
    logger.debug(f"Running git in directory: {os.getcwd()}")
    sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return sha_result.stdout.strip()


def get_git_diff(old_commit: str, new_commit: str) -> str:
    """Get git diff between two commits with extended context."""
    cmd = ["git", "diff", "-U10", old_commit, new_commit, "--", *config.FILE_PATTERNS]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout


def get_commit_message(sha: str) -> str:
    """Get commit message."""
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B", sha],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def get_commit_author(sha: str) -> str:
    """Get commit author."""
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%an", sha],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def has_parent_commit(sha: str) -> bool:
    """Check if commit has a parent (i.e., not an initial commit)."""
    result = subprocess.run(
        ["git", "rev-parse", f"{sha}^@"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return bool(result.stdout.strip())


def get_initial_commit_diff() -> str:
    """Get diff for initial commit (all files in the commit)."""
    cmd = ["git", "show", "HEAD", "--", *config.FILE_PATTERNS]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout
