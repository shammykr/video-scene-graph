"""Serves the web viewer and analysis output over HTTP.

Usage: python -m vsg.server --out output --port 8000
  GET /             -> web/index.html (viewer)
  GET /api/graphs   -> output/graphs.json
  GET /frames/*.jpg -> analyzed frame images
"""

import argparse
import functools
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, out_dir: str, **kwargs):
        self.out_dir = out_dir
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def translate_path(self, path):
        path = path.split("?", 1)[0]
        if path == "/api/graphs":
            return os.path.join(self.out_dir, "graphs.json")
        if path.startswith("/frames/"):
            name = os.path.basename(path)  # no directory traversal
            return os.path.join(self.out_dir, "frames", name)
        return super().translate_path(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="output", help="directory written by vsg.pipeline")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    handler = functools.partial(Handler, out_dir=os.path.abspath(a.out))
    server = ThreadingHTTPServer((a.host, a.port), handler)
    print(f"serving viewer at http://{a.host}:{a.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
