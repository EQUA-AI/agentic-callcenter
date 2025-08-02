// Event Grid System Topic module
// This must be deployed to the same resource group as the ACS resource

param topicName string
param acsResourceId string
param userAssignedIdentityResourceId string
param uniqueId string
param prefix string

// Service Bus parameters for event subscriptions
param sbNamespaceFQDN string
param smsQueueId string
param advMsgQueueId string
param callQueueId string

resource acsEGTopic 'Microsoft.EventGrid/systemTopics@2023-12-15-preview' = {
  name: topicName
  location: 'global'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    source: acsResourceId
    topicType: 'Microsoft.Communication.CommunicationServices'
  }
}

// SMS Event Grid subscription
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
          resourceId: smsQueueId
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

// Advanced Messaging Event Grid subscription  
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
          resourceId: advMsgQueueId
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

// Voice/Call Event Grid subscription
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
          resourceId: callQueueId
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

output topicName string = acsEGTopic.name
output topicId string = acsEGTopic.id
