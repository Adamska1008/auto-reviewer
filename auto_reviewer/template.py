"""Template utilities for rendering prompts."""

from importlib import resources
from jinja2 import Environment, FunctionLoader
from loguru import logger


@logger.catch
def load_prompt_resource(name: str) -> str:
    """Load Jinja2 template resource from auto_reviewer.prompts package."""
    return resources.files("auto_reviewer.prompts").joinpath(name).read_text(
        encoding="utf-8"
    )


ENV = Environment(loader=FunctionLoader(load_prompt_resource))


def render_prompt(
    template_name: str,
    diff_content: str,
    commit_sha: str,
    commit_author: str,
    commit_message: str,
) -> str:
    """
    Render prompt template with given context.

    Args:
        template_name: Name of the template file (e.g., "simple.j2")
        diff_content: Git diff output
        commit_sha: Short commit SHA
        commit_author: Author of the commit
        commit_message: Commit message

    Returns:
        Rendered prompt with prompt repetition applied
    """
    template = ENV.get_template(template_name)
    prompt = template.render(
        diff_content=diff_content,
        commit_sha=commit_sha,
        commit_author=commit_author,
        commit_message=commit_message,
    )
    # Use technique from paper: Prompt Repetition Improves Non-Reasoning LLMs
    prompt += prompt

    logger.debug(f"Generated prompt (length: {len(prompt)})")
    logger.debug(f"Prompt preview: {prompt[:500]}...")
    return prompt
