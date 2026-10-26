"""Google OAuth for the room's account: first login once, silent refresh afterwards.

Two files live in the secrets folder:
- credentials.json: the app's identity (Client ID + Secret), downloaded from Google Cloud.
- token.json: what the room account granted us; holds the long-lived refresh token.
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Least privilege: events only, no access to calendar settings or sharing.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def get_credentials(secrets_dir: Path) -> Credentials:
    credentials_file = secrets_dir / "credentials.json"
    token_file = secrets_dir / "token.json"

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        # Access token (~1 h) ran out: trade the refresh token for a new one, no browser.
        creds.refresh(Request())
    else:
        # First time (or consent revoked): the browser dance. Needs a human, once.
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=False)

    token_file.write_text(creds.to_json())
    return creds
