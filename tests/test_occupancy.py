from datetime import datetime, timedelta

from ghost_meeting.core.events import PersonCountObserved, RoomOccupied, RoomVacated
from ghost_meeting.core.occupancy import OccupancyTracker

T0 = datetime(2026, 1, 1, 10, 0, 0)


def obs(seconds: float, count: int) -> PersonCountObserved:
    return PersonCountObserved(
        room_id="room1", timestamp=T0 + timedelta(seconds=seconds), count=count
    )


def feed(tracker: OccupancyTracker, readings: list[tuple[float, int]]) -> list:
    events = [tracker.update(obs(s, c)) for s, c in readings]
    return [e for e in events if e is not None]


def test_empty_room_stays_silent():
    tracker = OccupancyTracker()
    assert feed(tracker, [(0, 0), (2, 0), (10, 0)]) == []


def test_person_present_for_debounce_marks_room_occupied():
    tracker = OccupancyTracker()
    events = feed(tracker, [(0, 1), (1, 1), (2, 1), (3, 1)])
    assert len(events) == 1
    assert isinstance(events[0], RoomOccupied)


def test_person_walking_past_is_ignored():
    tracker = OccupancyTracker()
    assert feed(tracker, [(0, 1), (1, 1), (2, 0), (5, 0)]) == []


def test_flicker_resets_the_timer():
    tracker = OccupancyTracker()
    # Person seen, lost for one frame, seen again: the 3 s clock restarts at t=3.
    events = feed(tracker, [(0, 1), (2, 0), (3, 1), (5, 1)])
    assert events == []


def test_leaving_for_debounce_marks_room_vacated():
    tracker = OccupancyTracker()
    events = feed(tracker, [(0, 1), (3, 1), (4, 0), (7, 0)])
    assert [type(e) for e in events] == [RoomOccupied, RoomVacated]
