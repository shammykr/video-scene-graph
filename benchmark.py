"""Decoder benchmark: C++ (pybind11 + FFmpeg) vs pure-Python OpenCV.

Both paths decode every frame of the video to an (H, W, 3) uint8 RGB NumPy array
using their idiomatic API (fresh array per frame). Reports the best of N runs.

Usage: python benchmark.py data/sample.mp4 --runs 5
"""

import argparse
import platform
import time

import cv2

from vsg._framedecoder import FrameDecoder


def bench_cpp(path):
    n = 0
    t = time.perf_counter()
    for _ in FrameDecoder(path):
        n += 1
    return n, time.perf_counter() - t


def bench_opencv(path):
    cap = cv2.VideoCapture(path)
    n = 0
    t = time.perf_counter()
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        n += 1
    elapsed = time.perf_counter() - t
    cap.release()
    return n, elapsed


def best_fps(fn, path, runs):
    fn(path)  # warm-up (file cache, codec init)
    results = [fn(path) for _ in range(runs)]
    frames = results[0][0]
    return frames, max(n / dt for n, dt in results)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--runs", type=int, default=5)
    a = p.parse_args()

    d = FrameDecoder(a.video)
    print(f"video: {a.video} ({d.width}x{d.height}, {d.fps:g} fps, {d.frame_count} frames)")
    print(f"host:  {platform.machine()} {platform.platform()}, OpenCV {cv2.__version__}")

    n_cpp, cpp = best_fps(bench_cpp, a.video, a.runs)
    n_cv, ocv = best_fps(bench_opencv, a.video, a.runs)
    assert n_cpp == n_cv, f"frame count mismatch: cpp={n_cpp} opencv={n_cv}"

    print(f"\n{'decoder':<22}{'frames':>8}{'FPS':>10}")
    print(f"{'C++ (pybind11/FFmpeg)':<22}{n_cpp:>8}{cpp:>10.0f}")
    print(f"{'Python (OpenCV)':<22}{n_cv:>8}{ocv:>10.0f}")
    print(f"\nspeedup: {cpp / ocv:.2f}x")


if __name__ == "__main__":
    main()
