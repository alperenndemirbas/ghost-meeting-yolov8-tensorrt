"""Google Calendar login check: python scripts/google_login.py

First run opens the consent flow (log in with the ROOM account). Later runs reuse
secrets/token.json. Then it lists the room calendar's next events as proof it works.
"""

from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.discovery import build

from ghost_meeting.adapters.google_auth import get_credentials

SECRETS_DIR = Path(__file__).resolve().parent.parent / "secrets"


def main() -> None:
    creds = get_credentials(SECRETS_DIR)
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc).isoformat()
    result = service.events().list(
        calendarId="primary", timeMin=now, maxResults=5,
        singleEvents=True, orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    print(f"Login OK. Upcoming events on the room calendar: {len(events)}")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"  {start}  {event.get('summary', '(no title)')}")


if __name__ == "__main__":
    main()
