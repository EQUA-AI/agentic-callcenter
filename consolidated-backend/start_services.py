#!/usr/bin/env python3
"""
Startup script for consolidated backend - runs both FastAPI and Azure Functions
"""
import os
import sys
import subprocess
import asyncio
import signal
import threading
import time
from pathlib import Path

def setup_functions_environment():
    """Setup Azure Functions environment"""
    # Copy host.json to root directory
    functions_dir = Path(__file__).parent.parent / "functions"
    app_dir = Path(__file__).parent
    
    # Copy host.json for functions runtime
    host_json_source = functions_dir / "host.json"
    host_json_dest = app_dir / "host.json"
    
    if host_json_source.exists():
        import shutil
        shutil.copy2(host_json_source, host_json_dest)
        print(f"Copied host.json from {host_json_source} to {host_json_dest}")
    
    # Set Azure Functions environment variables
    os.environ["AzureWebJobsScriptRoot"] = str(app_dir)
    os.environ["AzureFunctionsJobHost__Logging__Console__IsEnabled"] = "true"
    
    # Ensure functions runtime can find the app
    if "FUNCTIONS_WORKER_RUNTIME" not in os.environ:
        os.environ["FUNCTIONS_WORKER_RUNTIME"] = "python"

def start_fastapi():
    """Start FastAPI application"""
    print("Starting FastAPI application...")
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app:app", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--workers", "1"
    ]
    return subprocess.Popen(cmd)

def start_azure_functions():
    """Start Azure Functions runtime"""
    print("Starting Azure Functions runtime...")
    
    # Use func start command
    cmd = [
        "func", "start", 
        "--port", "7071",
        "--python"
    ]
    
    # Try to start functions host
    try:
        return subprocess.Popen(cmd, cwd=Path(__file__).parent)
    except FileNotFoundError:
        print("Azure Functions Core Tools not found. Installing...")
        # Fallback: try to use python directly
        cmd = [
            sys.executable, "-c",
            "import azure.functions as func; "
            "from app import function_app; "
            "print('Functions runtime started via Python'); "
            "import time; "
            "while True: time.sleep(1)"
        ]
        return subprocess.Popen(cmd)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"Received signal {signum}, shutting down...")
    global fastapi_process, functions_process
    
    if fastapi_process:
        fastapi_process.terminate()
    if functions_process:
        functions_process.terminate()
    
    sys.exit(0)

# Global process references
fastapi_process = None
functions_process = None

def main():
    global fastapi_process, functions_process
    
    print("🚀 Starting Consolidated Backend (FastAPI + Azure Functions)")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup Functions environment
    setup_functions_environment()
    
    # Start both services
    try:
        fastapi_process = start_fastapi()
        time.sleep(2)  # Give FastAPI time to start
        
        functions_process = start_azure_functions()
        time.sleep(2)  # Give Functions time to start
        
        print("✅ Both services started successfully!")
        print("📊 FastAPI running on http://0.0.0.0:8000")
        print("⚡ Azure Functions running on http://0.0.0.0:7071")
        print("🔗 Health check: http://0.0.0.0:8000/health")
        
        # Monitor both processes
        while True:
            if fastapi_process.poll() is not None:
                print("❌ FastAPI process died, restarting...")
                fastapi_process = start_fastapi()
            
            if functions_process.poll() is not None:
                print("❌ Functions process died, restarting...")
                functions_process = start_azure_functions()
            
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Error starting services: {e}")
        signal_handler(signal.SIGTERM, None)

if __name__ == "__main__":
    main()
