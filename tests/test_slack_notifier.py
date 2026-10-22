import pytest

from ghost_meeting.adapters.slack import SlackNotifier, UnknownOrganizerError
from ghost_meeting.core.actions import NotifyOrganizer
from ghost_meeting.core.ports import Notifier


class FakeSlackClient:
    """Stands in for slack_sdk.WebClient: remembers calls instead of hitting the network."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat_postMessage(self, **kwargs) -> None:
        self.calls.append(kwargs)


def make_notifier() -> tuple[SlackNotifier, FakeSlackClient]:
    client = FakeSlackClient()
    return SlackNotifier(client, user_ids={"ahmet": "U111"}), client


def buttons_of(call: dict) -> list[dict]:
    actions = [b for b in call["blocks"] if b["type"] == "actions"]
    assert len(actions) == 1
    return actions[0]["elements"]


def test_message_goes_to_the_organizers_slack_id():
    notifier, client = make_notifier()
    notifier.notify_organizer(NotifyOrganizer("room1", "m1", "ahmet"))
    assert len(client.calls) == 1
    assert client.calls[0]["channel"] == "U111"


def test_message_mentions_the_room_and_has_plain_text_fallback():
    notifier, client = make_notifier()
    notifier.notify_organizer(NotifyOrganizer("room1", "m1", "ahmet"))
    call = client.calls[0]
    assert "room1" in call["text"]  # shown in notifications, where blocks are not rendered
    section = next(b for b in call["blocks"] if b["type"] == "section")
    assert "room1" in section["text"]["text"]


def test_message_has_coming_and_cancel_buttons_carrying_the_meeting_id():
    notifier, client = make_notifier()
    notifier.notify_organizer(NotifyOrganizer("room1", "m1", "ahmet"))
    buttons = buttons_of(client.calls[0])
    assert [b["action_id"] for b in buttons] == ["organizer_coming", "organizer_cancel"]
    assert [b["value"] for b in buttons] == ["m1", "m1"]


def test_unknown_organizer_raises_instead_of_failing_silently():
    notifier, client = make_notifier()
    with pytest.raises(UnknownOrganizerError):
        notifier.notify_organizer(NotifyOrganizer("room1", "m1", "mehmet"))
    assert client.calls == []


def test_slack_notifier_fits_the_port():
    notifier: Notifier = SlackNotifier(FakeSlackClient(), user_ids={})
    assert notifier is not None
