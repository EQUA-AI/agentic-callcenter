targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

// Generate resource token for unique naming
var resourceToken = uniqueString(subscription().id, location, environmentName)

// Main deployment parameters
param prefix string = 'dev-consolidated'
@minLength(1)
@description('Primary location for all resources')
param location string

@description('Name of the resource group')
param resourceGroupName string = 'rg-${environmentName}'

// New Foundry parameters
param foundryEndpoint string = 'https://weddingomni.services.ai.azure.com/api/projects/WeddingOmni'
param agentId string = 'asst_khFWOGAwaF7BJ73ecupCfXze'
param useFoundryAgent string = 'true'

// WhatsApp ACS parameters - only need the channel registration ID
param acsChannelRegistrationId string = '5b42b7cd-1bfe-4f94-acc9-7f46b19cb5ec'

// Existing Event Grid topic name
param existingEventGridTopicName string = 'dev-acs-topic-2wfnxagc7mn5g'

// Dynamic parameters that will be passed from the workflow
param applicationInsightsConnectionString string = 'placeholder'
param userAssignedIdentityClientId string = 'placeholder'
param speechServiceKey string = 'placeholder'
param backendContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param frontendContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// Create or reference the resource group with proper tags
resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: resourceGroupName
  location: location
  tags: {
    'azd-env-name': environmentName
  }
}

// Deploy consolidated container apps using existing infrastructure
module acaConsolidated './aca-consolidated.bicep' = {
  name: 'aca-consolidated'
  scope: rg
  params: {
    uniqueId: resourceToken  // Use generated resource token for unique naming
    prefix: prefix
    userAssignedIdentityResourceId: '/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroupName}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/devuami2wfnxagc7mn5g'
    userAssignedIdentityClientId: userAssignedIdentityClientId
    openAiEndpoint: 'https://openai-wedding.openai.azure.com/'
    cosmosDbEndpoint: 'https://devcosmos2wfnxagc7mn5g.documents.azure.com:443/'
    cosmosDbDatabase: 'conversations'
    cosmosDbContainer: 'chat_sessions'
    applicationInsightsConnectionString: applicationInsightsConnectionString
    containerRegistry: 'devacr2wfnxagc7mn5g'
    logAnalyticsWorkspaceName: 'dev-law-2wfnxagc7mn5g'
    acsEndpoint: 'https://dev-acs-2wfnxagc7mn5g.communication.azure.com'
    serviceBusNamespaceFqdn: 'dev-sb-2wfnxagc7mn5g.servicebus.windows.net'
    speechServiceKey: speechServiceKey
    cognitiveServiceEndpoint: 'https://dev-cogsvc-2wfnxagc7mn5g.cognitiveservices.azure.com/'
    backendContainerImage: backendContainerImage
    frontendContainerImage: frontendContainerImage
    foundryEndpoint: foundryEndpoint
    agentId: agentId
    useFoundryAgent: useFoundryAgent
    acsChannelRegistrationId: acsChannelRegistrationId
    existingEventGridTopicName: existingEventGridTopicName
  }
}

// Outputs
output AZURE_RESOURCE_GROUP string = rg.name
output RESOURCE_GROUP_ID string = rg.id
output AZURE_LOCATION string = location
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = 'devacr2wfnxagc7mn5g.azurecr.io'
output BACKEND_URL string = acaConsolidated.outputs.backendUrl
output FRONTEND_URL string = acaConsolidated.outputs.frontendUrl
output RESOURCE_GROUP_NAME string = rg.name
