import os
from azure.identity import AzureDeveloperCliCredential
from azure.core.exceptions import HttpResponseError
from azure.mgmt.eventgrid import EventGridManagementClient

# Load environment variables from azd environment
from utils import load_azd_env

load_azd_env()

# Environment variables
resource_group = os.getenv("AZURE_RESOURCE_GROUP")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
tenant_id = os.getenv("AZURE_TENANT_ID")

# ACS and Event Grid configuration
existing_acs_resource_group = "WeddingBotUS"
existing_eventgrid_topic_name = "AIWedding"

# Service Bus configuration (from the new resource group)
sb_namespace_fqdn = os.getenv("ServiceBusConnection__fullyQualifiedNamespace", "").replace("https://", "").replace("/", "")
if not sb_namespace_fqdn:
    print("❌ ServiceBusConnection__fullyQualifiedNamespace not found in environment")
    exit(1)

sb_namespace_name = sb_namespace_fqdn.split('.')[0]

credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
client = EventGridManagementClient(credential, subscription_id)

# Service Bus queue resource IDs
sms_queue_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ServiceBus/namespaces/{sb_namespace_name}/queues/sms"
messages_queue_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ServiceBus/namespaces/{sb_namespace_name}/queues/messages"
calls_queue_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ServiceBus/namespaces/{sb_namespace_name}/queues/calls"

def create_event_subscription(subscription_name, queue_resource_id, event_types, description):
    try:
        print(f"Creating Event Grid subscription: {subscription_name} -> {description}")
        
        event_subscription = client.system_topic_event_subscriptions.begin_create_or_update(
            existing_acs_resource_group,  # Event Grid topic is in WeddingBotUS
            existing_eventgrid_topic_name,  # AIWedding topic
            subscription_name,
            {
                "destination": {
                    "endpointType": "ServiceBusQueue",
                    "properties": {
                        "resourceId": queue_resource_id
                    }
                },
                "filter": {
                    "included_event_types": event_types
                },
                "eventDeliverySchema": "EventGridSchema"
            }
        ).result()
        
        print(f"✅ Successfully created subscription: {subscription_name}")
        return True
        
    except HttpResponseError as e:
        if "already exists" in str(e).lower():
            print(f"⚠️  Subscription {subscription_name} already exists")
            return True
        else:
            print(f"❌ Error creating subscription {subscription_name}: {e}")
            print(f"Error details: {e.response.text if hasattr(e, 'response') else 'No additional details'}")
            return False

# Create SMS events subscription
sms_success = create_event_subscription(
    "telco-sms-subscription",
    sms_queue_resource_id,
    ["Microsoft.Communication.SMSReceived"],
    "SMS events to sms queue"
)

# Create advanced messaging events subscription  
messaging_success = create_event_subscription(
    "telco-messaging-subscription",
    messages_queue_resource_id,
    [
        "Microsoft.Communication.AdvancedMessageReceived",
        "Microsoft.Communication.AdvancedMessageDeliveryStatusUpdated",
        "Microsoft.Communication.AdvancedMessageChannelRegistrationStatusUpdated",
        "Microsoft.Communication.ChatMessageReceived",
        "Microsoft.Communication.ChatMessageEdited",
        "Microsoft.Communication.ChatMessageDeleted",
        "Microsoft.Communication.ChatThreadCreated",
        "Microsoft.Communication.ChatThreadDeleted",
        "Microsoft.Communication.ChatThreadPropertiesUpdated",
        "Microsoft.Communication.ChatParticipantAddedToThread",
        "Microsoft.Communication.ChatParticipantRemovedFromThread"
    ],
    "Advanced messaging and chat events to messages queue"
)

# Create voice/call events subscription
calls_success = create_event_subscription(
    "telco-calls-subscription", 
    calls_queue_resource_id,
    [
        "Microsoft.Communication.IncomingCall",
        "Microsoft.Communication.CallEnded",
        "Microsoft.Communication.CallConnectionStateChanged",
        "Microsoft.Communication.CallTransferAccepted",
        "Microsoft.Communication.CallTransferFailed",
        "Microsoft.Communication.ParticipantsUpdated",
        "Microsoft.Communication.RecordingFileStatusUpdated",
        "Microsoft.Communication.PlayCompleted",
        "Microsoft.Communication.PlayFailed",
        "Microsoft.Communication.RecognizeCompleted",
        "Microsoft.Communication.RecognizeFailed"
    ],
    "Voice and call events to calls queue"
)

if sms_success and messaging_success and calls_success:
    print("\n🎉 All Event Grid subscriptions configured successfully!")
    print(f"📋 Event Grid Topic: {existing_eventgrid_topic_name} (in {existing_acs_resource_group})")
    print(f"📨 SMS events -> {resource_group}/sms queue")
    print(f"💬 Messaging events -> {resource_group}/messages queue") 
    print(f"📞 Call events -> {resource_group}/calls queue")
else:
    print("\n❌ Some Event Grid subscriptions failed to create")
    exit(1)
