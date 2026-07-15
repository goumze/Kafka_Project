import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

app = FastAPI(title="StreamSocial Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mock storage for events
events_storage = []

class UserRegistration(BaseModel):
    username: str
    email: str
    source: str = "web"

# Mock event for testing
def generate_mock_events():
    """Generate some mock events for demonstration"""
    mock_events = [
        {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "user_registration",
            "event_data": {"username": "alice", "email": "alice@example.com"},
            "timestamp": datetime.now().isoformat()
        },
        {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "content_like",
            "event_data": {"content_id": "post_123", "liked": True},
            "timestamp": datetime.now().isoformat()
        },
        {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "content_comment",
            "event_data": {"content_id": "post_456", "comment": "Great post!"},
            "timestamp": datetime.now().isoformat()
        },
    ]
    return mock_events

# Initialize with mock events
events_storage = generate_mock_events()

@app.post("/events/user/register")
async def register_user(registration: UserRegistration):
    user_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    
    event = {
        "event_id": event_id,
        "user_id": user_id,
        "event_type": "user_registration",
        "event_data": {"username": registration.username, "email": registration.email},
        "timestamp": datetime.now().isoformat()
    }
    
    events_storage.append(event)
    if len(events_storage) > 100:
        events_storage.pop(0)  # Keep only last 100 events
    
    return {"success": True, "user_id": user_id, "event_id": event_id}

@app.get("/events/recent")
async def get_recent_events():
    return {"success": True, "events": events_storage[-20:], "count": len(events_storage)}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "StreamSocial Backend", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {
        "service": "StreamSocial Event-Driven Backend",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "register_user": "POST /events/user/register",
            "get_events": "GET /events/recent"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



