from datetime import datetime, timedelta

from ghost_meeting.core.events import (
    Event,
    PersonCountObserved,
    RoomOccupied,
    RoomVacated,
)


class OccupancyTracker:
    """Turns noisy per-frame person counts into stable occupied/vacated events.

    A change is only reported once the new reading has held continuously for
    `debounce`, so someone walking past the door does not flip the room state.
    One tracker instance per room.
    """

    def __init__(self, debounce: timedelta = timedelta(seconds=3)):
        self._debounce = debounce
        self._occupied = False
        self._disagree_since: datetime | None = None

    def update(self, observation: PersonCountObserved) -> Event | None:
        people_seen = observation.count > 0

        if people_seen == self._occupied:
            self._disagree_since = None
            return None

        if self._disagree_since is None:
            self._disagree_since = observation.timestamp

        if observation.timestamp - self._disagree_since < self._debounce:
            return None

        self._occupied = people_seen
        self._disagree_since = None
        event_type = RoomOccupied if people_seen else RoomVacated
        return event_type(room_id=observation.room_id, timestamp=observation.timestamp)
