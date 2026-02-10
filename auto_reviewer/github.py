"""GitHub API client for posting commit comments."""

import httpx
from loguru import logger

from auto_reviewer import config


class GitHubClient:
    """GitHub API client for posting commit comments."""

    def __init__(
        self, token: str, repository: str, api_url: str = config.GITHUB_API_URL
    ):
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
