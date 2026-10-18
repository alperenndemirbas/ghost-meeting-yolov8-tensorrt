"""Counts people in a single image with YOLO.

Knows nothing about cameras, rooms or time: image in, number out.
"""

import numpy as np
from ultralytics import YOLO

PERSON_CLASS_ID = 0  # in the COCO dataset YOLO was trained on, class 0 is "person"


class PersonDetector:
    def __init__(self, model_path: str = "yolov8n.pt", min_confidence: float = 0.4) -> None:
        self._model = YOLO(model_path)
        self._min_confidence = min_confidence

    def count_people(self, image: np.ndarray) -> int:
        """`image` is a BGR array of shape (height, width, 3), as OpenCV produces."""
        results = self._model(
            image,
            classes=[PERSON_CLASS_ID],
            conf=self._min_confidence,
            verbose=False,
        )
        return len(results[0].boxes)
