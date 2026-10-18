"""Manual check: python scripts/count_people_in_image.py <image path>"""

import sys

import cv2

from ghost_meeting.vision.detector import PersonDetector


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/count_people_in_image.py <image path>")
    image = cv2.imread(sys.argv[1])
    if image is None:
        sys.exit(f"Could not read image: {sys.argv[1]}")
    detector = PersonDetector()
    print(f"People found: {detector.count_people(image)}")


if __name__ == "__main__":
    main()
