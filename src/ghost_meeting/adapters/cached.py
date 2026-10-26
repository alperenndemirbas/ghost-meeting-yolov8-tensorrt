"""A wrapper that remembers a calendar's answers for a short while.

The runner asks for meetings on every camera frame (~15 times a second); a real
calendar is a network call, so we only really ask once per `ttl` per room.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from ghost_meeting.core.ports import CalendarProvider, Meeting


class CachedCalendar:
    def __init__(
        self,
        inner: CalendarProvider,
        ttl: timedelta = timedelta(seconds=30),
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._inner = inner
        self._ttl = ttl
        self._clock = clock
        self._cache: dict[str, tuple[datetime, list[Meeting]]] = {}

    def meetings_for(self, room_id: str) -> list[Meeting]:
        now = self._clock()
        cached = self._cache.get(room_id)
        if cached is not None and now - cached[0] < self._ttl:
            return cached[1]
        meetings = self._inner.meetings_for(room_id)
        self._cache[room_id] = (now, meetings)
        return meetings

    def cancel_meeting(self, room_id: str, meeting_id: str) -> None:
        self._inner.cancel_meeting(room_id, meeting_id)
        self._cache.pop(room_id, None)  # our remembered list is now out of date
