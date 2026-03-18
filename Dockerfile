# AWS Cost Sentinel - Docker Image

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements-dev.txt .

# Install Python dependencies (boto3 comes from requirements-dev.txt)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir boto3

# Copy application code
COPY src/ ./src/
COPY config.yaml.example ./config.yaml
COPY sentinel_cli.py .

# Create non-root user
RUN useradd -m -u 1000 sentinel && \
    chown -R sentinel:sentinel /app

USER sentinel

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "src.sentinel"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.sentinel import CostSentinel; s = CostSentinel(); s.get_status()" || exit 1