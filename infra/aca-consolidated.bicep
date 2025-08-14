param uniqueId string
param prefix string
param userAssignedIdentityResourceId string
param userAssignedIdentityClientId string
param openAiEndpoint string
param cosmosDbEndpoint string
param cosmosDbDatabase string
param cosmosDbContainer string
param applicationInsightsConnectionString string
param containerRegistry string = '${prefix}acr${uniqueId}'
param location string = resourceGroup().location
param logAnalyticsWorkspaceName string
param acsEndpoint string
param serviceBusNamespaceFqdn string

param speechServiceKey string
param cognitiveServiceEndpoint string

// Container images - consolidated
param backendContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param frontendContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// Azure AI Foundry parameters
param foundryEndpoint string = ''
param agentId string = ''
param useFoundryAgent string = 'false'

// WhatsApp ACS parameters
param acsChannelRegistrationId string = ''

// Messaging Connect parameters
param messagingConnectEnabled bool = true
param whatsappChannelId string = ''
param smsChannelId string = ''

// Event Grid parameters
param existingEventGridTopicName string = 'AIWedding'

// Multi-agent configuration parameters
param multiAgentEnabled string = 'true'
param enableConfigUI string = 'true'

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

// Container App Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-11-02-preview' = {
  name: 'con-env-${uniqueId}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// ===== CONSOLIDATED BACKEND SERVICES =====

// Primary Backend Service (API + Functions) - Scalable design for future load balancing
resource backendContainerApp 'Microsoft.App/containerApps@2022-03-01' = {
  name: 'con-backend-${uniqueId}'
  location: location
  tags: {'azd-service-name': 'backend' }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false  // Internal access only
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: '${containerRegistry}.azurecr.io'
          identity: userAssignedIdentityResourceId
        }
      ]
    }
    template: {
      scale: {
        minReplicas: 1
        maxReplicas: 10  // Allow scaling for load - can add more instances when needed
      }
      containers: [
        {
          name: 'backend'
          image: backendContainerImage
          resources: {
            cpu: 2
            memory: '4Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTIONSTRING', value: applicationInsightsConnectionString }
            { name: 'AZURE_OPENAI_WHISPER_ENDPOINT', value: openAiEndpoint }
            { name: 'AZURE_OPENAI_WHISPER_DEPLOYMENT', value: 'whisper' }
            { name: 'AZURE_OPENAI_WHISPER_VERSION', value: '2024-02-01' }
            { name: 'COSMOSDB_ENDPOINT', value: cosmosDbEndpoint }
            { name: 'COSMOSDB_DATABASE', value: cosmosDbDatabase }
            { name: 'COSMOSDB_CONTAINER', value: cosmosDbContainer }
            { name: 'ACS_ENDPOINT', value: acsEndpoint }
            { name: 'ACS_CHANNEL_REGISTRATION_ID', value: acsChannelRegistrationId }
            { name: 'ServiceBusConnection__fullyQualifiedNamespace', value: serviceBusNamespaceFqdn }
            // Messaging Connect configuration
            { name: 'MESSAGING_CONNECT_ENABLED', value: string(messagingConnectEnabled) }
            { name: 'MESSAGING_CONNECT_ENDPOINT', value: '${acsEndpoint}/messaging/connect/v1' }
            { name: 'WHATSAPP_CHANNEL_ID', value: !empty(whatsappChannelId) ? whatsappChannelId : acsChannelRegistrationId }
            { name: 'SMS_CHANNEL_ID', value: smsChannelId }  // Infobip SMS channel ID
            // Foundry agent configuration
            { name: 'AZURE_AI_FOUNDRY_ENDPOINT', value: foundryEndpoint }
            { name: 'AGENT_ID', value: agentId }
            { name: 'USE_FOUNDRY_AGENT', value: useFoundryAgent }
            // Multi-tenant configuration
            { name: 'SERVICE_ROLE', value: 'backend' }
            { name: 'ENABLE_LOAD_BALANCING', value: 'false' }  // Single instance for now
            // Speech and Cognitive Services
            { name: 'SPEECH_KEY', value: speechServiceKey }
            { name: 'SPEECH_REGION', value: location }
            { name: 'COGNITIVE_SERVICE_ENDPOINT', value: cognitiveServiceEndpoint }
            // Multi-agent configuration
            { name: 'MULTI_AGENT_ENABLED', value: multiAgentEnabled }
            { name: 'ENABLE_CONFIG_UI', value: enableConfigUI }
            { name: 'COSMOS_DATABASE_NAME', value: cosmosDbDatabase }
          ]
        }
      ]
    }
  }
}

