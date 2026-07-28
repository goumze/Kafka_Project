#!/usr/bin/env python3
"""
Test script to demonstrate producer-consumer integration for StreamSocial events
This script:
1. Sends sample events using the producer
2. Displays the events being consumed
"""

import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from producers.event_producer import StreamSocialEventProducer
from models.events import EventType


def send_sample_events():
    """Send sample events to Kafka"""
    print("=" * 60)
    print("StreamSocial Event Producer Test")
    print("=" * 60)
    
    producer = StreamSocialEventProducer()
    
    sample_events = [
        {
            "event_type": EventType.USER_REGISTRATION,
            "user_id": str(uuid.uuid4()),
            "data": {
                "username": "alice",
                "email": "alice@example.com",
                "registration_source": "web"
            }
        },
        {
            "event_type": EventType.USER_REGISTRATION,
            "user_id": str(uuid.uuid4()),
            "data": {
                "username": "bob",
                "email": "bob@example.com",
                "registration_source": "mobile"
            }
        },
        {
            "event_type": EventType.CONTENT_LIKE,
            "user_id": str(uuid.uuid4()),
            "data": {
                "content_id": "post_123",
                "content_type": "post",
                "liked": True
            }
        },
        {
            "event_type": EventType.CONTENT_COMMENT,
            "user_id": str(uuid.uuid4()),
            "data": {
                "content_id": "post_456",
                "comment": "Great post! Really enjoyed this content.",
                "comment_id": str(uuid.uuid4())
            }
        },
        {
            "event_type": EventType.USER_FOLLOW,
            "user_id": str(uuid.uuid4()),
            "data": {
                "followed_user_id": str(uuid.uuid4()),
                "followed_at": datetime.now().isoformat()
            }
        }
    ]
    
    print(f"\nSending {len(sample_events)} sample events to Kafka...\n")
    
    for i, event_template in enumerate(sample_events, 1):
        try:
            print(f"Event {i}:")
            print(f"  Type: {event_template['event_type']}")
            print(f"  User ID: {event_template['user_id']}")
            print(f"  Data: {json.dumps(event_template['data'], indent=2)}")
            
            producer.publish_event(
                event_type=event_template['event_type'],
                user_id=event_template['user_id'],
                data=event_template['data']
            )
            
            print(f"  ✓ Sent successfully\n")
            time.sleep(0.5)  # Small delay between sends
            
        except Exception as e:
            print(f"  ✗ Error sending event: {str(e)}\n")
    
    print("=" * 60)
    print(f"Successfully sent {len(sample_events)} events!")
    print("=" * 60)
    print("\nNow run the consumer to see these events being processed:")
    print("  python consumers/consumer_runner.py")
    print("\nOr in a separate terminal:")
    print("  docker exec kafka-broker-1 kafka-console-consumer --bootstrap-server kafka-1:29092 --topic streamsocial_events --from-beginning")


if __name__ == "__main__":
    send_sample_events()
