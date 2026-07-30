"""Backward-compatible event model test."""

from models.events import EventType, StreamSocialEvent


def test_event_creation():
    event = StreamSocialEvent(
        event_id="test-123",
        event_type=EventType.USER_REGISTRATION,
        user_id="user-456",
        data={"username": "testuser"},
    )
    assert event.event_id == "test-123"
    assert event.event_type == EventType.USER_REGISTRATION
    assert event.user_id == "user-456"
    assert event.data == {"username": "testuser"}