// ===== CONSOLIDATED FRONTEND SERVICE =====

// Frontend Service (Voice + UI)
resource frontendContainerApp 'Microsoft.App/containerApps@2022-03-01' = {
  name: 'con-frontend-${uniqueId}'
  location: location
  tags: {'azd-service-name': 'frontend' }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true  // External access for voice webhooks and UI
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: '${containerRegistry}.azurecr.io'
          identity: userAssignedIdentityResourceId
        }
      ]
    }
    template: {
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
      containers: [
        {
          name: 'frontend'
          image: frontendContainerImage
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTIONSTRING', value: applicationInsightsConnectionString }
            { name: 'ACS_ENDPOINT', value: acsEndpoint }
            { name: 'ACS_CHANNEL_REGISTRATION_ID', value: acsChannelRegistrationId }
            // Backend service URLs (single backend for now, ready for load balancing)
            { name: 'BACKEND_PRIMARY_URL', value: 'http://${backendContainerApp.name}' }
            { name: 'BACKEND_SECONDARY_URL', value: 'http://${backendContainerApp.name}' }  // Same as primary for now
            // Voice-specific environment variables
            { name: 'VOICE_NAME', value: 'en-US-AvaMultilingualNeural' }
            { name: 'COGNITIVE_SERVICE_ENDPOINT', value: cognitiveServiceEndpoint }
            { name: 'AZURE_OPENAI_WHISPER_ENDPOINT', value: openAiEndpoint }
            { name: 'AZURE_OPENAI_WHISPER_VERSION', value: '2024-02-01' }
            { name: 'AZURE_OPENAI_WHISPER_DEPLOYMENT', value: 'whisper' }
            { name: 'AZURE_OPENAI_WHISPER_KEY', value: '' }
            { name: 'SPEECH_KEY', value: speechServiceKey }
            { name: 'SPEECH_REGION', value: location }
            // Frontend configuration
            { name: 'SERVICE_ROLE', value: 'frontend' }
            { name: 'ENABLE_VOICE', value: 'true' }
            { name: 'ENABLE_CHAT', value: 'true' }
            { name: 'LOAD_BALANCING_MODE', value: 'single' }  // For future expansion
          ]
        }
      ]
    }
  }
}

// ===== OUTPUTS =====

output BACKEND_URL string = 'https://${backendContainerApp.properties.configuration.ingress.fqdn}'
output FRONTEND_URL string = 'https://${frontendContainerApp.properties.configuration.ingress.fqdn}'
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerAppEnv.id
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = '${containerRegistry}.azurecr.io'

// Event Grid output for scripts
output EVENTGRID_TOPIC_NAME string = existingEventGridTopicName

// Service discovery outputs (ready for future load balancing)
output backendName string = backendContainerApp.name
output frontendName string = frontendContainerApp.name

// Legacy outputs for compatibility
output backendUrl string = 'https://${backendContainerApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendContainerApp.properties.configuration.ingress.fqdn}'
output containerAppEnvironmentId string = containerAppEnv.id

// Future scaling outputs (commented for now)
// output backendSecondaryUrl string = 'https://${backendSecondaryContainerApp.properties.configuration.ingress.fqdn}'
// output backendSecondaryName string = backendSecondaryContainerApp.name
