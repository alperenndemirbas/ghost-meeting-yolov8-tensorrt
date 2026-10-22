"""Live demo: python scripts/run_room.py [rtsp url] [--scenario 1|2]  (press q to stop)

Scenario 1 (default): a fake meeting starts in 5 seconds with a 20 second tolerance.
Stay out of the camera's view and the MockNotifier complains about 25 seconds from now.
Scenario 2: no meeting is booked. Walk into view and stay for 15 seconds, and the
MockPrompter asks whether to reserve the room.
A debug window shows what the camera sees, with boxes around detected people.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta

import cv2
import numpy as np

from ghost_meeting.adapters.mock import MockCalendar, MockNotifier, MockPrompter
from ghost_meeting.core.ports import Meeting
from ghost_meeting.core.state_machine import RoomStateMachine
from ghost_meeting.runner import RoomRunner
from ghost_meeting.vision.detector import Detection, PersonDetector

DEFAULT_URL = "rtsp://localhost:8554/room1"
ROOM_ID = "room1"


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


def build_runner(scenario: int) -> RoomRunner:
    """Scenario 1 books a fake meeting; scenario 2 leaves the calendar empty."""
    calendar = MockCalendar()
    if scenario == 1:
        start = datetime.now() + timedelta(seconds=5)
        calendar.add_meeting(
            Meeting("m1", ROOM_ID, "ahmet", start, start + timedelta(minutes=5))
        )
    machine = RoomStateMachine(
        ROOM_ID, tolerance=timedelta(seconds=20), dwell=timedelta(seconds=15)
    )
    return RoomRunner(ROOM_ID, calendar, MockNotifier(), MockPrompter(), machine=machine)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one room against a live RTSP stream.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="RTSP stream address")
    parser.add_argument("--scenario", type=int, choices=[1, 2], default=1)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    url = args.url
    capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        sys.exit(f"Could not open stream: {url}")
    detector = PersonDetector()

    runner = build_runner(args.scenario)

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
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
