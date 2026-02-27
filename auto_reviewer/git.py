"""Git utilities for getting commit info and diffs."""

import os
import subprocess
from loguru import logger

from auto_reviewer import config

ROOT_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def try_execute_command(*cmd, check: bool = True) -> str:
    """
    Try to execute a git commit from shell. May git error.
    Args:
        cmd: commands to execute
        check: if True, raise RuntimeError when command fails
    Returns:
        Command stdout as string
    """
    clean_cmd = [str(c) for c in cmd if c]
    if not clean_cmd:
        return ""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(clean_cmd)
        logger.error(f"Error: command {' '.join(cmd_str)} failed")
        logger.error(f"Stderr: {e.stderr.strip()}")
        if check:
            raise RuntimeError(f"command failed: {cmd_str}") from e
        return e.stdout


def get_current_commit_sha() -> str:
    """Get current commit SHA."""
    logger.debug(f"Running git in directory: {os.getcwd()}")
    sha = try_execute_command("git", "rev-parse", "HEAD")
    return sha.strip()


def get_git_diff(new_commit: str, old_commit: str | None = None) -> str:
    """
    Get git diff between two commits with extended context.
    If arg `old_commit`, set old_commit hash to root hash.
    """
    if old_commit is None:
        old_commit = ROOT_HASH
    cmd = ["git", "diff", "-U10", old_commit, new_commit, "--", *config.FILE_PATTERNS]
    return try_execute_command(*cmd)


def get_commit_message(sha: str) -> str:
    """Get commit message."""
    return try_execute_command("git", "log", "-1", "--pretty=%B", sha).strip()


def get_commit_author(sha: str) -> str:
    """Get commit author."""
    return try_execute_command("git", "log", "-1", "--pretty=%an", sha).strip()


def is_initial_commit(sha: str) -> bool:
    """Check if commit is initial (i.e., has no parent)."""
    try:
        parents = try_execute_command("git", "rev-parse", "--parents", "-1", sha)
        return len(parents.strip().split()) == 1
    except RuntimeError:
        return False
