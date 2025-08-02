param uniqueId string
param prefix string
param userAssignedIdentityPrincipalId string
param userAssignedIdentityResourceId string
param communicationServiceDataLocation string = 'United States'
param location string = resourceGroup().location

// Parameters for existing ACS resource
param existingAcsName string = 'WeddingUS'
param existingAcsResourceGroup string = 'WeddingBotUS'
param existingEventGridTopicName string = 'AIWedding'
param existingAcsPrincipalId string = ''
param useExistingAcs bool = true

// Create new ACS resource only if not using existing
resource newAcs 'Microsoft.Communication/CommunicationServices@2023-04-01-preview' = if (!useExistingAcs) {
  name: '${prefix}-acs-${uniqueId}'
  location: 'global'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    dataLocation: communicationServiceDataLocation
    linkedDomains: []
  }
}

resource emailService 'Microsoft.Communication/emailServices@2023-04-01-preview' = if (!useExistingAcs) {
  name: '${prefix}-email-${uniqueId}'
  location: 'global'
  properties: {
    dataLocation: communicationServiceDataLocation
  }
}

resource acsRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAcs) {
  name: guid(newAcs.id, userAssignedIdentityPrincipalId, 'contributor')
  scope: newAcs
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // Role definition ID for Contributor
    principalId: userAssignedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// A service bus queue to store events
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: '${prefix}-sb-${uniqueId}'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
}

// SB Data Owner role assignment for the service bus namespace
resource sbRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(serviceBusNamespace.id, userAssignedIdentityPrincipalId, 'dataowner')
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '090c5cfd-751d-490a-894a-3ce6f1109419')
    principalId: userAssignedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource smsQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  name: 'sms'
  parent: serviceBusNamespace
  properties: {}
}
resource advMsgQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  name: 'messages'
  parent: serviceBusNamespace
  properties: {}
}
resource callQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  name: 'calls'
  parent: serviceBusNamespace
  properties: {}
}

// For new ACS resources, create Event Grid system topic in the same resource group
resource newAcsEGTopic 'Microsoft.EventGrid/systemTopics@2023-12-15-preview' = if (!useExistingAcs) {
  name: '${prefix}-acs-topic-${uniqueId}'
  location: 'global'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    source: newAcs.id
    topicType: 'Microsoft.Communication.CommunicationServices'
  }
}

// Note: Event Grid subscriptions to Service Bus queues across resource groups 
// require special handling. For now, we'll skip creating subscriptions here
// and handle them in a post-deployment script or separately.

// The existing Event Grid topic in WeddingBotUS will need subscriptions created
// manually or via separate deployment to forward events to our Service Bus queues.

output acsName string = useExistingAcs ? existingAcsName : newAcs.name
output acsEndpoint string = 'weddingus.unitedstates.communication.azure.com'
output acsTopicName string = useExistingAcs ? existingEventGridTopicName : newAcsEGTopic.name
output acsTopicId string = useExistingAcs ? resourceId(existingAcsResourceGroup, 'Microsoft.EventGrid/systemTopics', existingEventGridTopicName) : newAcsEGTopic.id
// output acsEmailDomainName string = acsEmailDomain.name
// output acsEmailSender string = 'donotreply@${acsEmailDomain.properties.mailFromSenderDomain}'
output sbNamespace string = serviceBusNamespace.name
output sbNamespaceFQDN string = serviceBusNamespace.properties.serviceBusEndpoint
output smsQueueName string = smsQueue.name
output advMsgQueueName string = advMsgQueue.name
output callQueueName string = callQueue.name
output acsIdentityId string = existingAcsPrincipalId
