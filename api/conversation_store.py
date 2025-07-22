from azure.cosmos import CosmosClient, PartitionKey, exceptions

class ConversationStore:
    def __init__(self, url, key, database_name, container_name):
        self.client = CosmosClient(url, credential=key)
        self.database_name = database_name
        self.container_name = container_name
        self.db = None
        self.container = None
        self.initialize_database()
        self.initialize_container()

    def initialize_database(self):
        try:
            self.db = self.client.create_database_if_not_exists(id=self.database_name)
        except exceptions.CosmosResourceExistsError:
            self.db = self.client.get_database_client(database=self.database_name)

    def initialize_container(self):
        try:
            self.container = self.db.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/conversation_id"),
                offer_throughput=400
            )
        except exceptions.CosmosResourceExistsError:
            self.container = self.db.get_container_client(container=self.container_name)
            
    # Save all in the conversation
    def save_conversation(self, conversation_id: str, conversation: dict):
        self.container.upsert_item({
                "id": conversation_id,
                "conversation_id": conversation_id,
                "messages": conversation.get("messages", []),
                "variables": conversation.get("variables", {}),
            })
        
    def get_conversation(self, conversation_id):
        try:
            item = self.container.read_item(item=conversation_id, partition_key=conversation_id)
            return item
        except exceptions.CosmosResourceNotFoundError:
            return None