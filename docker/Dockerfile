# Multi-stage production Dockerfile for AI Content OS
FROM python:3.14-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency specifications
COPY pyproject.toml ./

# Sync dependencies using uv
RUN uv sync --frozen --no-dev || uv pip install -r pyproject.toml

# Production runtime stage
FROM python:3.14-slim AS runner

WORKDIR /app

# Create non-root system user
RUN groupadd -g 999 appgroup && \
    useradd -r -u 999 -g appgroup appuser

# Copy virtual environment and application code from builder
COPY --from=builder /app /app
COPY . /app

# Set write permissions for log and user_data directories
RUN mkdir -p /app/user_data/logs /app/user_data/database && \
    chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AI_CONTENT_OS_ENV=production

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from modules.config import get_config; from modules.infrastructure import HealthChecker; h = HealthChecker(get_config()); exit(0 if h.check_readiness().status.value != 'UNHEALTHY' else 1)"

CMD ["python", "-m", "modules.infrastructure.startup"]
