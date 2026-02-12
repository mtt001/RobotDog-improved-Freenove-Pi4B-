#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Viewer Static Server
 File   : static_viewer_server.py
 Author : pi (admin) + Codex

 Serves /Server/web assets with explicit cache policy:
 - HTML: no-store (avoid stale UI during active development)
 - JS/CSS: short cache
 - Others: moderate cache

Version
v1.1 (2026-02-09 19:01)

Revision History
v1.1 (2026-02-09 19:01) : Avoid duplicate Cache-Control headers by using a per-request cache override for /health.
v1.0 (2026-02-09 18:55) : Initial custom static server with cache headers and /health endpoint.
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class ViewerHandler(SimpleHTTPRequestHandler):
    server_version = "RobotDogViewer/1.0"

    def do_GET(self):
        if self.path == "/health":
            self._cache_override = "no-store"
            payload = {"ok": True, "service": "robot-viewer", "ts": time.time()}
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            self._cache_override = None
            return
        super().do_GET()

    def end_headers(self):
        cache = getattr(self, "_cache_override", None)
        if cache is None:
            path = self.path.split("?", 1)[0].lower()
            if path.endswith(".html") or path == "/" or path == "":
                cache = "no-store"
            elif path.endswith(".js") or path.endswith(".css"):
                cache = "public, max-age=60"
            else:
                cache = "public, max-age=300"
        self.send_header("Cache-Control", cache)
        super().end_headers()

    def log_message(self, fmt, *args):
        return


def main():
    p = argparse.ArgumentParser(description="Robot Dog static viewer server")
    p.add_argument("--listen", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--directory", default=os.path.dirname(os.path.abspath(__file__)))
    args = p.parse_args()

    os.chdir(args.directory)
    server = ThreadingHTTPServer((args.listen, args.port), ViewerHandler)
    print(f"[viewer-static] serving {args.directory} on {args.listen}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
