"""Auto Code Reviewer - Main entry point."""

from loguru import logger
from unidiff import PatchSet

from auto_reviewer import config
from auto_reviewer.ast_analysis import (
    NodeInfo,
    analyze_added_code,
    extract_parent_scope,
)
from auto_reviewer.github import GitHubClient
from auto_reviewer.git import (
    get_commit_author,
    get_commit_message,
    get_current_commit_sha,
    get_git_diff,
    is_initial_commit,
)
from auto_reviewer.llm import call_llm
from auto_reviewer.template import render_prompt


def get_added_line_number_from_diff(diff_text: str) -> dict[str, list[int]]:
    patch = PatchSet(diff_text)
    results = {}  # result is a dict of {<FILENAME>: [LINE NUMBER ARRAY]}
    for file in patch:
        linenos = []
        for hunk in file:
            current_line_no = hunk.target_start
            for line in hunk:
                if line.is_added:
                    linenos.append(current_line_no)
                if not line.is_removed:
                    current_line_no += 1
        if linenos:
            results[file.path] = linenos
    return results


def main():
    """Main entry point for the auto reviewer."""
    config.setup_logging()
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
    commit_msg = get_commit_message(commit_sha)
    commit_author = get_commit_author(commit_sha)

    base_commit = None
    # Check if this is the initial commit (no parent)
    if not is_initial_commit(commit_sha):
        base_commit = f"HEAD~{config.PUSH_COMMITS_COUNT}"
    no_context_diff_output = get_git_diff("HEAD", base_commit)
    rich_context_diff_output = get_git_diff("HEAD", base_commit, "-U10")
    logger.info(
        f"Got diff from {base_commit} to {commit_sha[:7]} "
        f"({config.PUSH_COMMITS_COUNT} commit(s)) by {commit_author}"
    )

    if not no_context_diff_output.strip():
        logger.info("No tracked files changed, skipping review")
        return

    # ====================================
    # 2. Get context of each hunk, including the parent block of each hunk
    # ====================================
    added_lineno = get_added_line_number_from_diff(no_context_diff_output)
    file_analysis: dict[str, list[NodeInfo]] = {}
    for filename, linenos in added_lineno.items():
        file_analysis[filename] = analyze_added_code(filename, linenos)

    related_context = dict(
        map(
            lambda item: (item[0], extract_parent_scope(item[1])), file_analysis.items()
        )
    )

    # =========================================================================
    # 3. 获取调用的函数，与引用位置信息 
    # =========================================================================
    


    # =========================================================================
    # 4. Render Jinja2 template
    # =========================================================================
    prompt = render_prompt(
        template_name="with_analysis.j2",
        diff_content=rich_context_diff_output,
        commit_sha=commit_sha[:7],
        commit_author=commit_author,
        commit_message=commit_msg,
        language=config.AUTO_REVIEWER_LANGUAGE,
        related_context=related_context,
    )

    # Print full prompt in debug mode
    if config.AUTO_REVIEWER_DEBUG:
        print("\n" + "=" * 80)
        print("DEBUG: FULL PROMPT CONTENT")
        print("=" * 80)
        print(prompt)
        print("=" * 80 + "\n")

    # =========================================================================
    # 5. Call LLM API
    # =========================================================================
    review_result = call_llm(prompt)

    # Output to stdout (GitHub Actions logs)
    print("\n" + "=" * 80)
    print("CODE REVIEW RESULT:")
    print("=" * 80)
    print(review_result)
    print("=" * 80 + "\n")

    # =========================================================================
    # 6. Post to GitHub (if token is available)
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
