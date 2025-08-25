# Consolidated Frontend

This directory contains the Chainlit-based frontend application with direct Azure AI Foundry integration.

## 📁 Current Files

### Core Application
- **`chainlit_app.py`** - Main Chainlit application with Azure AI Foundry integration
- **`azure_foundry_client.py`** - Azure AI Foundry client for direct agent communication
- **`requirements.txt`** - Python dependencies

### Configuration
- **`.env.example`** - Environment configuration template
- **`.env`** - Local environment configuration (not in git)
- **`chainlit.md`** - Chainlit app description
- **`.chainlit/`** - Chainlit configuration directory

### Assets & Styling
- **`public/`** - Static assets (CSS, JS, images)
  - `custom.css` - Custom styling for EPCON AI branding
  - `custom.js` - Custom JavaScript functionality
  - `animations.css` - UI animations
  - `placeholder.png` - Placeholder image

### Docker & Documentation
- **`frontend.dockerfile`** - Docker configuration
- **`CUSTOMIZATION_COMPLETE.md`** - Documentation of completed customizations
- **`FRONTEND_CUSTOMIZATION.md`** - Guide to frontend customization

### Testing
- **`test_foundry_connection.py`** - Tests Azure AI Foundry integration

## 🚀 Quick Start

1. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure AI Foundry configuration
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   chainlit run chainlit_app.py --port 8501
   ```

4. **Access the app:**
   Open http://localhost:8501 in your browser

## 🤖 AI Agents

The application connects to three specialized Azure AI Foundry agents:
- **Hajj & Umrah Services** (🕋) - Spiritual journey guidance
- **Wedding Planning** (💒) - Complete wedding coordination  
- **EPCON AI** (🤖) - Technical diagnostic & spare parts

## 🔧 Configuration

Key environment variables in `.env`:
- `AZURE_AI_FOUNDRY_ENDPOINT` - Your Azure AI Foundry project endpoint
- `AGENT_ID` - Default agent ID (optional)

Authentication uses `DefaultAzureCredential` which supports:
- Azure CLI login (recommended for local development)
- Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
- Managed Identity (for Azure deployments)
