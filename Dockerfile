FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy dependency files first (for better Docker caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY main.py .
COPY prompts ./prompts/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV GITHUB_API_URL=https://api.github.com

# Set entrypoint
ENTRYPOINT ["uv", "run", "main.py"]
