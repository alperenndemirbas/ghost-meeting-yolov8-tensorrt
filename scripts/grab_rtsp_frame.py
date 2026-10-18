"""Manual check: python scripts/grab_rtsp_frame.py [rtsp url] [output path]"""

import sys

import cv2

DEFAULT_URL = "rtsp://localhost:8554/room1"
DEFAULT_OUTPUT = "frame.jpg"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    output = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        sys.exit(f"Could not open stream: {url}")
    ok, frame = capture.read()
    capture.release()
    if not ok:
        sys.exit("Stream opened but no frame was received")
    cv2.imwrite(output, frame)
    height, width = frame.shape[:2]
    print(f"Saved {width}x{height} frame to {output}")


if __name__ == "__main__":
    main()
