"""Ports: what the core needs from the outside world, without saying how it is done.

Any class that has these methods can be plugged in (structural typing via Protocol).
Real adapters (Slack, Google Calendar) and mock adapters satisfy the same contract.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ghost_meeting.core.actions import AskToReserve, NotifyOrganizer


@dataclass(frozen=True)
class Meeting:
    meeting_id: str
    room_id: str
    organizer: str
    start: datetime
    end: datetime


class Notifier(Protocol):
    def notify_organizer(self, action: NotifyOrganizer) -> None: ...


class Prompter(Protocol):
    def ask_to_reserve(self, action: AskToReserve) -> None: ...


class CalendarProvider(Protocol):
    def meetings_for(self, room_id: str) -> list[Meeting]: ...
