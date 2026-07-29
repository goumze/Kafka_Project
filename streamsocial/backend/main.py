import threading
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import consumer and producer
from consumers.event_consumer import StreamSocialEventConsumer
from producers.event_producer import StreamSocialEventProducer

# Import controllers
from controllers import event_router, consumer_router, cluster_router, health_router
from controllers import event_controller, consumer_controller

app = FastAPI(title="StreamSocial Backend API", version="1.0.0")

# Initialize producer
producer = StreamSocialEventProducer()

# Inject dependencies into controllers
event_controller.set_producer(producer)
event_controller.set_consumer(None)  # Will be set during startup

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routers
app.include_router(health_router)
app.include_router(event_router)
app.include_router(consumer_router)
app.include_router(cluster_router)

# Global consumer instance(s) - support horizontal scaling
consumer: Optional[StreamSocialEventConsumer] = None
consumer_thread: Optional[threading.Thread] = None
consumer_running = False


def run_consumer_in_background():
    """Run the consumer in a background thread"""
    global consumer, consumer_running
    try:
        if consumer is None:
            consumer = StreamSocialEventConsumer(instance_id="primary")
        consumer_running = True
        
        # Register default event handlers (optional)
        def handle_user_registration(event_data):
            """Default handler for user registration events"""
            print(f"[HANDLER] User registered: {event_data.get('data', {}).get('username')}")
        
        def handle_content_like(event_data):
            """Default handler for content like events"""
            print(f"[HANDLER] Content liked by user: {event_data.get('user_id')}")
        
        consumer.register_handler('user_registration', handle_user_registration)
        consumer.register_handler('content_like', handle_content_like)
        
        consumer.start_consuming()
        event_controller.set_consumer(consumer)
        consumer_controller.set_consumer_state(consumer, consumer_thread, consumer_running, instance_id="primary")
        print("[CONSUMER] Kafka consumer started in background thread.")
    except Exception as e:
        print(f"[ERROR] Error in consumer thread: {str(e)}")
        consumer_running = False


@app.on_event("startup")
async def startup_event():
    """Start the Kafka consumer when the application starts"""
    global consumer_thread
    print("[STARTUP] Starting Kafka consumer in background...")
    consumer_thread = threading.Thread(target=run_consumer_in_background, daemon=True)
    consumer_thread.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global consumer, consumer_running
    consumer_running = False
    if consumer:
        consumer.close()
    print("[SHUTDOWN] Kafka consumer stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



