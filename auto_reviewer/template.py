"""Template utilities for rendering prompts."""

from importlib import resources
from jinja2 import Environment, FunctionLoader
from loguru import logger

from auto_reviewer.ast_analysis import CodeContext


@logger.catch
def load_prompt_resource(name: str) -> str:
    """Load Jinja2 template resource from auto_reviewer.prompts package."""
    return (
        resources.files("auto_reviewer.prompts")
        .joinpath(name)
        .read_text(encoding="utf-8")
    )


def render_prompt(
    template_name: str,
    diff_content: str,
    commit_sha: str,
    commit_author: str,
    commit_message: str,
    language: str,
    related_context: dict[str, list[CodeContext]],
) -> str:
    """
    Render prompt template with given context.

    Args:
        template_name: Name of the template file (e.g., "simple.j2")
        diff_content: Git diff output
        commit_sha: Short commit SHA
        commit_author: Author of the commit
        commit_message: Commit message
        language: Output language for review

    Returns:
        Rendered prompt with prompt repetition applied
    """
    env = Environment(loader=FunctionLoader(load_prompt_resource))
    template = env.get_template(template_name)
    prompt = template.render(
        diff_content=diff_content,
        commit_sha=commit_sha,
        commit_author=commit_author,
        commit_message=commit_message,
        language=language,
        related_context=related_context,
    )
    logger.debug(f"Generated prompt (length: {len(prompt)})")
    logger.debug(f"Prompt preview: {prompt[:500]}...")
    return prompt
