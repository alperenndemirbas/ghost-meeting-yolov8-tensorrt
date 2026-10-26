"""Real CalendarProvider: reads and edits a room's Google Calendar.

Each room has its own Google account, so a room maps to one calendar id.
"""

from datetime import datetime, timedelta, tzinfo
from typing import Any

from ghost_meeting.core.ports import Meeting

# How much of the calendar we look at around "now".
LOOKBEHIND = timedelta(hours=12)
LOOKAHEAD = timedelta(hours=24)


def _room_declined(event: dict) -> bool:
    """`self: true` marks the attendee entry that belongs to the calendar's owner."""
    return any(
        a.get("self") and a.get("responseStatus") == "declined"
        for a in event.get("attendees", [])
    )


class GoogleCalendar:
    def __init__(
        self,
        service: Any,
        calendar_ids: dict[str, str],
        tz: tzinfo | None = None,
    ) -> None:
        """`service` is googleapiclient's calendar client (a fake in tests).

        `tz` is the zone the room runs in; None means the machine's own zone.
        """
        self._service = service
        self._calendar_ids = calendar_ids
        self._tz = tz

    def meetings_for(self, room_id: str) -> list[Meeting]:
        now = datetime.now(self._tz).astimezone(self._tz)
        response = self._service.events().list(
            calendarId=self._calendar_ids[room_id],
            timeMin=(now - LOOKBEHIND).isoformat(),
            timeMax=(now + LOOKAHEAD).isoformat(),
            singleEvents=True,  # expand recurring meetings into separate occurrences
            orderBy="startTime",
        ).execute()

        meetings = []
        for event in response.get("items", []):
            start, end = event["start"], event["end"]
            if "dateTime" not in start:  # all-day event, not a meeting
                continue
            if _room_declined(event):  # we released it earlier; Google still lists it
                continue
            meetings.append(
                Meeting(
                    meeting_id=event["id"],
                    room_id=room_id,
                    organizer=event["organizer"]["email"],
                    start=self._to_local(start["dateTime"]),
                    end=self._to_local(end["dateTime"]),
                )
            )
        return meetings

    def cancel_meeting(self, room_id: str, meeting_id: str) -> None:
        """Release the room. If the room owns the event, delete it; if it is only a
        guest, decline, so the organizer's meeting survives and they are told."""
        calendar_id = self._calendar_ids[room_id]
        events = self._service.events()
        event = events.get(calendarId=calendar_id, eventId=meeting_id).execute()

        if event.get("organizer", {}).get("self"):
            events.delete(calendarId=calendar_id, eventId=meeting_id).execute()
            return

        attendees = event.get("attendees", [])
        for attendee in attendees:
            if attendee.get("self"):
                attendee["responseStatus"] = "declined"
        events.patch(
            calendarId=calendar_id,
            eventId=meeting_id,
            body={"attendees": attendees},
            sendUpdates="all",
        ).execute()

    def _to_local(self, iso_time: str) -> datetime:
        """Google sends '...+03:00'; the core uses naive local time (datetime.now())."""
        return datetime.fromisoformat(iso_time).astimezone(self._tz).replace(tzinfo=None)
