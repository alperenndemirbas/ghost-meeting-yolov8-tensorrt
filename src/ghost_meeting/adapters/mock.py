"""Fake adapters for development and tests: no network, fully controllable."""

from ghost_meeting.core.actions import AskToReserve, NotifyOrganizer
from ghost_meeting.core.ports import Meeting


class MockNotifier:
    """Records notifications instead of sending them, so tests can inspect them."""

    def __init__(self) -> None:
        self.sent: list[NotifyOrganizer] = []

    def notify_organizer(self, action: NotifyOrganizer) -> None:
        self.sent.append(action)
        print(f"[MockNotifier] {action.organizer}: {action.meeting_id} odasına gelmedin mi? ({action.room_id})")


class MockPrompter:
    """Records spoken questions instead of playing them through a speaker."""

    def __init__(self) -> None:
        self.asked: list[AskToReserve] = []

    def ask_to_reserve(self, action: AskToReserve) -> None:
        self.asked.append(action)
        print(f"[MockPrompter] ({action.room_id}) Odayı sizin için ayıralım mı?")


class MockCalendar:
    """In-memory calendar; meetings are added by hand."""

    def __init__(self) -> None:
        self._meetings: list[Meeting] = []

    def add_meeting(self, meeting: Meeting) -> None:
        self._meetings.append(meeting)

    def meetings_for(self, room_id: str) -> list[Meeting]:
        return [m for m in self._meetings if m.room_id == room_id]
