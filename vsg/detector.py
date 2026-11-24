"""Per-frame object detection with a pretrained torchvision Faster R-CNN (COCO)."""

from dataclasses import dataclass
from typing import List

import numpy as np
import torch
from torchvision.models.detection import (
    FasterRCNN_MobileNet_V3_Large_FPN_Weights,
    fasterrcnn_mobilenet_v3_large_fpn,
)


@dataclass
class Detection:
    box: tuple  # (x1, y1, x2, y2) in pixels
    label: str
    score: float


class Detector:
    def __init__(self, score_threshold: float = 0.6, device: str = None):
        weights = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
        self.categories = weights.meta["categories"]
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = fasterrcnn_mobilenet_v3_large_fpn(weights=weights).eval().to(self.device)
        self.score_threshold = score_threshold

    @torch.inference_mode()
    def __call__(self, frame: np.ndarray) -> List[Detection]:
        """Detect objects in an (H, W, 3) uint8 RGB frame."""
        x = torch.from_numpy(frame).permute(2, 0, 1).float().div_(255).to(self.device)
        out = self.model([x])[0]
        dets = []
        for box, label, score in zip(out["boxes"], out["labels"], out["scores"]):
            if score < self.score_threshold:
                continue
            dets.append(
                Detection(
                    box=tuple(round(v, 1) for v in box.tolist()),
                    label=self.categories[int(label)],
                    score=round(float(score), 3),
                )
            )
        return dets
