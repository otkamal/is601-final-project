# ---- Builder stage: installs Python dependencies, discarded from the final image ----
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build-time system dependencies, for any dependency without a prebuilt
# wheel for this platform/Python version. Discarded along with this stage.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip "setuptools>=78.1.1" wheel

# Install into an isolated prefix (not this interpreter's own
# site-packages) so only the app's actual dependencies -- not pip,
# setuptools, or the compilers above -- get copied into the runtime image.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Runtime stage: slim final image, no build tools or pip ----
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime system dependencies only: curl for the healthcheck, libssl3 for
# compiled extensions (bcrypt/cryptography) that link against it dynamically.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libssl3 curl && \
    rm -rf /var/lib/apt/lists/*

# Drop the base image's own bundled pip/setuptools -- nothing at runtime
# needs them, and pip vendors third-party libraries (e.g. msgpack) whose
# CVE fixes lag behind pip releases, so the safest fix is to not ship pip
# in the runtime image at all rather than chase its vendored versions.
RUN python -m pip uninstall -y pip setuptools || true

# Create non-root user
RUN groupadd -r appgroup && \
    useradd -r -g appgroup appuser

# Bring in only the installed dependencies from the builder stage.
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Ensure correct ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check for the service
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run database initialization before starting the app
CMD python -m app.database_init && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
