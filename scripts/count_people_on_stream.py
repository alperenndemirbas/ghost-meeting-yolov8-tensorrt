"""Manual check: python scripts/count_people_on_stream.py [rtsp url]  (Ctrl+C to stop)"""

import sys
import time

import cv2

from ghost_meeting.vision.detector import PersonDetector

DEFAULT_URL = "rtsp://localhost:8554/room1"
REPORT_EVERY_SECONDS = 5.0


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        sys.exit(f"Could not open stream: {url}")
    detector = PersonDetector()

    last_count = None
    frames = 0
    window_start = time.monotonic()
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                sys.exit("Lost the stream")
            count = detector.count_people(frame)
            frames += 1
            if count != last_count:
                print(f"People: {count}")
                last_count = count
            elapsed = time.monotonic() - window_start
            if elapsed >= REPORT_EVERY_SECONDS:
                print(f"  ({frames / elapsed:.1f} frames/s processed)")
                frames = 0
                window_start = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        capture.release()


if __name__ == "__main__":
    main()
