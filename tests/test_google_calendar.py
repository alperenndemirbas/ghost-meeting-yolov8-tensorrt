from datetime import datetime, timedelta, timezone

from ghost_meeting.adapters.google_calendar import GoogleCalendar
from ghost_meeting.core.ports import CalendarProvider, Meeting

TZ = timezone(timedelta(hours=3))


class FakeRequest:
    """Google's client builds a request first and sends it on .execute()."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def execute(self) -> dict:
        return self._payload


class FakeEvents:
    def __init__(self, items: list[dict]) -> None:
        self.items = items
        self.list_calls: list[dict] = []
        self.deleted: list[dict] = []
        self.patched: list[dict] = []

    def list(self, **kwargs) -> FakeRequest:
        self.list_calls.append(kwargs)
        return FakeRequest({"items": self.items})

    def get(self, calendarId: str, eventId: str) -> FakeRequest:
        return FakeRequest(next(e for e in self.items if e["id"] == eventId))

    def patch(self, **kwargs) -> FakeRequest:
        self.patched.append(kwargs)
        return FakeRequest({})

    def delete(self, **kwargs) -> FakeRequest:
        self.deleted.append(kwargs)
        return FakeRequest({})


class FakeService:
    def __init__(self, items: list[dict]) -> None:
        self._events = FakeEvents(items)

    def events(self) -> FakeEvents:
        return self._events


def timed_event(event_id: str = "abc") -> dict:
    """A meeting Ahmet organized; the room (oda1) is just an invited guest."""
    return {
        "id": event_id,
        "summary": "Sprint",
        "organizer": {"email": "ahmet@example.com"},
        "attendees": [
            {"email": "ahmet@example.com", "responseStatus": "accepted"},
            {"email": "oda1@gmail.com", "self": True, "responseStatus": "accepted"},
        ],
        "start": {"dateTime": "2026-01-01T10:00:00+03:00"},
        "end": {"dateTime": "2026-01-01T11:00:00+03:00"},
    }


def room_owned_event(event_id: str = "own") -> dict:
    """An event created directly in the room's calendar: the room is the organizer."""
    event = timed_event(event_id)
    event["organizer"] = {"email": "oda1@gmail.com", "self": True}
    return event


def make_calendar(items: list[dict]) -> tuple[GoogleCalendar, FakeService]:
    service = FakeService(items)
    return GoogleCalendar(service, {"room1": "oda1@gmail.com"}, tz=TZ), service


def test_event_becomes_a_meeting_in_naive_local_time():
    calendar, _ = make_calendar([timed_event()])
    assert calendar.meetings_for("room1") == [
        Meeting(
            "abc", "room1", "ahmet@example.com",
            datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 11, 0),
        )
    ]


def test_all_day_events_are_not_meetings():
    all_day = {"id": "x", "start": {"date": "2026-01-01"}, "end": {"date": "2026-01-02"}}
    calendar, _ = make_calendar([all_day, timed_event()])
    assert [m.meeting_id for m in calendar.meetings_for("room1")] == ["abc"]


def test_it_reads_the_calendar_mapped_to_the_room():
    calendar, service = make_calendar([])
    calendar.meetings_for("room1")
    call = service.events().list_calls[0]
    assert call["calendarId"] == "oda1@gmail.com"
    assert call["singleEvents"] is True  # recurring meetings arrive as separate occurrences


def test_meeting_the_room_already_declined_is_not_a_meeting():
    declined = timed_event("gone")
    declined["attendees"][1]["responseStatus"] = "declined"
    calendar, _ = make_calendar([declined, timed_event()])
    assert [m.meeting_id for m in calendar.meetings_for("room1")] == ["abc"]


def test_cancel_declines_when_the_room_is_only_a_guest():
    calendar, service = make_calendar([timed_event()])
    calendar.cancel_meeting("room1", "abc")

    events = service.events()
    assert events.deleted == []  # the organizer's meeting must stay
    [call] = events.patched
    assert call["calendarId"] == "oda1@gmail.com" and call["eventId"] == "abc"
    assert call["sendUpdates"] == "all"  # tell the organizer the room was released
    statuses = {a["email"]: a["responseStatus"] for a in call["body"]["attendees"]}
    assert statuses == {"ahmet@example.com": "accepted", "oda1@gmail.com": "declined"}


def test_cancel_deletes_when_the_room_organized_the_event():
    calendar, service = make_calendar([room_owned_event()])
    calendar.cancel_meeting("room1", "own")

    events = service.events()
    assert events.deleted == [{"calendarId": "oda1@gmail.com", "eventId": "own"}]
    assert events.patched == []


def test_google_calendar_fits_the_port():
    calendar: CalendarProvider = make_calendar([])[0]
    assert calendar is not None
