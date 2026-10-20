"""Finds people in a single image with YOLO.

Knows nothing about cameras, rooms or time: image in, detections out.
"""

from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

PERSON_CLASS_ID = 0  # in the COCO dataset YOLO was trained on, class 0 is "person"


@dataclass(frozen=True)
class Detection:
    """One person: a rectangle in pixel coordinates plus how sure YOLO is (0..1)."""

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


class PersonDetector:
    def __init__(self, model_path: str = "yolov8n.pt", min_confidence: float = 0.4) -> None:
        self._model = YOLO(model_path)
        self._min_confidence = min_confidence

    def detect_people(self, image: np.ndarray) -> list[Detection]:
        """`image` is a BGR array of shape (height, width, 3), as OpenCV produces."""
        results = self._model(
            image,
            classes=[PERSON_CLASS_ID],
            conf=self._min_confidence,
            verbose=False,
        )
        detections = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            detections.append(Detection(x1, y1, x2, y2, float(box.conf[0])))
        return detections

    def count_people(self, image: np.ndarray) -> int:
        return len(self.detect_people(image))
