from datetime import datetime, timedelta

from ghost_meeting.core.actions import AskToReserve, NotifyOrganizer, ReleaseRoom
from ghost_meeting.core.events import (
    MeetingEnded,
    MeetingStarted,
    OrganizerReplied,
    Reply,
    RoomOccupied,
    RoomVacated,
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


# --- Scenario 2: someone is in the room but no meeting is booked ---
def vacated(minutes: float) -> RoomVacated:
    return RoomVacated(room_id="room1", timestamp=at(minutes))


def test_person_in_idle_room_moves_to_occupied_no_meeting():
    machine = RoomStateMachine("room1")
    machine.handle(occupied(0))
    assert machine.state == RoomState.OCCUPIED_NO_MEETING


def test_asks_to_reserve_after_dwell_time():
    machine = RoomStateMachine("room1", dwell=timedelta(minutes=2))
    machine.handle(occupied(0))
    assert machine.handle(tick(1.9)) == []
    assert machine.handle(tick(2)) == [AskToReserve("room1")]


def test_asks_only_once_per_visit():
    machine = RoomStateMachine("room1", dwell=timedelta(minutes=2))
    machine.handle(occupied(0))
    machine.handle(tick(2))
    assert machine.handle(tick(3)) == []
    assert machine.handle(tick(60)) == []


def test_leaving_before_dwell_time_asks_nothing():
    machine = RoomStateMachine("room1", dwell=timedelta(minutes=2))
    machine.handle(occupied(0))
    machine.handle(vacated(1))
    assert machine.state == RoomState.IDLE
    assert machine.handle(tick(5)) == []


def test_new_visit_after_leaving_can_be_asked_again():
    machine = RoomStateMachine("room1", dwell=timedelta(minutes=2))
    machine.handle(occupied(0))
    machine.handle(tick(2))
    machine.handle(vacated(10))
    machine.handle(occupied(60))
    assert machine.handle(tick(61)) == []
    assert machine.handle(tick(62)) == [AskToReserve("room1")]


def test_meeting_starting_while_occupied_moves_to_in_progress():
    machine = RoomStateMachine("room1", dwell=timedelta(minutes=2))
    machine.handle(occupied(0))
    machine.handle(tick(2))
    machine.handle(meeting_started(30))
    assert machine.state == RoomState.MEETING_IN_PROGRESS
    assert machine.handle(tick(40)) == []


def test_never_asks_while_a_meeting_is_in_progress():
    machine = RoomStateMachine("room1", dwell=timedelta(minutes=2))
    machine.handle(meeting_started())
    machine.handle(occupied(1))
    assert machine.handle(tick(30)) == []


# --- Organizer's answer to the no-show message ---
def replied(minutes: float, reply: Reply, meeting_id: str = "m1") -> OrganizerReplied:
    return OrganizerReplied(
        room_id="room1", timestamp=at(minutes), meeting_id=meeting_id, reply=reply
    )


def notified_machine() -> RoomStateMachine:
    """Meeting m1 started at 0, organizer was notified at minute 10."""
    machine = RoomStateMachine(
        "room1", reply_timeout=timedelta(minutes=5), grace=timedelta(minutes=10)
    )
    machine.handle(meeting_started())
    machine.handle(tick(10))
    return machine


def test_cancel_reply_releases_room_immediately():
    machine = notified_machine()
    actions = machine.handle(replied(11, Reply.CANCEL))
    assert actions == [ReleaseRoom("room1", "m1")]
    assert machine.state == RoomState.IDLE


def test_no_reply_releases_room_after_reply_timeout():
    machine = notified_machine()
    assert machine.handle(tick(14.9)) == []
    assert machine.handle(tick(15)) == [ReleaseRoom("room1", "m1")]
    assert machine.state == RoomState.IDLE


def test_room_is_released_only_once():
    machine = notified_machine()
    machine.handle(tick(15))
    assert machine.handle(tick(16)) == []


def test_coming_reply_gives_extra_grace_from_the_reply_time():
    machine = notified_machine()
    assert machine.handle(replied(11, Reply.COMING)) == []
    assert machine.state == RoomState.ORGANIZER_COMING
    # the 5-minute reply timeout no longer applies
    assert machine.handle(tick(15)) == []
    assert machine.handle(tick(20.9)) == []
    assert machine.handle(tick(21)) == [ReleaseRoom("room1", "m1")]
    assert machine.state == RoomState.IDLE


def test_arriving_after_coming_reply_keeps_the_room():
    machine = notified_machine()
    machine.handle(replied(11, Reply.COMING))
    machine.handle(occupied(14))
    assert machine.state == RoomState.MEETING_IN_PROGRESS
    assert machine.handle(tick(30)) == []


def test_arriving_before_reply_timeout_keeps_the_room():
    machine = notified_machine()
    machine.handle(occupied(12))
    assert machine.handle(tick(20)) == []
    assert machine.state == RoomState.MEETING_IN_PROGRESS


def test_reply_for_another_meeting_is_ignored():
    machine = notified_machine()
    assert machine.handle(replied(11, Reply.CANCEL, meeting_id="other")) == []
    assert machine.state == RoomState.NO_SHOW_NOTIFIED


def test_late_reply_after_room_was_released_is_ignored():
    machine = notified_machine()
    machine.handle(tick(15))
    assert machine.handle(replied(16, Reply.CANCEL)) == []
    assert machine.state == RoomState.IDLE


def test_cancel_reply_after_organizer_arrived_is_ignored():
    machine = notified_machine()
    machine.handle(occupied(12))
    assert machine.handle(replied(13, Reply.CANCEL)) == []
    assert machine.state == RoomState.MEETING_IN_PROGRESS
