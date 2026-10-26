from datetime import datetime, timedelta

from ghost_meeting.adapters.cached import CachedCalendar
from ghost_meeting.adapters.mock import MockCalendar
from ghost_meeting.core.ports import CalendarProvider, Meeting

T0 = datetime(2026, 1, 1, 10, 0, 0)


class CountingCalendar(MockCalendar):
    """A MockCalendar that counts how often the 'real' source is asked."""

    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    def meetings_for(self, room_id: str) -> list[Meeting]:
        self.reads += 1
        return super().meetings_for(room_id)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


def meeting(meeting_id: str, room_id: str = "room1") -> Meeting:
    return Meeting(meeting_id, room_id, "ahmet", T0, T0 + timedelta(hours=1))


def make_cached() -> tuple[CachedCalendar, CountingCalendar, Clock]:
    inner, clock = CountingCalendar(), Clock()
    inner.add_meeting(meeting("m1"))
    return CachedCalendar(inner, ttl=timedelta(seconds=30), clock=clock), inner, clock


def test_repeated_reads_within_ttl_hit_the_source_once():
    cached, inner, clock = make_cached()
    for _ in range(100):
        cached.meetings_for("room1")
        clock.now += timedelta(milliseconds=66)  # ~15 fps
    assert inner.reads == 1


def test_read_after_ttl_asks_the_source_again():
    cached, inner, clock = make_cached()
    cached.meetings_for("room1")
    clock.now += timedelta(seconds=31)
    cached.meetings_for("room1")
    assert inner.reads == 2


def test_rooms_are_cached_separately():
    cached, inner, _ = make_cached()
    inner.add_meeting(meeting("m2", "room2"))
    assert [m.meeting_id for m in cached.meetings_for("room1")] == ["m1"]
    assert [m.meeting_id for m in cached.meetings_for("room2")] == ["m2"]
    assert inner.reads == 2


def test_cancel_goes_to_the_source_and_the_next_read_is_fresh():
    cached, inner, _ = make_cached()
    cached.meetings_for("room1")
    cached.cancel_meeting("room1", "m1")
    assert cached.meetings_for("room1") == []  # not the stale cached list
    assert inner.reads == 2


def test_cached_calendar_fits_the_port():
    cached: CalendarProvider = make_cached()[0]
    assert cached is not None
