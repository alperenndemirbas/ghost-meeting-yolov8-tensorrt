from datetime import datetime, timedelta
from enum import Enum

from ghost_meeting.core.actions import (
    Action,
    AskToReserve,
    NotifyOrganizer,
    ReleaseRoom,
)
from ghost_meeting.core.events import (
    Event,
    MeetingEnded,
    MeetingStarted,
    OrganizerReplied,
    Reply,
    RoomOccupied,
    RoomVacated,
    Tick,
)


class RoomState(Enum):
    IDLE = "idle"
    MEETING_WAITING = "meeting_waiting"
    MEETING_IN_PROGRESS = "meeting_in_progress"
    NO_SHOW_NOTIFIED = "no_show_notified"
    ORGANIZER_COMING = "organizer_coming"
    OCCUPIED_NO_MEETING = "occupied_no_meeting"


class RoomStateMachine:
    """Decides what to do for one room. Events go in, actions come out.

    It does no I/O and never reads the clock; time only advances through
    the timestamps of incoming events.
    """

    def __init__(
        self,
        room_id: str,
        tolerance: timedelta = timedelta(minutes=10),
        dwell: timedelta = timedelta(minutes=2),
        reply_timeout: timedelta = timedelta(minutes=5),
        grace: timedelta = timedelta(minutes=10),
    ):
        self.room_id = room_id
        self.state = RoomState.IDLE
        self._tolerance = tolerance
        self._dwell = dwell
        self._reply_timeout = reply_timeout
        self._grace = grace
        self._occupied = False
        self._occupied_since: datetime | None = None
        self._asked = False
        self._meeting: MeetingStarted | None = None
        # When the room is released if nobody shows up (set after notifying / "coming").
        self._release_at: datetime | None = None

    def handle(self, event: Event) -> list[Action]:
        if isinstance(event, RoomOccupied):
            return self._on_occupied(event)
        if isinstance(event, RoomVacated):
            return self._on_vacated()
        if isinstance(event, MeetingStarted):
            return self._on_meeting_started(event)
        if isinstance(event, MeetingEnded):
            return self._on_meeting_ended(event)
        if isinstance(event, OrganizerReplied):
            return self._on_organizer_replied(event)
        if isinstance(event, Tick):
            return self._on_tick(event)
        return []

    def _on_occupied(self, event: RoomOccupied) -> list[Action]:
        self._occupied = True
        if self.state in (
            RoomState.MEETING_WAITING,
            RoomState.NO_SHOW_NOTIFIED,
            RoomState.ORGANIZER_COMING,
        ):
            self.state = RoomState.MEETING_IN_PROGRESS
        elif self.state == RoomState.IDLE:
            self.state = RoomState.OCCUPIED_NO_MEETING
            self._occupied_since = event.timestamp
            self._asked = False
        return []

    def _on_vacated(self) -> list[Action]:
        self._occupied = False
        if self.state == RoomState.OCCUPIED_NO_MEETING:
            self.state = RoomState.IDLE
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

    def _on_organizer_replied(self, event: OrganizerReplied) -> list[Action]:
        if self._meeting is None or event.meeting_id != self._meeting.meeting_id:
            return []
        if self.state == RoomState.NO_SHOW_NOTIFIED and event.reply == Reply.COMING:
            self.state = RoomState.ORGANIZER_COMING
            self._release_at = event.timestamp + self._grace
            return []
        if event.reply == Reply.CANCEL and self.state in (
            RoomState.NO_SHOW_NOTIFIED,
            RoomState.ORGANIZER_COMING,
        ):
            return self._release()
        return []

    def _release(self) -> list[Action]:
        assert self._meeting is not None
        meeting_id = self._meeting.meeting_id
        self._meeting = None
        self._release_at = None
        self.state = RoomState.IDLE
        return [ReleaseRoom(room_id=self.room_id, meeting_id=meeting_id)]

    def _on_tick(self, event: Tick) -> list[Action]:
        if self.state == RoomState.OCCUPIED_NO_MEETING:
            return self._maybe_ask_to_reserve(event)
        if self.state in (RoomState.NO_SHOW_NOTIFIED, RoomState.ORGANIZER_COMING):
            if self._release_at is not None and event.timestamp >= self._release_at:
                return self._release()
            return []
        if self.state != RoomState.MEETING_WAITING or self._meeting is None:
            return []
        if event.timestamp - self._meeting.timestamp < self._tolerance:
            return []
        self.state = RoomState.NO_SHOW_NOTIFIED
        self._release_at = event.timestamp + self._reply_timeout
        return [
            NotifyOrganizer(
                room_id=self.room_id,
                meeting_id=self._meeting.meeting_id,
                organizer=self._meeting.organizer,
            )
        ]

    def _maybe_ask_to_reserve(self, event: Tick) -> list[Action]:
        if self._asked or self._occupied_since is None:
            return []
        if event.timestamp - self._occupied_since < self._dwell:
            return []
        self._asked = True
        return [AskToReserve(room_id=self.room_id)]
