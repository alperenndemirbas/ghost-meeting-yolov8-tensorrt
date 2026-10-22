"""SlackNotifier check: python scripts/send_slack_notifier_demo.py <your Slack member ID>

Pushes a fake NotifyOrganizer action through the real SlackNotifier, so you get the
buttoned message on your phone. The buttons do nothing yet (nobody listens for clicks).
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from slack_sdk import WebClient

from ghost_meeting.adapters.slack import SlackNotifier
from ghost_meeting.core.actions import NotifyOrganizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a buttoned test message.")
    parser.add_argument("user_id", help="Slack member ID, e.g. U0123456789")
    args = parser.parse_args()

    load_dotenv()
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        sys.exit("SLACK_BOT_TOKEN is missing; check your .env file")

    # "ahmet" is the organizer name used in the fake meeting; here it maps to you.
    notifier = SlackNotifier(WebClient(token=token), user_ids={"ahmet": args.user_id})
    notifier.notify_organizer(NotifyOrganizer("room1", "m1", "ahmet"))
    print("Message sent, check Slack.")


if __name__ == "__main__":
    main()
