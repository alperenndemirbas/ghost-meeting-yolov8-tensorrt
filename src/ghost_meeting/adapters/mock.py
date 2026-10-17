"""Fake adapters for development and tests: no network, fully controllable."""

from ghost_meeting.core.actions import NotifyOrganizer
from ghost_meeting.core.ports import Meeting


class MockNotifier:
    """Records notifications instead of sending them, so tests can inspect them."""

    def __init__(self) -> None:
        self.sent: list[NotifyOrganizer] = []

    def notify_organizer(self, action: NotifyOrganizer) -> None:
        self.sent.append(action)
        print(f"[MockNotifier] {action.organizer}: {action.meeting_id} odasına gelmedin mi? ({action.room_id})")


class MockCalendar:
    """In-memory calendar; meetings are added by hand."""

    def __init__(self) -> None:
        self._meetings: list[Meeting] = []

    def add_meeting(self, meeting: Meeting) -> None:
        self._meetings.append(meeting)

    def meetings_for(self, room_id: str) -> list[Meeting]:
        return [m for m in self._meetings if m.room_id == room_id]
