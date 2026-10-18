"""Scenario 1 demo: python scripts/run_room.py [rtsp url]  (Ctrl+C to stop)

A fake meeting starts in 5 seconds with a 20 second tolerance. Stay out of the
camera's view and the MockNotifier should complain about 25 seconds from now.
"""

import asyncio
import sys
from datetime import datetime, timedelta

import cv2

from ghost_meeting.adapters.mock import MockCalendar, MockNotifier
from ghost_meeting.core.ports import Meeting
from ghost_meeting.core.state_machine import RoomStateMachine
from ghost_meeting.runner import RoomRunner
from ghost_meeting.vision.detector import PersonDetector

DEFAULT_URL = "rtsp://localhost:8554/room1"
ROOM_ID = "room1"


def read_and_count(capture: cv2.VideoCapture, detector: PersonDetector) -> int | None:
    """Blocking: waits for one frame, then runs YOLO on it."""
    ok, frame = capture.read()
    if not ok:
        return None
    return detector.count_people(frame)


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        sys.exit(f"Could not open stream: {url}")
    detector = PersonDetector()

    start = datetime.now() + timedelta(seconds=5)
    calendar = MockCalendar()
    calendar.add_meeting(
        Meeting("m1", ROOM_ID, "ahmet", start, start + timedelta(minutes=5))
    )
    runner = RoomRunner(
        ROOM_ID,
        calendar,
        MockNotifier(),
        machine=RoomStateMachine(ROOM_ID, tolerance=timedelta(seconds=20)),
    )

    last_state = None
    try:
        while True:
            count = await asyncio.to_thread(read_and_count, capture, detector)
            if count is None:
                sys.exit("Lost the stream")
            runner.advance(datetime.now(), count)
            state = runner.machine.state
            if state != last_state:
                print(f"{datetime.now():%H:%M:%S} state={state.name} people={count}")
                last_state = state
    finally:
        capture.release()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
