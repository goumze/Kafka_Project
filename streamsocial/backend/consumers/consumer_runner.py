import json
import logging
from kafka import KafkaConsumer
from typing import Dict, Any, List, Callable
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StreamSocialEventConsumer:
    def __init__(self, 
                 bootstrap_servers: List[str] = None, 
                 group_id: str = 'streamsocial_event_consumers',
                 auto_offset_reset: str = 'earliest'):
        """
        Initialize the Kafka consumer for StreamSocial events
        
        Args:
            bootstrap_servers: List of Kafka broker addresses
            group_id: Consumer group identifier
            auto_offset_reset: Where to start reading from ('earliest' or 'latest')
        """
        if bootstrap_servers is None:
            bootstrap_servers = ['localhost:9092', 'localhost:9093', 'localhost:9094']
        
        self.consumer = KafkaConsumer(
            'streamsocial_events',
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            session_timeout_ms=30000
        )
        
        self.event_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.processed_events = []
        self.total_events_processed = 0
        logger.info(f"Consumer initialized with group: {group_id}")

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler function for a specific event type
        
        Args:
            event_type: The event type to handle
            handler: Callable that processes the event
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Handler registered for event type: {event_type}")

    def handle_user_registration(self, event_data: Dict[str, Any]):
        """Handle user registration events"""
        logger.info(f"Processing user registration: {event_data.get('data', {}).get('username')}")
        # Add custom logic here

    def handle_content_like(self, event_data: Dict[str, Any]):
        """Handle content like events"""
        logger.info(f"Processing content like from user: {event_data.get('user_id')}")
        # Add custom logic here

    def handle_content_comment(self, event_data: Dict[str, Any]):
        """Handle content comment events"""
        logger.info(f"Processing content comment from user: {event_data.get('user_id')}")
        # Add custom logic here

    def start_consuming(self):
        """Start consuming events from Kafka"""
        logger.info("Starting event consumer...")
        
        # Register default handlers
        self.register_handler('user_registration', self.handle_user_registration)
        self.register_handler('content_like', self.handle_content_like)
        self.register_handler('content_comment', self.handle_content_comment)
        
        try:
            for message in self.consumer:
                try:
                    # Manually deserialize bytes to JSON
                    event_data = json.loads(message.value.decode('utf-8')) if message.value else {}
                    event_type = event_data.get('event_type')
                    event_id = event_data.get('event_id')
                    
                    logger.info(f"Received event: {event_id} of type: {event_type}")
                    
                    # Store for dashboard/monitoring
                    self.processed_events.append({
                        **event_data,
                        'processed_at': datetime.now().isoformat()
                    })
                    
                    # Keep only last 1000 events in memory
                    if len(self.processed_events) > 1000:
                        self.processed_events.pop(0)
                    
                    self.total_events_processed += 1
                    
                    # Process with handler if registered
                    if event_type in self.event_handlers:
                        handler = self.event_handlers[event_type]
                        handler(event_data)
                        logger.info(f"Event {event_id} processed by handler")
                    else:
                        logger.debug(f"No handler registered for event type: {event_type}")
                        
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}", exc_info=True)
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            self.consumer.close()
            logger.info(f"Consumer closed. Total events processed: {self.total_events_processed}")

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            'total_events_processed': self.total_events_processed,
            'events_in_memory': len(self.processed_events),
            'recent_events': self.processed_events[-10:] if self.processed_events else []
        }


if __name__ == "__main__":
    consumer = StreamSocialEventConsumer()
    consumer.start_consuming()
