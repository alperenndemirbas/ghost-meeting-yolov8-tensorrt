from datetime import datetime, timedelta

from ghost_meeting.core.actions import NotifyOrganizer
from ghost_meeting.core.events import (
    MeetingEnded,
    MeetingStarted,
    RoomOccupied,
    Tick,
)
from ghost_meeting.core.state_machine import RoomState, RoomStateMachine

T0 = datetime(2026, 1, 1, 10, 0, 0)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def meeting_started(minutes: float = 0) -> MeetingStarted:
    return MeetingStarted(
        room_id="room1", timestamp=at(minutes), meeting_id="m1", organizer="ahmet"
    )


def tick(minutes: float) -> Tick:
    return Tick(room_id="room1", timestamp=at(minutes))


def occupied(minutes: float) -> RoomOccupied:
    return RoomOccupied(room_id="room1", timestamp=at(minutes))


def test_empty_room_after_tolerance_notifies_organizer():
    machine = RoomStateMachine("room1")
    machine.handle(meeting_started())
    assert machine.handle(tick(9)) == []
    actions = machine.handle(tick(10))
    assert actions == [NotifyOrganizer("room1", "m1", "ahmet")]
    assert machine.state == RoomState.NO_SHOW_NOTIFIED


def test_organizer_is_notified_only_once():
    machine = RoomStateMachine("room1")
    machine.handle(meeting_started())
    machine.handle(tick(10))
    assert machine.handle(tick(11)) == []


def test_arriving_before_tolerance_prevents_notification():
    machine = RoomStateMachine("room1")
    machine.handle(meeting_started())
    machine.handle(occupied(5))
    assert machine.handle(tick(12)) == []
    assert machine.state == RoomState.MEETING_IN_PROGRESS


def test_room_already_occupied_when_meeting_starts():
    machine = RoomStateMachine("room1")
    machine.handle(occupied(-1))
    machine.handle(meeting_started())
    assert machine.state == RoomState.MEETING_IN_PROGRESS
    assert machine.handle(tick(15)) == []


def test_arriving_after_notification_moves_to_in_progress():
    machine = RoomStateMachine("room1")
    machine.handle(meeting_started())
    machine.handle(tick(10))
    machine.handle(occupied(11))
    assert machine.state == RoomState.MEETING_IN_PROGRESS


def test_meeting_end_returns_to_idle():
    machine = RoomStateMachine("room1")
    machine.handle(meeting_started())
    machine.handle(MeetingEnded(room_id="room1", timestamp=at(30), meeting_id="m1"))
    assert machine.state == RoomState.IDLE
    assert machine.handle(tick(40)) == []
