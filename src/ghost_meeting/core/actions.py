"""Actions are what the core asks the outside world to do.

The core never sends a Slack message itself; it only returns an action,
and an adapter (e.g. a Notifier) carries it out.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    room_id: str


@dataclass(frozen=True)
class NotifyOrganizer(Action):
    meeting_id: str
    organizer: str
