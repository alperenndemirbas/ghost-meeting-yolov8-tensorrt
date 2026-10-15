from datetime import timedelta
from enum import Enum

from ghost_meeting.core.actions import Action, NotifyOrganizer
from ghost_meeting.core.events import (
    Event,
    MeetingEnded,
    MeetingStarted,
    RoomOccupied,
    RoomVacated,
    Tick,
)


class RoomState(Enum):
    IDLE = "idle"
    MEETING_WAITING = "meeting_waiting"
    MEETING_IN_PROGRESS = "meeting_in_progress"
    NO_SHOW_NOTIFIED = "no_show_notified"


class RoomStateMachine:
    """Decides what to do for one room. Events go in, actions come out.

    It does no I/O and never reads the clock; time only advances through
    the timestamps of incoming events.
    """

    def __init__(self, room_id: str, tolerance: timedelta = timedelta(minutes=10)):
        self.room_id = room_id
        self.state = RoomState.IDLE
        self._tolerance = tolerance
        self._occupied = False
        self._meeting: MeetingStarted | None = None

    def handle(self, event: Event) -> list[Action]:
        if isinstance(event, RoomOccupied):
            return self._on_occupied()
        if isinstance(event, RoomVacated):
            self._occupied = False
            return []
        if isinstance(event, MeetingStarted):
            return self._on_meeting_started(event)
        if isinstance(event, MeetingEnded):
            return self._on_meeting_ended(event)
        if isinstance(event, Tick):
            return self._on_tick(event)
        return []

    def _on_occupied(self) -> list[Action]:
        self._occupied = True
        if self.state in (RoomState.MEETING_WAITING, RoomState.NO_SHOW_NOTIFIED):
            self.state = RoomState.MEETING_IN_PROGRESS
        return []

    def _on_meeting_started(self, event: MeetingStarted) -> list[Action]:
        self._meeting = event
        if self._occupied:
            self.state = RoomState.MEETING_IN_PROGRESS
        else:
            self.state = RoomState.MEETING_WAITING
        return []

    def _on_meeting_ended(self, event: MeetingEnded) -> list[Action]:
        if self._meeting and event.meeting_id == self._meeting.meeting_id:
            self._meeting = None
            self.state = RoomState.IDLE
        return []

    def _on_tick(self, event: Tick) -> list[Action]:
        if self.state != RoomState.MEETING_WAITING or self._meeting is None:
            return []
        if event.timestamp - self._meeting.timestamp < self._tolerance:
            return []
        self.state = RoomState.NO_SHOW_NOTIFIED
        return [
            NotifyOrganizer(
                room_id=self.room_id,
                meeting_id=self._meeting.meeting_id,
                organizer=self._meeting.organizer,
            )
        ]
