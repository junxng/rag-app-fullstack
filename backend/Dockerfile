# Build stage
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    python3-dev \
    libpq-dev \
    postgresql-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.5.5 /uv /bin/uv

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies using uv with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.11.4 && \
    . .venv/bin/activate && \
    uv pip sync requirements.txt

# Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash app_user

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R app_user:app_user /app

# Switch to non-root user
USER app_user

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run migrations and start the application
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
