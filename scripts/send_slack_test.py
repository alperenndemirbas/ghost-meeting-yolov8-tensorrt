"""Slack connection check: python scripts/send_slack_test.py <your Slack member ID>

Sends one direct message from the bot to you. Nothing else in the project is involved,
so if this works, the tokens and bot permissions are fine.
Find your member ID in Slack: your profile -> three dots -> Copy member ID (starts with U).
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from slack_sdk import WebClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test DM from the bot.")
    parser.add_argument("user_id", help="Slack member ID, e.g. U0123456789")
    args = parser.parse_args()

    load_dotenv()  # copies the lines of .env into os.environ
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        sys.exit("SLACK_BOT_TOKEN is missing; check your .env file")

    client = WebClient(token=token)
    # Posting to a user ID opens (or reuses) the bot's direct message with that person.
    client.chat_postMessage(channel=args.user_id, text="Merhaba! Ben Ghost Meeting botuyum.")
    print("Message sent, check Slack.")


if __name__ == "__main__":
    main()
