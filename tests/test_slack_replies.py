from datetime import datetime

import pytest

from ghost_meeting.adapters.slack import (
    ACTION_CANCEL,
    ACTION_COMING,
    make_click_handler,
    reply_from_click,
)
from ghost_meeting.core.events import OrganizerReplied, Reply

NOW = datetime(2026, 1, 1, 10, 11, 0)


def test_coming_button_becomes_a_coming_reply():
    event = reply_from_click("room1", ACTION_COMING, "m1", NOW)
    assert event == OrganizerReplied("room1", NOW, "m1", Reply.COMING)


def test_cancel_button_becomes_a_cancel_reply():
    event = reply_from_click("room1", ACTION_CANCEL, "m1", NOW)
    assert event == OrganizerReplied("room1", NOW, "m1", Reply.CANCEL)


def test_unknown_button_is_an_error_not_silently_ignored():
    with pytest.raises(ValueError):
        reply_from_click("room1", "something_else", "m1", NOW)


# --- The handler Bolt calls on a click: ack, translate, hand over ---
def click_body(action_id: str, meeting_id: str) -> dict:
    """The slice of Slack's payload we read; the real one has many more fields."""
    return {"actions": [{"action_id": action_id, "value": meeting_id}]}


def test_click_handler_acks_and_submits_the_event():
    submitted: list[OrganizerReplied] = []
    acked: list[bool] = []
    handler = make_click_handler("room1", submitted.append, clock=lambda: NOW)

    handler(
        ack=lambda: acked.append(True),
        body=click_body(ACTION_CANCEL, "m1"),
        respond=lambda **kwargs: None,
    )

    assert acked == [True]
    assert submitted == [OrganizerReplied("room1", NOW, "m1", Reply.CANCEL)]


def test_click_handler_replaces_the_message_so_the_buttons_disappear():
    responses: list[dict] = []
    handler = make_click_handler("room1", lambda event: None, clock=lambda: NOW)

    handler(
        ack=lambda: None,
        body=click_body(ACTION_COMING, "m1"),
        respond=lambda **kwargs: responses.append(kwargs),
    )

    assert len(responses) == 1
    assert responses[0]["replace_original"] is True
    assert "Cevabınız alındı" in responses[0]["text"]
    # No "actions" block left, so there is nothing to click again
    assert all(block["type"] != "actions" for block in responses[0]["blocks"])


def test_click_handler_acks_even_when_the_button_is_unknown():
    # Slack shows the user an error if we don't ack within 3 s, so ack comes first.
    acked: list[bool] = []
    handler = make_click_handler("room1", lambda event: None, clock=lambda: NOW)

    with pytest.raises(ValueError):
        handler(
            ack=lambda: acked.append(True),
            body=click_body("something_else", "m1"),
            respond=lambda **kwargs: None,
        )

    assert acked == [True]
