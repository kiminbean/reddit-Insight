# Reddit Insight Dashboard
# Multi-stage build for smaller final image

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY pyproject.toml .
COPY src/ src/

# Install package and dependencies
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ src/
COPY pyproject.toml .

# Create data directory
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PORT=8888

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/health')"

# Default command
CMD ["python", "-m", "uvicorn", "reddit_insight.dashboard.app:app", "--host", "0.0.0.0", "--port", "8888"]
