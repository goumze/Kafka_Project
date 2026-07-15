from pydantic import BaseModel, Field
from typing import Dict,Any, Optional
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    #User Registration
    USER_REGISTRATION = "user_registration"
    USER_LOGIN = "user_login"
    USER_PROFILE_UPDATE = "user_profile_update"
    USER_FOLLOW = "user_follow"
    USER_POST_CREATE = "user_post_create"
    USER_POST_DELETE = "user_post_delete"

    #Content Interaction
    CONTENT_LIKE = "content_like"
    CONTENT_COMMENT = "content_comment"
    CONTENT_SHARE = "content_share"

    #System Events
    SYSTEM_NOTIFICATION = "system_notification"

class StreamSocialEvent(BaseModel):
    event_id: str = Field(description="Unique event identifier")
    event_type: EventType = Field(description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(description="User who triggered the event")
    session_id: Optional[str] = Field(description="User session identifier")
    data: Dict[str, Any] = Field(description="Event-specific payload")    