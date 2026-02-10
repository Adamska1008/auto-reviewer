import os
import sys
from loguru import logger

# GitHub API Configuration
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")  # owner/repo format

# Auto Reviewer Configuration
AUTO_REVIEWER_API_KEY = os.getenv("AUTO_REVIEWER_API_KEY")
AUTO_REVIEWER_BASE_URL = os.getenv("AUTO_REVIEWER_BASE_URL")
AUTO_REVIEWER_MODEL = os.getenv("AUTO_REVIEWER_MODEL", "gpt-4.1")

# Which file to track
_raw_patterns = os.getenv("AUTO_REVIEWER_FILE_PATTERNS", "*.py")
FILE_PATTERNS = [pattern.strip() for pattern in _raw_patterns.split(",")]


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
    )


setup_logging()
