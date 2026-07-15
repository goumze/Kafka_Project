import json
from kafka import KafkaConsumer
from typing import Dict, Any, List, Callable
from datetime import datetime

class StreamSocialEventConsumer:
    def __init__(self, bootstrap_servers: List[str] = ['localhost:9091','localhost:9092','localhost:9093'], group_id: str = 'streamsocial_event_consumers'):
        self.consumer = KafkaConsumer(
            'streamsocial_events',
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='earliest'
        )
        self.event_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.processed_events = []

    def start_consuming(self):
        for message in self.consumer:
            event_data = message.value
            event_type = event_data.get('event_type')
            
            # Store for dashboard
            self.processed_events.append({
                **event_data,
                'processed_at': datetime.now().isoformat()
            }) 

            # Process with handler
            if event_type in self.event_handlers:
                self.event_handlers[event_type](event_data) 

    