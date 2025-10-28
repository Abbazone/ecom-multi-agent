# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    CHROMA_DIR=/.chroma

# Install system deps (curl for healthcheck; build tools minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Install deps
RUN python -m pip install --upgrade pip \
 && pip install -r requirements.txt

# (Optional) Pre-download sentence-transformers model to avoid cold start
# RUN python - <<'PY'
# from sentence_transformers import SentenceTransformer
# SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# PY

# Add application code
COPY . .

# Create non-root user and ensure Chroma dir exists and is writable
RUN useradd -m -u 10001 appuser \
 && mkdir -p ${CHROMA_DIR} \
 && chown -R appuser:appuser ${CHROMA_DIR} /app

USER appuser

EXPOSE 8000

# Healthcheck hits /healthz (FastAPI should expose it)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Default entrypoint: uvicorn (no reload in container)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]