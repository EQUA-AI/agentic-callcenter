#!/bin/bash
"""
Startup Script for Backend Container
Runs diagnostics first, then starts the application
"""

echo "🚀 Starting Backend Container..."
echo "=================================="

# Run startup diagnostics
echo "🔍 Running startup diagnostics..."
python startup_diagnostic.py

# Check if diagnostics passed
if [ $? -ne 0 ]; then
    echo "❌ Startup diagnostics failed! Check the logs above for issues."
    echo "📋 Common issues to check:"
    echo "  - Missing environment variables"
    echo "  - Azure authentication issues"
    echo "  - Network connectivity"
    echo "  - Service Bus configuration"
    exit 1
fi

echo "✅ Diagnostics passed! Starting application..."

# Start the FastAPI application
exec python -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info
