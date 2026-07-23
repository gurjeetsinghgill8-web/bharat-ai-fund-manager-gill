# ══════════════════════════════════════════════════════════════
# Dockerfile — Bharat AI Fund Manager Gill FastAPI Backend
# Phase 2 / Brick 2.3 — Hugging Face Spaces Docker deployment
#
# Hugging Face Spaces requirements:
#   - Must expose port 7860
#   - App runs as non-root user (HF requirement)
#   - Python files must be in /app
# ══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Hugging Face requirement)
RUN useradd -m -u 1000 appuser

# Working directory
WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements_fastapi.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_fastapi.txt

# Copy all project Python files
COPY *.py ./
COPY fastapi_app/ ./fastapi_app/
COPY jarvis_keys.txt ./

# Create directories needed at runtime
RUN mkdir -p /app/data_cache /app/screener_cache /app/reports && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start FastAPI with uvicorn
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
