import json
import uuid
from kafka import KafkaProducer
from typing import Dict, Any, List
from datetime import datetime
from models.events import StreamSocialEvent, EventType
from kafka.admin import KafkaAdminClient, NewTopic


class StreamSocialEventProducer:
    def __init__(self, bootstrap_servers: List[str] = ['localhost:9092','localhost:9093','localhost:9094']):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            acks='all',
            retries=10
        )  # Ensure all replicas acknowledge the message
        self.topic = 'streamsocial_events'

    def create_topic_if_not_exists(self):
        # Kafka topics are usually created automatically when a message is sent to them.
        # However, if you want to ensure the topic exists, you can use the Kafka AdminClient.
        admin_client = KafkaAdminClient(bootstrap_servers=self.producer.config['bootstrap_servers'])
        existing_topics = admin_client.list_topics()

        if self.topic not in existing_topics:
            topic = NewTopic(name=self.topic, num_partitions=3, replication_factor=3)
            admin_client.create_topics(new_topics=[topic], validate_only=False)
            print(f"Created topic: {self.topic}")
        else:
            print(f"Topic already exists: {self.topic}")    
        

    def publish_event(self, event_type: EventType, user_id: str, data: Dict[str,Any]):
        event = StreamSocialEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            data=data
        )
        
        # Manually serialize the event to JSON string first to handle datetime
        event_dict = event.model_dump(mode='json')
        event_json_str = json.dumps(event_dict)
        event_bytes = event_json_str.encode('utf-8')
        
        self.producer.send(self.topic, value=event_bytes)
        self.producer.flush()  # Ensure the message is sent    



        