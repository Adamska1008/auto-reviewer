"""LLM client for code review."""

from loguru import logger
from openai import OpenAI

from auto_reviewer import config


def call_llm(prompt: str) -> str:
    """
    Call LLM API with the given prompt.

    Args:
        prompt: The prompt to send to LLM

    Returns:
        The LLM response text

    Raises:
        ValueError: If LLM returns empty response
    """
    client = OpenAI(
        base_url=config.AUTO_REVIEWER_BASE_URL, api_key=config.AUTO_REVIEWER_API_KEY
    )

    logger.info(f"Calling LLM API: model={config.AUTO_REVIEWER_MODEL}, base_url={config.AUTO_REVIEWER_BASE_URL}")
    logger.debug(f"Prompt length: {len(prompt)} characters")

    completion = client.chat.completions.create(
        model=config.AUTO_REVIEWER_MODEL, messages=[{"role": "user", "content": prompt}]
    )

    response = completion.choices[0].message.content

    if response is None:
        logger.error("LLM returned empty response")
        raise ValueError("Empty response from LLM")

    logger.info(f"Received LLM response: {len(response)} characters")
    return response
