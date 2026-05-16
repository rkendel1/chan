# Multi-stage build for Chandra OCR HTTP API
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Install Python dependencies
# For vLLM mode (lightweight), we only need base dependencies
RUN uv pip install --system --no-cache -e .

# For HuggingFace mode, uncomment the line below
# RUN uv pip install --system --no-cache -e ".[hf]"

# Install Flask for HTTP server (from dev dependencies)
RUN pip install --no-cache-dir flask

# Copy application code
COPY chandra/ ./chandra/
COPY README.md LICENSE ./

# Expose port for HTTP server
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=5000
ENV INFERENCE_METHOD=vllm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Run the HTTP server
CMD ["python", "-m", "chandra.scripts.http_server"]
