"""Events are the only way services talk to the core.

Every event is an immutable record of "something happened in a room at a given time".
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class Event:
    room_id: str
    timestamp: datetime


# --- Clock: lets time-based rules fire even when nothing else happens ---
@dataclass(frozen=True)
class Tick(Event):
    pass


# --- Vision: raw observation, one per processed frame (or per second) ---
@dataclass(frozen=True)
class PersonCountObserved(Event):
    count: int


# --- Derived from the raw observations after debouncing ---
@dataclass(frozen=True)
class RoomOccupied(Event):
    pass


@dataclass(frozen=True)
class RoomVacated(Event):
    pass


# --- Calendar: meeting lifecycle ---
@dataclass(frozen=True)
class MeetingStarted(Event):
    meeting_id: str
    organizer: str


@dataclass(frozen=True)
class MeetingEnded(Event):
    meeting_id: str


# --- Messaging: the organizer answered the no-show message ---
class Reply(Enum):
    COMING = "coming"
    CANCEL = "cancel"


@dataclass(frozen=True)
class OrganizerReplied(Event):
    meeting_id: str
    reply: Reply
