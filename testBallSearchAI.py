#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: testBallSearchAI.py
Project: Freenove Robot Dog - Client AI Vision Test
Purpose:
  - Connect to Pi video stream (port 8001) and telemetry (port 5001).
  - Send periodic frames to a vision model (OpenAI Responses API).
  - Overlay detected ball hints, center point, HSV, and (x,y) on the frame.
  - Provide a simple, standalone validation tool before integrating into mtDogMain.

Notes:
  - Requires OPENAI_API_KEY env var; optional OPENAI_VISION_MODEL (default gpt-4o-mini).
  - Network access is required for the model call; use small frame rate for latency control.
  - This is a debug tool; do not run concurrently with other clients using port 8001.

Author: MT Tsai, CODEX
Version: 0.1.0
Last Modified: 2025-11-13

Revision History:
  0.1.0  2025-11-13  Initial standalone AI vision test tool with overlays and telemetry.
"""

import base64
import json
import os
import re
import socket
import struct
import threading
import time
import urllib.request

import cv2
import numpy as np


HOST_FALLBACK = "192.168.0.32"
VIDEO_PORT = 8001
TELEM_PORT = 5001
TIMEOUT = 10
MAX_FRAME = 5_000_000

AI_INTERVAL_SEC = 1.5
OPENAI_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.6
THICK = 2


def load_host():
    ip_path = os.path.join(os.path.dirname(__file__), "IP.txt")
    try:
        with open(ip_path, "r", encoding="utf-8") as f:
            ip = f.read().strip()
            if ip:
                return ip
    except OSError:
        pass
    return HOST_FALLBACK


def recvall(sock, n: int) -> bytearray:
    buf = bytearray(n)
    mv = memoryview(buf)
    got = 0
    while got < n:
        r = sock.recv_into(mv[got:], n - got)
        if r == 0:
            raise ConnectionError("Socket closed while receiving data")
        got += r
    return buf


def read_len(sock) -> int:
    hdr4 = recvall(sock, 4)
    n32 = struct.unpack("<I", hdr4)[0]
    if 0 < n32 <= MAX_FRAME:
        return n32
    hdr8 = hdr4 + recvall(sock, 4)
    n64 = struct.unpack("<Q", hdr8)[0]
    if 0 < n64 <= MAX_FRAME:
        return n64
    raise ValueError(f"Invalid frame length (32={n32}, 64={n64})")


class TelemetryClient(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._stop = threading.Event()
        self.last_line = ""

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=TIMEOUT) as s:
                    s.settimeout(TIMEOUT)
                    buf = b""
                    while not self._stop.is_set():
                        chunk = s.recv(1024)
                        if not chunk:
                            break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            try:
                                self.last_line = line.decode("utf-8", errors="ignore").strip()
                            except Exception:
                                self.last_line = ""
            except OSError:
                time.sleep(1.0)


def encode_jpeg_b64(frame_bgr) -> str:
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise ValueError("Failed to encode JPEG")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _extract_json(text: str):
    if not text:
        return None
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def call_openai_for_ball(image_bgr):
    if not OPENAI_API_KEY:
        return None, "Missing OPENAI_API_KEY"
    image_b64 = encode_jpeg_b64(image_bgr)
    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Find a ball in the image. Return JSON only with keys: "
                            "found (bool), x (int), y (int), radius (int), confidence (0-1). "
                            "Coordinates are pixel positions in the image."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{image_b64}",
                    },
                ],
            }
        ],
        "max_output_tokens": 120,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        return None, f"API error: {exc}"

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None, "Bad JSON from API"

    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text = c.get("text")
                    break
            if text:
                break
    result = _extract_json(text or "")
    if not result:
        return None, "No JSON in response"
    return result, ""


def draw_overlay(frame, det, telem_line, status_text):
    h, w = frame.shape[:2]

    hsv = None
    if det and det.get("found"):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    cv2.putText(frame, f"{w}x{h}", (10, 22), FONT, FONT_SCALE, (0, 255, 255), THICK)
    if telem_line:
        cv2.putText(frame, telem_line, (10, 46), FONT, FONT_SCALE, (0, 200, 0), THICK)
    if status_text:
        cv2.putText(frame, status_text, (10, 70), FONT, FONT_SCALE, (0, 180, 255), THICK)

    if not det or not det.get("found"):
        return

    x = int(det.get("x", -1))
    y = int(det.get("y", -1))
    r = int(det.get("radius", 0))
    if x < 0 or y < 0 or r <= 0:
        return

    cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
    cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)

    cx = max(0, min(frame.shape[1] - 1, x))
    cy = max(0, min(frame.shape[0] - 1, y))
    h_val, s_val, v_val = hsv[cy, cx]
    text1 = f"HSV({int(h_val)},{int(s_val)},{int(v_val)})"
    text2 = f"(x,y)=({x},{y})"
    tx = min(x + 10, frame.shape[1] - 220)
    ty = min(y - 10, frame.shape[0] - 10)
    cv2.putText(frame, text1, (tx, ty), FONT, FONT_SCALE, (255, 255, 255), THICK)
    cv2.putText(frame, text2, (tx, ty + 22), FONT, FONT_SCALE, (255, 255, 255), THICK)


def main():
    host = load_host()
    telem = TelemetryClient(host, TELEM_PORT)
    telem.start()

    cv2.namedWindow("BallSearchAI", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("BallSearchAI", 960, 540)

    ai_last = 0.0
    det_last = None
    status = ""

    while True:
        try:
            with socket.create_connection((host, VIDEO_PORT), timeout=TIMEOUT) as sock:
                sock.settimeout(TIMEOUT)
                while True:
                    frame_len = read_len(sock)
                    jpg = recvall(sock, frame_len)
                    frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    now = time.time()
                    if now - ai_last >= AI_INTERVAL_SEC:
                        ai_last = now
                        det, err = call_openai_for_ball(frame)
                        if det:
                            det_last = det
                            status = f"AI ok (conf={det.get('confidence', 0):.2f})"
                        else:
                            status = err or "AI no result"

                    draw_overlay(frame, det_last, telem.last_line, status)
                    cv2.imshow("BallSearchAI", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q")):
                        raise KeyboardInterrupt
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(0.5)

    telem.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
