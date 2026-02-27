"""Auto Code Reviewer - Main entry point."""

from loguru import logger
from unidiff import PatchSet

import tree_sitter as ts
import tree_sitter_python as tspython

from auto_reviewer import config
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

PY_LANGUAGAE = ts.Language(tspython.language())
parser = ts.Parser(language=PY_LANGUAGAE)


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


MAX_LINE_WIDTH = 200


def analyze_added_code(file_path: str, added_lineno: list[int]):
    with open(file_path, "rb") as f:
        code_bytes = f.read()
    tree = parser.parse(code_bytes)
    root_node = tree.root_node

    results = []
    for lineno in added_lineno:
        target_line = lineno - 1
        node = root_node.descendant_for_point_range(
            (target_line, 0), (target_line, MAX_LINE_WIDTH)
        )
        assert node is not None
        node_info = {
            "line": lineno,
            "type": node.type,
            "text": node.text.decode("utf-8") if node.text else "",
            "parent_scope": find_parent_scope(node),
        }
        results.append(node_info)
    return results


def find_parent_scope(node: ts.Node) -> ts.Node | None:
    current = node
    while current:
        if current.type in ["function_definition", "class_definition"]:
            return current
        current = current.parent
    return None


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
    diff_output = get_git_diff("HEAD", base_commit)
    logger.info(
        f"Got diff from {base_commit} to {commit_sha[:7]} "
        f"({config.PUSH_COMMITS_COUNT} commit(s)) by {commit_author}"
    )

    if not diff_output.strip():
        logger.info("No tracked files changed, skipping review")
        return

    # ====================================
    # 2. Get lineno of each hunk
    # ====================================

    # =========================================================================
    # 3. Render Jinja2 template
    # =========================================================================
    prompt = render_prompt(
        template_name="simple.j2",
        diff_content=diff_output,
        commit_sha=commit_sha[:7],
        commit_author=commit_author,
        commit_message=commit_msg,
        language=config.AUTO_REVIEWER_LANGUAGE,
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
