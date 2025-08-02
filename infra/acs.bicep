param uniqueId string
param prefix string
param userAssignedIdentityPrincipalId string
param userAssignedIdentityResourceId string
param communicationServiceDataLocation string = 'United States'
param location string = resourceGroup().location

// Parameters for existing ACS resource
param existingAcsName string = 'WeddingUS'
param existingAcsResourceGroup string = 'WeddingBotUS'
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

// An EventGrid topic to receive events from the communication service
resource acsEGTopic 'Microsoft.EventGrid/systemTopics@2023-12-15-preview' = {
  name: '${prefix}-acs-topic-${uniqueId}'
  location: 'global'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    source: useExistingAcs ? '/subscriptions/${subscription().subscriptionId}/resourceGroups/${existingAcsResourceGroup}/providers/Microsoft.Communication/CommunicationServices/${existingAcsName}' : newAcs.id
    topicType: 'Microsoft.Communication.CommunicationServices'
  }
}

// An EventGrid subscription to forward events to the service bus queue
resource smsEGSub 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2023-12-15-preview' = {
  name: '${prefix}-sms-sub-${uniqueId}'
  parent: acsEGTopic
  properties: {
    deliveryWithResourceIdentity: {
      identity: {
        type: 'UserAssigned'
        userAssignedIdentity: userAssignedIdentityResourceId
      }
      destination: {
        endpointType: 'ServiceBusQueue'
        properties: {
          resourceId: smsQueue.id
        }
      }
    }
    eventDeliverySchema: 'EventGridSchema'
    filter: {
      includedEventTypes: [
        'Microsoft.Communication.SMSReceived'
      ]
    }
  }
}
// An EventGrid subscription to forward advanced messaging events to the service bus queue
resource msgEGSub 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2023-12-15-preview' = {
  name: '${prefix}-msg-sub-${uniqueId}'
  parent: acsEGTopic
  properties: {
    deliveryWithResourceIdentity: {
      identity: {
        type: 'UserAssigned'
        userAssignedIdentity: userAssignedIdentityResourceId
      }
      destination: {
        endpointType: 'ServiceBusQueue'
        properties: {
          resourceId: advMsgQueue.id
        }
      }
    }
    eventDeliverySchema: 'EventGridSchema'
    filter: {
      includedEventTypes: [
        'Microsoft.Communication.AdvancedMessageReceived'
        'Microsoft.Communication.AdvancedMessageDeliveryStatusUpdated'
        'Microsoft.Communication.AdvancedMessageChannelRegistrationStatusUpdated'
        // Additional WhatsApp advanced messaging events
        'Microsoft.Communication.ChatMessageReceived'
        'Microsoft.Communication.ChatMessageEdited'
        'Microsoft.Communication.ChatMessageDeleted'
        'Microsoft.Communication.ChatThreadCreated'
        'Microsoft.Communication.ChatThreadDeleted'
        'Microsoft.Communication.ChatThreadPropertiesUpdated'
        'Microsoft.Communication.ChatParticipantAddedToThread'
        'Microsoft.Communication.ChatParticipantRemovedFromThread'
      ]
    }
  }
}

// An EventGrid subscription for voice/call events to the service bus queue
resource callEGSub 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2023-12-15-preview' = {
  name: '${prefix}-call-sub-${uniqueId}'
  parent: acsEGTopic
  properties: {
    deliveryWithResourceIdentity: {
      identity: {
        type: 'UserAssigned'
        userAssignedIdentity: userAssignedIdentityResourceId
      }
      destination: {
        endpointType: 'ServiceBusQueue'
        properties: {
          resourceId: callQueue.id
        }
      }
    }
    eventDeliverySchema: 'EventGridSchema'
    filter: {
      includedEventTypes: [
        'Microsoft.Communication.IncomingCall'
        'Microsoft.Communication.CallEnded'
        'Microsoft.Communication.CallConnectionStateChanged'
        'Microsoft.Communication.CallTransferAccepted'
        'Microsoft.Communication.CallTransferFailed'
        'Microsoft.Communication.ParticipantsUpdated'
        'Microsoft.Communication.RecordingFileStatusUpdated'
        'Microsoft.Communication.PlayCompleted'
        'Microsoft.Communication.PlayFailed'
        'Microsoft.Communication.RecognizeCompleted'
        'Microsoft.Communication.RecognizeFailed'
      ]
    }
  }
}

output acsName string = useExistingAcs ? existingAcsName : newAcs.name
output acsEndpoint string = 'weddingus.unitedstates.communication.azure.com'
output acsTopicName string = acsEGTopic.name
output acsTopicId string = acsEGTopic.id
// output acsEmailDomainName string = acsEmailDomain.name
// output acsEmailSender string = 'donotreply@${acsEmailDomain.properties.mailFromSenderDomain}'
output sbNamespace string = serviceBusNamespace.name
output sbNamespaceFQDN string = serviceBusNamespace.properties.serviceBusEndpoint
output smsQueueName string = smsQueue.name
output advMsgQueueName string = advMsgQueue.name
output callQueueName string = callQueue.name
output acsIdentityId string = 'existing-acs-identity'
