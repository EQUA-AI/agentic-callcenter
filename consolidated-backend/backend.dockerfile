# Consolidated Backend Dockerfile (API + Functions)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY consolidated-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy consolidated backend application code
COPY consolidated-backend/app.py .
COPY consolidated-backend/messaging_connect.py .
COPY consolidated-backend/config_manager.py .
COPY consolidated-backend/multi_agent_router.py .

# Copy shared utilities and routers from parent directories
COPY api/routers ./routers
COPY consolidated-backend/routers/* ./routers/
COPY consolidated-backend/templates ./templates
COPY api/utils ./utils
COPY api/conversation_store.py .
COPY api/foundry_agent.py .

# Copy functions code
COPY functions/foundry_agent.py ./functions_foundry_agent.py
COPY functions/function_app.py ./function_app.py

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
