import os
import subprocess
import sys
from importlib import resources

import httpx
from loguru import logger
from openai import OpenAI

# =============================================================================
# Configuration
# =============================================================================

# GitHub API Configuration
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")  # owner/repo format

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "deepseek/deepseek-v3.2"

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
)


# =============================================================================
# GitHub API Client
# =============================================================================


class GitHubClient:
    """GitHub API client for posting commit comments."""

    def __init__(self, token: str, repository: str, api_url: str = GITHUB_API_URL):
        self.token = token
        self.repository = repository
        self.api_url = api_url
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def create_commit_comment(self, commit_sha: str, body: str) -> dict:
        """
        Create a comment for a specific commit.

        API Endpoint: POST /repos/{owner}/{repo}/commits/{commit_sha}/comments
        Docs: https://docs.github.com/rest/commits/comments#create-a-commit-comment
        """
        url = f"{self.api_url}/repos/{self.repository}/commits/{commit_sha}/comments"

        response = self.client.post(
            url, json={"body": body}, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        logger.info(f"Successfully posted comment to commit {commit_sha[:7]}")
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self.client.close()


# =============================================================================
# Git Functions
# =============================================================================


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
    cmd = ["git", "diff", "-U10", old_commit, new_commit, "--", "*.py"]
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


# =============================================================================
# Template Functions
# =============================================================================


@logger.catch
def load_prompt_resource(name: str) -> str:
    """Load Jinja2 template resource."""
    return resources.files("prompts").joinpath(name).read_text(encoding="utf-8")


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point for the auto reviewer."""
    logger.info("Auto Code Reviewer starting...")

    # =========================================================================
    # 1. Validate environment variables
    # =========================================================================
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY environment variable is required")
        raise ValueError("Missing OPENROUTER_API_KEY")

    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set, will not post comments to GitHub")

    # =========================================================================
    # 2. Get git diff and commit metadata
    # =========================================================================
    commit_sha = get_current_commit_sha()
    diff_output = get_git_diff("HEAD~1", "HEAD")
    commit_msg = get_commit_message(commit_sha)
    commit_author = get_commit_author(commit_sha)

    logger.info(f"Got diff from {'HEAD~1'} to {commit_sha[:7]} by {commit_author}")

    if not diff_output.strip():
        logger.info("No Python files changed, skipping review")
        return

    # =========================================================================
    # 3. Render Jinja2 template
    # =========================================================================
    from jinja2 import Environment, FunctionLoader

    env = Environment(loader=FunctionLoader(load_prompt_resource))
    template = env.get_template("simple.j2")
    prompt = template.render(
        diff_content=diff_output,
        commit_sha=commit_sha[:7],
        commit_author=commit_author,
        commit_message=commit_msg,
    )
    # use a simple technique in paper: Prompt Repetition Improves Non-Reasoning LLMs
    prompt += prompt

    logger.debug(f"Generated prompt (length: {len(prompt)})")
    logger.debug(f"Prompt message: {prompt[:1000]}...")

    # =========================================================================
    # 4. Call OpenRouter API
    # =========================================================================
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

    logger.info(f"Calling OpenRouter API with model: {OPENROUTER_MODEL}")
    completion = client.chat.completions.create(
        model=OPENROUTER_MODEL, messages=[{"role": "user", "content": prompt}]
    )

    review_result = completion.choices[0].message.content

    if review_result is None:
        logger.error("LLM returned empty response")
        raise ValueError("Empty response from LLM")

    logger.info("Got review result from LLM")

    # Output to stdout (GitHub Actions logs)
    print("\n" + "=" * 80)
    print("CODE REVIEW RESULT:")
    print("=" * 80)
    print(review_result)
    print("=" * 80 + "\n")

    # =========================================================================
    # 5. Post to GitHub (if token is available)
    # =========================================================================
    if GITHUB_TOKEN and GITHUB_REPOSITORY:
        github_client = GitHubClient(
            token=GITHUB_TOKEN, repository=GITHUB_REPOSITORY, api_url=GITHUB_API_URL
        )

        github_client.create_commit_comment(commit_sha=commit_sha, body=review_result)
        github_client.close()
    else:
        logger.info("Skipping GitHub comment posting (no token/repository)")

    logger.info("Auto Code Reviewer completed successfully")


if __name__ == "__main__":
    main()
