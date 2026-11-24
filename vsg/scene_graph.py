"""Scene graph construction: objects are nodes, spatial relations are directed edges."""

from typing import List

import networkx as nx

from vsg.detector import Detection
from vsg.tracker import iou

OVERLAP_IOU = 0.1


def spatial_relations(a, b) -> List[str]:
    """Relations of box `a` with respect to box `b` (image coordinates, y grows downward)."""
    if iou(a, b) >= OVERLAP_IOU:
        return ["overlapping"]
    rels = []
    if a[3] <= b[1]:
        rels.append("above")
    elif a[1] >= b[3]:
        rels.append("below")
    if a[2] <= b[0]:
        rels.append("left-of")
    elif a[0] >= b[2]:
        rels.append("right-of")
    if not rels:
        # Boxes touch/overlap slightly without clear separation: use centre offsets.
        acx, acy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
        bcx, bcy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        dx, dy = acx - bcx, acy - bcy
        if abs(dx) >= abs(dy):
            rels.append("left-of" if dx < 0 else "right-of")
        else:
            rels.append("above" if dy < 0 else "below")
    return rels


def build_scene_graph(detections: List[Detection], track_ids: List[int]) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for d, tid in zip(detections, track_ids):
        g.add_node(tid, label=d.label, score=d.score, box=list(d.box))
    for d1, t1 in zip(detections, track_ids):
        for d2, t2 in zip(detections, track_ids):
            if t1 == t2:
                continue
            for rel in spatial_relations(d1.box, d2.box):
                if rel == "overlapping" and t1 > t2:
                    continue  # symmetric: store once
                g.add_edge(t1, t2, relation=rel)
    return g
