"""Auto Code Reviewer - Main entry point."""

from loguru import logger

from auto_reviewer import config
from auto_reviewer.github import GitHubClient
from auto_reviewer.git import (
    get_commit_author,
    get_commit_message,
    get_current_commit_sha,
    get_git_diff,
)
from auto_reviewer.llm import call_llm
from auto_reviewer.template import render_prompt


def main():
    """Main entry point for the auto reviewer."""
    logger.info("Auto Code Reviewer starting...")

    # =========================================================================
    # 1. Validate environment variables
    # =========================================================================
    if not config.AUTO_REVIEWER_API_KEY:
        logger.error("AUTO_REVIEWER_API_KEY environment variable is required")
        raise ValueError("Missing AUTO_REVIEWER_API_KEY")

    if not config.GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set, will not post comments to GitHub")

    # =========================================================================
    # 2. Get git diff and commit metadata
    # =========================================================================
    commit_sha = get_current_commit_sha()
    diff_output = get_git_diff("HEAD~1", "HEAD")
    commit_msg = get_commit_message(commit_sha)
    commit_author = get_commit_author(commit_sha)

    logger.info(f"Got diff from HEAD~1 to {commit_sha[:7]} by {commit_author}")

    if not diff_output.strip():
        logger.info("No tracked files changed, skipping review")
        return

    # =========================================================================
    # 3. Render Jinja2 template
    # =========================================================================
    prompt = render_prompt(
        template_name="simple.j2",
        diff_content=diff_output,
        commit_sha=commit_sha[:7],
        commit_author=commit_author,
        commit_message=commit_msg,
    )

    # =========================================================================
    # 4. Call LLM API
    # =========================================================================
    review_result = call_llm(prompt)

    # Output to stdout (GitHub Actions logs)
    print("\n" + "=" * 80)
    print("CODE REVIEW RESULT:")
    print("=" * 80)
    print(review_result)
    print("=" * 80 + "\n")

    # =========================================================================
    # 5. Post to GitHub (if token is available)
    # =========================================================================
    if config.GITHUB_TOKEN and config.GITHUB_REPOSITORY:
        github_client = GitHubClient(
            token=config.GITHUB_TOKEN,
            repository=config.GITHUB_REPOSITORY,
            api_url=config.GITHUB_API_URL,
        )

        github_client.create_commit_comment(commit_sha=commit_sha, body=review_result)
        github_client.close()
    else:
        logger.info("Skipping GitHub comment posting (no token/repository)")

    logger.info("Auto Code Reviewer completed successfully")


if __name__ == "__main__":
    main()
