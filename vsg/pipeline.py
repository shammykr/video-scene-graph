"""End-to-end analysis: decode -> detect -> track -> scene graph -> JSON + frame images.

Usage: python -m vsg.pipeline data/sample.mp4 --out output --stride 3
"""

import argparse
import json
import os
import time

import cv2
from networkx.readwrite import json_graph

from vsg.decode import frames
from vsg.detector import Detector
from vsg.scene_graph import build_scene_graph
from vsg.tracker import IoUTracker


def analyze(video: str, out_dir: str, stride: int = 1, max_frames: int = None,
            backend: str = "cpp", score_threshold: float = 0.6) -> dict:
    os.makedirs(os.path.join(out_dir, "frames"), exist_ok=True)
    detector = Detector(score_threshold=score_threshold)
    tracker = IoUTracker()
    records = []
    t0 = time.perf_counter()

    for idx, frame in frames(video, backend):
        if idx % stride:
            continue
        dets = detector(frame)
        ids = tracker.update(dets)
        graph = build_scene_graph(dets, ids)

        name = f"{idx:06d}.jpg"
        cv2.imwrite(os.path.join(out_dir, "frames", name), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 80])
        data = json_graph.node_link_data(graph, edges="edges")
        records.append({
            "index": idx,
            "image": f"frames/{name}",
            "nodes": data["nodes"],
            "edges": [{"source": e["source"], "target": e["target"], "relation": e["relation"]}
                      for e in data["edges"]],
        })
        if max_frames and len(records) >= max_frames:
            break

    elapsed = time.perf_counter() - t0
    result = {"video": os.path.basename(video), "stride": stride, "frames": records}
    with open(os.path.join(out_dir, "graphs.json"), "w") as f:
        json.dump(result, f)
    print(f"analyzed {len(records)} frames in {elapsed:.1f}s "
          f"({len(records) / elapsed:.1f} frames/s) -> {out_dir}/graphs.json")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("video")
    p.add_argument("--out", default="output")
    p.add_argument("--stride", type=int, default=1, help="analyze every Nth frame")
    p.add_argument("--max-frames", type=int)
    p.add_argument("--backend", choices=["cpp", "opencv"], default="cpp")
    p.add_argument("--threshold", type=float, default=0.6)
    a = p.parse_args()
    analyze(a.video, a.out, a.stride, a.max_frames, a.backend, a.threshold)


if __name__ == "__main__":
    main()
