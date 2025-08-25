# Consolidated Backend Dockerfile (API + Functions)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy consolidated backend application code
COPY app.py .
COPY messaging_connect.py .
COPY config_manager.py .
COPY multi_agent_router.py .
COPY servicebus_processor.py .
COPY start_services.py .
COPY conversation_store.py .
COPY multi_container_conversation_store.py .
COPY container_manager.py .
COPY setup_config.py .
COPY host.json .
COPY foundry_agent.py .
COPY function_app.py .

# Copy routers and utilities from consolidated backend
COPY routers/ ./routers/
COPY templates ./templates

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
