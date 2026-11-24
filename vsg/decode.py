"""Frame sources: the C++ FFmpeg decoder (default) and a pure-Python OpenCV fallback.

Both yield (frame_index, frame) where frame is an (H, W, 3) uint8 RGB array.
"""

from typing import Iterator, Tuple

import numpy as np

Frame = Tuple[int, np.ndarray]


def cpp_frames(path: str, threads: int = 0) -> Iterator[Frame]:
    from vsg._framedecoder import FrameDecoder

    for i, frame in enumerate(FrameDecoder(path, threads)):
        yield i, frame


def opencv_frames(path: str) -> Iterator[Frame]:
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    i = 0
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            yield i, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            i += 1
    finally:
        cap.release()


def frames(path: str, backend: str = "cpp") -> Iterator[Frame]:
    if backend == "cpp":
        return cpp_frames(path)
    if backend == "opencv":
        return opencv_frames(path)
    raise ValueError(f"unknown backend {backend!r}")
