# Multi-stage production build for harness-memory runtime
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY core ./core
COPY mcp ./mcp
COPY migrations ./migrations
RUN pip install --no-cache-dir --prefix=/install .

# Production runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create unprivileged appuser (UID 10001, GID 10001)
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g 10001 -m -s /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application and migration assets
COPY alembic.ini .
COPY pyproject.toml .
COPY migrations ./migrations
COPY core ./core
COPY mcp ./mcp

# Set permissions
RUN chown -R appuser:appuser /app

USER 10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.create_connection(('127.0.0.1', 8000), timeout=2); s.close()" || exit 1

CMD ["python", "-m", "mcp.server.app"]
