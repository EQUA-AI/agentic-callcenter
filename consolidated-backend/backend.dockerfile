# Consolidated Backend Dockerfile (API + Functions)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy shared utilities from parent directories
COPY ../api/routers ./routers
COPY ../api/utils ./utils
COPY ../api/foundry_agent.py ./
COPY ../api/conversation_store.py ./

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 80

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AZURE_FUNCTIONS_ENVIRONMENT=Production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
