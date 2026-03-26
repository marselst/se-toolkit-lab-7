# Bot Dockerfile - uses uv for dependency management
# See https://docs.astral.sh/uv/guides/integration/docker/

ARG REGISTRY_PREFIX=harbor.pg.innopolis.university/docker-hub-cache/
FROM ${REGISTRY_PREFIX}python:3.14.2-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Setup non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Set working directory
WORKDIR /app

# Copy bot project files
COPY bot/pyproject.toml bot/uv.lock ./

# Sync dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Copy the rest of the bot code
COPY bot/ ./bot/

# Change ownership to nonroot user
RUN chown -R nonroot:nonroot /app

# Switch to non-root user
USER nonroot

# Set Python path
ENV PATH="/app/.venv/bin:$PATH"

# Run the bot
CMD ["python", "bot/bot.py"]
