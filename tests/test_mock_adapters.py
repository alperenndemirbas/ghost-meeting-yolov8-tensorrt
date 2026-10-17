from datetime import datetime, timedelta

from ghost_meeting.adapters.mock import MockCalendar, MockNotifier
from ghost_meeting.core.actions import NotifyOrganizer
from ghost_meeting.core.ports import CalendarProvider, Meeting, Notifier

T0 = datetime(2026, 1, 1, 10, 0, 0)


def make_meeting(meeting_id: str, room_id: str) -> Meeting:
    return Meeting(meeting_id, room_id, "ahmet", T0, T0 + timedelta(hours=1))


def test_mock_notifier_records_actions():
    notifier = MockNotifier()
    action = NotifyOrganizer("room1", "m1", "ahmet")
    notifier.notify_organizer(action)
    assert notifier.sent == [action]


def test_mock_calendar_returns_only_requested_room():
    calendar = MockCalendar()
    calendar.add_meeting(make_meeting("m1", "room1"))
    calendar.add_meeting(make_meeting("m2", "room2"))
    assert [m.meeting_id for m in calendar.meetings_for("room1")] == ["m1"]


def test_mocks_fit_the_ports():
    # Type-checker level check: assigning proves the mocks satisfy the contracts.
    notifier: Notifier = MockNotifier()
    calendar: CalendarProvider = MockCalendar()
    assert notifier is not None and calendar is not None
