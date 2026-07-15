import json
import uuid
from kafka import KafkaProducer
from typing import Dict, Any, List
from datetime import datetime
from models.events import StreamSocialEvent, EventType

class StreamSocialEventProducer:
    def __init__(self, bootstrap_servers: List[str] = ['localhost:9091','localhost:9092','localhost:9093']):
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                      value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                                      key_serializer=lambda k: k.encode('utf-8') if k else None)
        self.topic = 'streamsocial_events'

    def publish_event(self, event_type: EventType, user_id: str, data: Dict[str,Any]):
        event = StreamSocialEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=str(uuid.uuid4()),  # Assuming a new session for each event; adjust as needed
            user_id=user_id,
            data=data
        )
        self.producer.send(self.topic, key=event.user_id, value=event.model_dump())
        self.producer.flush()  # Ensure the message is sent    



        