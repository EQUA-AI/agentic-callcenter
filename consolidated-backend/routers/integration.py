import os
from fastapi import APIRouter
from pydantic import BaseModel
from azure.communication.email import EmailClient
from azure.identity import DefaultAzureCredential

integration_router = APIRouter(prefix="/integration")

# To use Azure Active Directory Authentication (DefaultAzureCredential) make sure to have AZURE_CLIENT_ID as env variables.
endpoint = os.environ.get("ACS_ENDPOINT")
sender_address = os.environ.get("ACS_SENDER_ADDRESS")
email_client = EmailClient(endpoint, DefaultAzureCredential())

class EmailRequest(BaseModel):
    content: str
    recipient: str
    subject: str

@integration_router.post("/email")
def send_email(request: EmailRequest):
    try:
        # Send an email
        # See https://learn.microsoft.com/en-us/python/api/overview/azure/communication-email-readme?view=azure-python
        poller = email_client.begin_send(message={
            "content": {
                "subject": request.subject,
                "plainText": request.content
            },
            "recipients": {
                "to": [
                    {
                        "address": request.recipient,
                        "displayName": request.recipient
                    }
                ]
            },
            "senderAddress": sender_address
        })
        response = poller.result()
        return True, response
    except Exception as e:
        return False, str(e)
