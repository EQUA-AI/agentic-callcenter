# Consolidated Frontend Dockerfile - Chainlit Application
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY consolidated-frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Chainlit application files
COPY consolidated-frontend/chainlit_app.py .
COPY consolidated-frontend/azure_foundry_client.py .
COPY consolidated-frontend/chainlit.md .

# Copy Chainlit configuration
COPY consolidated-frontend/.chainlit ./.chainlit

# Copy static assets and public files
COPY consolidated-frontend/public ./public

# Create directories for Chainlit files and logs
RUN mkdir -p /app/.files /app/logs

# Set environment variables for Chainlit
ENV PYTHONPATH=/app
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8080
ENV PYTHONUNBUFFERED=1

# Default Azure AI Foundry configuration (will be overridden by container app env vars)
ENV AZURE_AI_FOUNDRY_ENDPOINT=""
ENV AGENT_ID=""

# Expose port
EXPOSE 8080

# Health check - Updated for Chainlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Start the Chainlit application
CMD ["python", "-m", "chainlit", "run", "chainlit_app.py", "--host", "0.0.0.0", "--port", "8080"]
