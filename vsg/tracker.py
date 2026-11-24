"""Temporal object tracking across consecutive frames via greedy IoU matching."""

from typing import Dict, List

from vsg.detector import Detection


def iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


class IoUTracker:
    """Assigns persistent track IDs to detections.

    Each frame, detection/track pairs with the same label are matched greedily in
    descending IoU order. Unmatched detections start new tracks; tracks unseen for
    more than `max_age` frames are dropped.
    """

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 2):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.tracks: Dict[int, dict] = {}  # id -> {"box", "label", "age"}
        self._next_id = 1

    def update(self, detections: List[Detection]) -> List[int]:
        """Returns a track ID for each detection, in order."""
        pairs = []
        for tid, t in self.tracks.items():
            for di, d in enumerate(detections):
                if d.label == t["label"]:
                    score = iou(t["box"], d.box)
                    if score >= self.iou_threshold:
                        pairs.append((score, tid, di))
        pairs.sort(reverse=True)

        ids = [None] * len(detections)
        used_tracks = set()
        for _, tid, di in pairs:
            if tid in used_tracks or ids[di] is not None:
                continue
            ids[di] = tid
            used_tracks.add(tid)

        for di, d in enumerate(detections):
            if ids[di] is None:
                ids[di] = self._next_id
                self._next_id += 1
            self.tracks[ids[di]] = {"box": d.box, "label": d.label, "age": 0}

        for tid in list(self.tracks):
            if tid not in ids:
                self.tracks[tid]["age"] += 1
                if self.tracks[tid]["age"] > self.max_age:
                    del self.tracks[tid]
        return ids
