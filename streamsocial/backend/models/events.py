"""
StreamSocial Event Models
Defines all event types and their structures for the streaming platform.

Event Taxonomy:
- User Actions: Posts, comments, follows, profile updates (1000 partitions)
- Content Interactions: Likes, shares, views, analytics (500 partitions)
- System Events: Notifications, alerts, system changes (100 partitions)
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """
    StreamSocial Event Types
    
    User Actions (1000 partitions, key: user_id):
    - High volume, strict ordering required per user
    - Examples: posts, comments, follows
    
    Content Interactions (500 partitions, key: content_id):
    - Ultra-high volume, relaxed ordering
    - Examples: likes, shares, views, analytics
    
    System Events (100 partitions, key: system_id):
    - Lower volume, system-level events
    - Examples: notifications, errors, alerts
    """
    
    # ========== USER ACTIONS (routed to user-actions topic) ==========
    USER_REGISTRATION = "user_registration"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_PROFILE_UPDATE = "user_profile_update"
    USER_FOLLOW = "user_follow"
    USER_UNFOLLOW = "user_unfollow"
    USER_POST_CREATE = "user_post_create"
    USER_POST_DELETE = "user_post_delete"
    USER_POST_EDIT = "user_post_edit"
    USER_COMMENT_CREATE = "user_comment_create"
    USER_COMMENT_DELETE = "user_comment_delete"
    
    # ========== CONTENT INTERACTIONS (routed to content-interactions topic) ==========
    CONTENT_LIKE = "content_like"
    CONTENT_UNLIKE = "content_unlike"
    CONTENT_COMMENT = "content_comment"
    CONTENT_SHARE = "content_share"
    CONTENT_VIEW = "content_view"
    CONTENT_BOOKMARK = "content_bookmark"
    CONTENT_ANALYTICS = "content_analytics"
    
    # ========== SYSTEM EVENTS (routed to system-events topic) ==========
    SYSTEM_NOTIFICATION = "system_notification"
    SYSTEM_ALERT = "system_alert"
    SYSTEM_ERROR = "system_error"
    SYSTEM_HEALTH_CHECK = "system_health_check"


class StreamSocialEvent(BaseModel):
    """
    Base event structure for all StreamSocial events.
    
    All events share this core structure regardless of topic.
    Topic routing is automatic based on event_type.
    """
    
    event_id: str = Field(
        description="Unique event identifier (UUID)",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    event_type: EventType = Field(
        description="Type of event (determines target topic)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the event occurred"
    )
    user_id: str = Field(
        description="User who triggered the event"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="User session identifier"
    )
    data: Dict[str, Any] = Field(
        description="Event-specific payload (structure varies by event_type)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "event_type": "user_post_create",
                "timestamp": "2024-07-28T10:30:00",
                "user_id": "user_123",
                "session_id": "session_456",
                "data": {
                    "post_id": "post_789",
                    "content": "Check out this amazing content!",
                    "media_count": 2
                }
            }
        }


class UserActionEvent(StreamSocialEvent):
    """Event for user-initiated actions (1000 partitions, key: user_id)"""
    pass


class ContentInteractionEvent(StreamSocialEvent):
    """Event for content interactions (500 partitions, key: content_id)"""
    
    content_id: Optional[str] = Field(
        default=None,
        description="ID of the content being interacted with"
    )


class SystemEvent(StreamSocialEvent):
    """Event for system-level events (100 partitions, key: system_id)"""
    
    system_id: str = Field(
        default="default",
        description="System component identifier"
    )    