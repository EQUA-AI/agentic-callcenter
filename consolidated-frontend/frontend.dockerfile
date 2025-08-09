# Consolidated Frontend Dockerfile (Voice + UI)
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

# Copy consolidated frontend application code
COPY consolidated-frontend/app.py .

# Copy voice and UI code
COPY voice/app.py ./voice_app.py
COPY ui/chat.py ./ui_chat.py

# Copy UI static assets
COPY ui/public ./public

# Create static directory for UI assets and logs
RUN mkdir -p /app/static /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
