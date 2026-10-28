"""Live demo: python scripts/run_room.py [rtsp url] [--scenario 1|2] [--slack ID]
[--google --organizer EMAIL] [--voice] [--tolerance-seconds N]  (q stops)

Scenario 1 (default): a fake meeting starts in 5 seconds with a 20 second tolerance.
Stay out of the camera's view and the MockNotifier complains about 25 seconds from now.
Scenario 2: no meeting is booked. Walk into view and stay for 15 seconds, and the
MockPrompter asks whether to reserve the room.
--google: use the room account's real Google Calendar (book a meeting there yourself).
A debug window shows what the camera sees, with boxes around detected people.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv
from googleapiclient.discovery import build
from slack_sdk import WebClient

from ghost_meeting.adapters.cached import CachedCalendar
from ghost_meeting.adapters.google_auth import get_credentials
from ghost_meeting.adapters.google_calendar import GoogleCalendar
from ghost_meeting.adapters.mock import MockCalendar, MockNotifier, MockPrompter
from ghost_meeting.adapters.slack import SlackNotifier, make_click_handler, start_click_listener
from ghost_meeting.adapters.voice import VoicePrompter, piper_speaker, speak_in_background
from ghost_meeting.core.ports import CalendarProvider, Meeting, Notifier, Prompter
from ghost_meeting.core.state_machine import RoomStateMachine
from ghost_meeting.runner import RoomRunner
from ghost_meeting.vision.detector import Detection, PersonDetector

DEFAULT_URL = "rtsp://localhost:8554/room1"
ROOM_ID = "room1"
PROJECT_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = PROJECT_DIR / "secrets"
VOICE_MODEL = PROJECT_DIR / "models" / "tts" / "tr_TR-dfki-medium.onnx"


GREEN = (0, 255, 0)  # OpenCV colors are BGR, not RGB


def read_and_detect(
    capture: cv2.VideoCapture, detector: PersonDetector
) -> tuple[np.ndarray, list[Detection]] | None:
    """Blocking: waits for one frame, then runs YOLO on it."""
    ok, frame = capture.read()
    if not ok:
        return None
    return frame, detector.detect_people(frame)


def draw_overlay(frame: np.ndarray, detections: list[Detection], state_name: str) -> None:
    """Draws boxes and a status line directly onto `frame`."""
    for d in detections:
        cv2.rectangle(frame, (d.x1, d.y1), (d.x2, d.y2), GREEN, 2)
        cv2.putText(frame, f"{d.confidence:.2f}", (d.x1, d.y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1)
    status = f"people={len(detections)}  state={state_name}"
    cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN, 2)


def mock_calendar(scenario: int) -> CalendarProvider:
    """Scenario 1 books a fake meeting; scenario 2 leaves the calendar empty."""
    calendar = MockCalendar()
    if scenario == 1:
        start = datetime.now() + timedelta(seconds=5)
        calendar.add_meeting(
            Meeting("m1", ROOM_ID, "ahmet", start, start + timedelta(minutes=5))
        )
    return calendar


def google_calendar() -> CalendarProvider:
    """The room account's primary calendar, asked at most every 30 s."""
    service = build("calendar", "v3", credentials=get_credentials(SECRETS_DIR))
    return CachedCalendar(GoogleCalendar(service, {ROOM_ID: "primary"}))


def voice_prompter() -> Prompter:
    """Speaks the question through the speaker; the camera loop keeps running meanwhile."""
    return VoicePrompter(speak_in_background(piper_speaker(VOICE_MODEL)))


def build_runner(
    calendar: CalendarProvider,
    notifier: Notifier | None = None,
    tolerance: timedelta | None = None,
    prompter: Prompter | None = None,
) -> RoomRunner:
    """`tolerance` None keeps the state machine's real default (10 min)."""
    options = {} if tolerance is None else {"tolerance": tolerance}
    machine = RoomStateMachine(ROOM_ID, dwell=timedelta(seconds=15), **options)
    return RoomRunner(
        ROOM_ID,
        calendar,
        notifier or MockNotifier(),
        prompter or MockPrompter(),
        machine=machine,
    )


def connect_slack(user_id: str, organizer: str) -> tuple[Notifier, str, str]:
    """Reads the tokens from .env; returns the notifier plus the two tokens."""
    load_dotenv()
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not bot_token or not app_token:
        sys.exit("SLACK_BOT_TOKEN or SLACK_APP_TOKEN is missing; check your .env file")
    # Whoever the calendar names as `organizer` is reached on your Slack account.
    notifier = SlackNotifier(WebClient(token=bot_token), user_ids={organizer: user_id})
    return notifier, bot_token, app_token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one room against a live RTSP stream.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="RTSP stream address")
    parser.add_argument("--scenario", type=int, choices=[1, 2], default=1)
    parser.add_argument(
        "--slack", metavar="MEMBER_ID",
        help="send real Slack DMs to this member and listen for their button clicks",
    )
    parser.add_argument(
        "--google", action="store_true",
        help="use the room's real Google Calendar instead of the fake one (ignores --scenario)",
    )
    parser.add_argument(
        "--organizer", metavar="EMAIL",
        help="with --google --slack: the organizer's e-mail whose messages come to you",
    )
    parser.add_argument(
        "--voice", action="store_true",
        help="say the reservation question out loud (Piper) instead of printing it",
    )
    parser.add_argument(
        "--tolerance-seconds", type=int, metavar="N",
        help="how long to wait for the organizer (default: 20 with the fake calendar, "
        "the real 10 minutes with --google)",
    )
    args = parser.parse_args()
    if args.google and args.slack and not args.organizer:
        parser.error("--google with --slack needs --organizer <e-mail>")
    return args


async def main() -> None:
    args = parse_args()
    url = args.url
    capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        sys.exit(f"Could not open stream: {url}")
    detector = PersonDetector()

    if args.google:
        calendar = google_calendar()
    else:
        calendar = mock_calendar(args.scenario)
    if args.tolerance_seconds is not None:
        tolerance = timedelta(seconds=args.tolerance_seconds)
    else:
        tolerance = None if args.google else timedelta(seconds=20)

    prompter = voice_prompter() if args.voice else None

    socket = None
    if args.slack:
        organizer = args.organizer or "ahmet"  # "ahmet" is the fake calendar's organizer
        notifier, bot_token, app_token = connect_slack(args.slack, organizer)
        runner = build_runner(calendar, notifier, tolerance, prompter)
        # Clicks arrive on Bolt's thread and land in the runner's mailbox.
        socket = start_click_listener(
            bot_token, app_token, make_click_handler(ROOM_ID, runner.submit)
        )
        print("Slack listener connected")
    else:
        runner = build_runner(calendar, tolerance=tolerance, prompter=prompter)

    last_state = None
    try:
        while True:
            result = await asyncio.to_thread(read_and_detect, capture, detector)
            if result is None:
                sys.exit("Lost the stream")
            frame, detections = result
            count = len(detections)
            runner.advance(datetime.now(), count)
            state = runner.machine.state
            if state != last_state:
                print(f"{datetime.now():%H:%M:%S} state={state.name} people={count}")
                last_state = state

            draw_overlay(frame, detections, state.name)
            cv2.imshow("ghost-meeting debug", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        if socket is not None:
            socket.close()
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
