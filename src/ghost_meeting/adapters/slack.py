"""Real Notifier: sends the organizer a Slack direct message with buttons."""

from typing import Protocol

from ghost_meeting.core.actions import NotifyOrganizer

ACTION_COMING = "organizer_coming"
ACTION_CANCEL = "organizer_cancel"


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


def _button(label: str, action_id: str, meeting_id: str) -> dict:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": action_id,
        "value": meeting_id,
    }
