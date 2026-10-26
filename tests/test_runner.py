from datetime import datetime, timedelta

from ghost_meeting.adapters.mock import MockCalendar, MockNotifier, MockPrompter
from ghost_meeting.core.actions import AskToReserve, NotifyOrganizer
from ghost_meeting.core.events import OrganizerReplied, Reply
from ghost_meeting.core.ports import Meeting
from ghost_meeting.core.state_machine import RoomState
from ghost_meeting.runner import RoomRunner

T0 = datetime(2026, 1, 1, 10, 0, 0)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def make_runner() -> tuple[RoomRunner, MockNotifier]:
    calendar = MockCalendar()
    calendar.add_meeting(Meeting("m1", "room1", "ahmet", at(0), at(60)))
    notifier = MockNotifier()
    return RoomRunner("room1", calendar, notifier, MockPrompter()), notifier


def test_nobody_shows_up_organizer_gets_notified():
    runner, notifier = make_runner()
    for minute in range(0, 12):
        runner.advance(at(minute), person_count=0)
    assert notifier.sent == [NotifyOrganizer("room1", "m1", "ahmet")]
    assert runner.machine.state == RoomState.NO_SHOW_NOTIFIED


def test_someone_arrives_in_time_nobody_is_notified():
    runner, notifier = make_runner()
    runner.advance(at(0), person_count=0)
    # Presence must hold for the 3 s debounce before the room counts as occupied.
    runner.advance(at(5), person_count=1)
    runner.advance(at(5) + timedelta(seconds=3), person_count=1)
    runner.advance(at(12), person_count=1)
    assert notifier.sent == []
    assert runner.machine.state == RoomState.MEETING_IN_PROGRESS


def test_meeting_end_returns_room_to_idle():
    runner, _ = make_runner()
    runner.advance(at(0), person_count=0)
    runner.advance(at(61), person_count=0)
    assert runner.machine.state == RoomState.IDLE


def test_same_meeting_is_not_started_twice():
    runner, notifier = make_runner()
    for minute in range(0, 30):
        runner.advance(at(minute), person_count=0)
    assert len(notifier.sent) == 1


def test_unanswered_no_show_releases_room_in_the_calendar():
    calendar = MockCalendar()
    calendar.add_meeting(Meeting("m1", "room1", "ahmet", at(0), at(60)))
    runner = RoomRunner("room1", calendar, MockNotifier(), MockPrompter())
    # Notified at minute 10; the 5 min reply window then runs out with no answer.
    for minute in range(0, 17):
        runner.advance(at(minute), person_count=0)
    assert calendar.meetings_for("room1") == []
    assert runner.machine.state == RoomState.IDLE


# --- Replies arriving from another thread (Slack) through the runner's mailbox ---
def make_notified_runner() -> tuple[RoomRunner, MockCalendar]:
    calendar = MockCalendar()
    calendar.add_meeting(Meeting("m1", "room1", "ahmet", at(0), at(60)))
    runner = RoomRunner("room1", calendar, MockNotifier(), MockPrompter())
    for minute in range(0, 11):  # organizer gets notified at minute 10
        runner.advance(at(minute), person_count=0)
    assert runner.machine.state == RoomState.NO_SHOW_NOTIFIED
    return runner, calendar


def test_submitted_cancel_reply_releases_room_on_next_advance():
    runner, calendar = make_notified_runner()
    runner.submit(OrganizerReplied("room1", at(11), "m1", Reply.CANCEL))
    assert len(calendar.meetings_for("room1")) == 1  # nothing happens until advance
    runner.advance(at(11), person_count=0)
    assert calendar.meetings_for("room1") == []
    assert runner.machine.state == RoomState.IDLE


def test_submitted_coming_reply_keeps_the_meeting():
    runner, calendar = make_notified_runner()
    runner.submit(OrganizerReplied("room1", at(11), "m1", Reply.COMING))
    runner.advance(at(11), person_count=0)
    assert len(calendar.meetings_for("room1")) == 1
    assert runner.machine.state == RoomState.ORGANIZER_COMING


# --- Scenario 2 end to end: no meeting booked, someone walks in and stays ---
def make_empty_calendar_runner() -> tuple[RoomRunner, MockPrompter]:
    prompter = MockPrompter()
    runner = RoomRunner("room1", MockCalendar(), MockNotifier(), prompter=prompter)
    return runner, prompter


def test_person_staying_in_unbooked_room_gets_asked_once():
    runner, prompter = make_empty_calendar_runner()
    runner.advance(at(0), person_count=1)
    runner.advance(at(0) + timedelta(seconds=3), person_count=1)  # debounce passes
    runner.advance(at(1), person_count=1)
    assert prompter.asked == []
    runner.advance(at(2.1), person_count=1)
    assert prompter.asked == [AskToReserve("room1")]
    runner.advance(at(30), person_count=1)
    assert len(prompter.asked) == 1


def test_person_passing_through_is_not_asked():
    runner, prompter = make_empty_calendar_runner()
    runner.advance(at(0), person_count=1)
    runner.advance(at(0) + timedelta(seconds=1), person_count=0)  # gone before debounce
    runner.advance(at(10), person_count=0)
    assert prompter.asked == []
