"""Slack side of the organizer dialogue: sends the buttoned DM, decodes the clicks."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from ghost_meeting.core.actions import NotifyOrganizer
from ghost_meeting.core.events import OrganizerReplied, Reply

ACTION_COMING = "organizer_coming"
ACTION_CANCEL = "organizer_cancel"
ANSWERED_TEXT = "✅ Cevabınız alındı."


class UnknownOrganizerError(LookupError):
    """The organizer has no known Slack ID, so nobody could be notified."""


class SlackClient(Protocol):
    """The one slack_sdk.WebClient method we use; tests swap in a fake."""

    def chat_postMessage(self, **kwargs) -> object: ...


class SlackNotifier:
    def __init__(self, client: SlackClient, user_ids: dict[str, str]) -> None:
        self._client = client
        self._user_ids = user_ids

    def notify_organizer(self, action: NotifyOrganizer) -> None:
        user_id = self._user_ids.get(action.organizer)
        if user_id is None:
            raise UnknownOrganizerError(f"No Slack ID for organizer {action.organizer!r}")

        text = f"{action.room_id} odasındaki toplantınız başladı ama kimse gelmedi."
        self._client.chat_postMessage(
            channel=user_id,
            text=text,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{text} Geliyor musunuz?"},
                },
                {
                    "type": "actions",
                    "elements": [
                        _button("Geleceğim", ACTION_COMING, action.meeting_id),
                        _button("İptal Et", ACTION_CANCEL, action.meeting_id),
                    ],
                },
            ],
        )


_REPLIES = {ACTION_COMING: Reply.COMING, ACTION_CANCEL: Reply.CANCEL}


def reply_from_click(
    room_id: str, action_id: str, meeting_id: str, now: datetime
) -> OrganizerReplied:
    """Translate a Slack button click into the core's own language (an event)."""
    reply = _REPLIES.get(action_id)
    if reply is None:
        raise ValueError(f"Unknown button action_id {action_id!r}")
    return OrganizerReplied(room_id, now, meeting_id, reply)


def make_click_handler(
    room_id: str,
    submit: Callable[[OrganizerReplied], None],
    clock: Callable[[], datetime] = datetime.now,
) -> Callable[..., None]:
    """Build the function Bolt calls when a button is clicked.

    `submit` is e.g. `runner.submit`; `clock` is injectable so tests control time.
    """

    def handle_click(ack: Callable[[], None], body: dict, respond: Callable[..., None]) -> None:
        ack()  # Slack wants an answer within 3 s, so this comes before anything else
        action = body["actions"][0]
        submit(reply_from_click(room_id, action["action_id"], action["value"], clock()))
        # Swap the buttoned message for plain text so the buttons can't be clicked again
        respond(
            replace_original=True,
            text=ANSWERED_TEXT,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": ANSWERED_TEXT}}],
        )

    return handle_click


def start_click_listener(
    bot_token: str, app_token: str, handler: Callable[..., None]
) -> SocketModeHandler:
    """Connect to Slack over Socket Mode and route both buttons to `handler`.

    Returns right away: Bolt runs the connection in its own background thread.
    """
    app = App(token=bot_token)
    for action_id in _REPLIES:
        app.action(action_id)(handler)
    socket = SocketModeHandler(app, app_token)
    socket.connect()
    return socket


def _button(label: str, action_id: str, meeting_id: str) -> dict:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": action_id,
        "value": meeting_id,
    }
