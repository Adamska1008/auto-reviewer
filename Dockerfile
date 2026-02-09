FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install git (required for getting diff and commit info)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /build

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY main.py .
COPY prompts ./prompts/

# Build and install the package
RUN uv tool install .

# Copy entrypoint script to root
COPY entrypoint.sh /

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/build
ENV GITHUB_API_URL=https://api.github.com

# Set entrypoint (use bash explicitly to avoid permission issues)
ENTRYPOINT ["bash", "/entrypoint.sh"]
