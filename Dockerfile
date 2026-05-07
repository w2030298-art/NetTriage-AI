# =============================================================================
# NetTriage AI — Docker image
# =============================================================================
# Steps to build and run:
#   docker compose build
#   docker compose up -d
#   curl http://127.0.0.1:8000/healthz
# =============================================================================

FROM python:3.12-slim

# Install uv (fast Python package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency manifests first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install runtime dependencies only (no dev tools in production)
RUN uv sync --frozen --no-dev

# Copy application source
COPY src/ ./src/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash nettriage && \
    mkdir -p /app/data/uploads /app/data/exports && \
    chown -R nettriage:nettriage /app

# Switch to non-root user
USER nettriage

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz').read()"

# Start the application
CMD ["uv", "run", "uvicorn", "nettriage.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
