# Bot Provisional - Multi-stage Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash botuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy Spanish model
RUN python -m spacy download es_core_news_sm

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Development stage
FROM base as development

# Expose ports for development
EXPOSE 8000

# Default command for development
CMD ["python", "-m", "src.dashboard.main"]

# Production stage
FROM base as production

# Copy only necessary files for production
COPY --from=base /app/src ./src
COPY --from=base /app/config ./config
COPY --from=base /app/docs ./docs

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["uvicorn", "src.dashboard.main:app", "--host", "0.0.0.0", "--port", "8000"]