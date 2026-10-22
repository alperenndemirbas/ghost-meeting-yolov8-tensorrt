"""Glue between the outside world and the core, for one room.

The runner owns no business rules. It translates (calendar, camera, clock) into
events, feeds them to the state machine, and hands the resulting actions to adapters.
Time comes in as an argument, so a test can simulate hours in microseconds.
"""

from datetime import datetime

from ghost_meeting.core.actions import Action, AskToReserve, NotifyOrganizer
from ghost_meeting.core.events import (
    Event,
    MeetingEnded,
    MeetingStarted,
    PersonCountObserved,
    Tick,
)
from ghost_meeting.core.occupancy import OccupancyTracker
from ghost_meeting.core.ports import CalendarProvider, Notifier, Prompter
from ghost_meeting.core.state_machine import RoomStateMachine


class RoomRunner:
    def __init__(
        self,
        room_id: str,
        calendar: CalendarProvider,
        notifier: Notifier,
        prompter: Prompter,
        machine: RoomStateMachine | None = None,
        tracker: OccupancyTracker | None = None,
    ) -> None:
        self.room_id = room_id
        self.machine = machine or RoomStateMachine(room_id)
        self._tracker = tracker or OccupancyTracker()
        self._calendar = calendar
        self._notifier = notifier
        self._prompter = prompter
        self._started: set[str] = set()
        self._ended: set[str] = set()

    def advance(self, now: datetime, person_count: int | None = None) -> None:
        """Move the room's clock to `now`, optionally with a fresh camera reading."""
        events: list[Event] = self._calendar_events(now)

        if person_count is not None:
            observation = PersonCountObserved(self.room_id, now, person_count)
            derived = self._tracker.update(observation)
            if derived is not None:
                events.append(derived)

        events.append(Tick(self.room_id, now))

        for event in events:
            for action in self.machine.handle(event):
                self._dispatch(action)

    def _calendar_events(self, now: datetime) -> list[Event]:
        events: list[Event] = []
        for meeting in self._calendar.meetings_for(self.room_id):
            if meeting.start <= now and meeting.meeting_id not in self._started:
                self._started.add(meeting.meeting_id)
                events.append(
                    MeetingStarted(
                        self.room_id, meeting.start, meeting.meeting_id, meeting.organizer
                    )
                )
            if meeting.end <= now and meeting.meeting_id not in self._ended:
                self._ended.add(meeting.meeting_id)
                events.append(MeetingEnded(self.room_id, meeting.end, meeting.meeting_id))
        return events

    def _dispatch(self, action: Action) -> None:
        if isinstance(action, NotifyOrganizer):
            self._notifier.notify_organizer(action)
        elif isinstance(action, AskToReserve):
            self._prompter.ask_to_reserve(action)
