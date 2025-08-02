import os
from azure.identity import AzureDeveloperCliCredential
from azure.core.exceptions import HttpResponseError
from azure.mgmt.eventgrid import EventGridManagementClient

# Load environment variables from azd environment
from utils import load_azd_env

load_azd_env()

resource_group = os.getenv("AZURE_RESOURCE_GROUP")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
topic_name = os.getenv("ACS_TOPIC_NAME")
webhook_url = os.getenv("VOICE_WEBHOOK_URL")
subscription_name = os.getenv("VOICE_SUBSCRIPTION_NAME")

credential = AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID"), process_timeout=60)
client = EventGridManagementClient(credential, subscription_id)

try:
    print(f"Creating Event Subscription for {topic_name} under {resource_group} to {webhook_url}")
    event_subscription = client.system_topic_event_subscriptions.begin_create_or_update(
        resource_group,
        topic_name,
        subscription_name,
        {
            "destination": {
                "endpointType": "WebHook",
                "properties": {
                    "endpointUrl": webhook_url
                }
            },
            "filter": {
                "included_event_types": [
                    "Microsoft.Communication.IncomingCall",
                    "Microsoft.Communication.CallEnded",
                    "Microsoft.Communication.CallConnectionStateChanged",
                    "Microsoft.Communication.ParticipantsUpdated"
                ]
            }
        }
    ).result()
    print(f"✅ Successfully created voice webhook subscription: {subscription_name}")
except HttpResponseError as e:
    print(f"❌ Error creating voice webhook subscription: {e}")
    print(f"Error details: {e.response.text if hasattr(e, 'response') else 'No additional details'}")
