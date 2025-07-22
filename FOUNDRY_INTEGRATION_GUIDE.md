# Azure AI Foundry Integration Guide

This guide walks you through replacing the vanilla agents with Azure AI Foundry agents in your agentic call center deployment.

## Prerequisites

✅ Existing deployment in `rg-WeddingAgenticCallcenter`  
✅ Azure OpenAI resource `WeddingUSAI` with `gpt-4o` deployed  
✅ Working Container Apps, Search, and other infrastructure  

## Step 1: Create Azure AI Foundry Hub and Project

### 1.1 Create Hub & Project

1. Go to **Azure Portal** → **Azure AI Foundry** → **"Create hub"**

   - **Hub name**: `wedding-foundry`
   - **Resource group**: `rg-WeddingAgenticCallcenter`
   - **Region**: `East US 2` (matches other resources)

2. Inside the hub, click **"Create project"**

   - **Project name**: `WeddingConcierge`
   - Leave default quota; click **Create**

3. **Copy the project connection string** (format: `https://wedding-foundry.eastus2.api.azureml.ms`)

### 1.2 Connect Existing Resources

In your project, go to **"Connected resources"** → **+ Add**

| Type | Resource | Purpose |
|------|----------|---------|
| Azure OpenAI | `WeddingUSAI` (existing) | Hosts the gpt-4o model |
| Azure AI Search | `dev-search-3dirbnu5qgcl2` | RAG enrichment |

### 1.3 Verify Model Deployment

Ensure `gpt-4o` is deployed in your Azure OpenAI resource:
- Go to **Project** → **Models + endpoints** → **Deploy model**
- If not deployed: **Source**: Azure OpenAI, **Model**: GPT-4o, **Deployment name**: `gpt-4o`

## Step 2: Grant Managed Identity Access

Run these Azure CLI commands to grant the managed identity access to your Foundry project:

```bash
# Login with an Owner account on the subscription
AZ_RG=rg-WeddingAgenticCallcenter
MI_ID=$(az identity show -g $AZ_RG -n dev-uami-3dirbnu5qgcl2 --query principalId -o tsv)
PROJ_ID=$(az ml workspace show --name WeddingConcierge --resource-group $AZ_RG --query id -o tsv)

az role assignment create \\
  --assignee-object-id $MI_ID \\
  --assignee-principal-type ServicePrincipal \\
  --role "Azure AI Developer" \\
  --scope $PROJ_ID
```

## Step 3: Create Your AI Agent

1. In Azure AI Foundry project, go to **"Agents"** → **"+ Create agent"**
2. Configure your agent with:
   - **Name**: Wedding Concierge Agent
   - **Instructions**: Add your specific agent instructions
   - **Model**: gpt-4o
   - Connect your search index for RAG if needed
3. **Copy the Agent ID** (format: `asst_xxxxx`)

## Step 4: Deploy the Updated Code

The code has been updated to support Azure AI Foundry. Now deploy with the new environment variables:

```bash
# Set the Foundry endpoint (replace with your actual endpoint)
azd env set AZURE_AI_FOUNDRY_ENDPOINT "https://wedding-foundry.eastus2.api.azureml.ms"

# Set your agent ID (replace with your actual agent ID)
azd env set AGENT_ID "asst_your_agent_id_here"

# Enable Foundry agent
azd env set USE_FOUNDRY_AGENT "true"

# Deploy the updated configuration
azd deploy
```

## Step 5: Test the Integration

1. **Open your UI**: Visit the Container App URL from `azd show`
2. **Send a test message**: Type "Hello" in the chat interface
3. **Verify response**: You should see responses from your Foundry agent instead of vanilla agents

## Step 6: Monitor and Troubleshoot

### Check Logs
```bash
# API Container logs
az containerapp logs show --name dev-api-3dirbnu5qgcl2 --resource-group rg-WeddingAgenticCallcenter --tail 50

# Functions logs  
az containerapp logs show --name dev-func-3dirbnu5qgcl2 --resource-group rg-WeddingAgenticCallcenter --tail 50
```

### Common Issues

1. **"Import azure.ai.agents could not be resolved"**
   - This is expected until deployment - the packages install during container build

2. **"Agent not found" errors**
   - Verify `AGENT_ID` is set correctly
   - Verify the agent exists in your Foundry project

3. **Permission errors**
   - Verify managed identity has "Azure AI Developer" role on the project
   - Check the role assignment was successful

## Step 7: Rollback (if needed)

To revert to vanilla agents:

```bash
azd env set USE_FOUNDRY_AGENT "false"
azd deploy
```

## Environment Variables Reference

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | `https://wedding-foundry.eastus2.api.azureml.ms` | Your Foundry project endpoint |
| `AGENT_ID` | `asst_abc123xyz` | Your agent's unique identifier |
| `USE_FOUNDRY_AGENT` | `true` | Enable/disable Foundry agent |

## What Changed in the Code

- ✅ Added Azure AI Foundry SDK dependencies
- ✅ Created `foundry_agent.py` modules
- ✅ Updated API router to support both vanilla and Foundry agents
- ✅ Added environment variable configuration
- ✅ Updated Bicep infrastructure templates

The system now supports both vanilla agents (fallback) and Foundry agents (when enabled), allowing for seamless switching between implementations.
