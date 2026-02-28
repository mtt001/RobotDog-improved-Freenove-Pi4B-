#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/line_messaging_api.py
Version: v1.0 (2026-02-26 10:04)
Revision History:
- 2026-02-26 10:04 v1.0 - Added LINE Messaging API helper for token validation and message send (push/broadcast) with optional .env loading and dry-run mode.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

LINE_API = "https://api.line.me"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LINE Messaging API sender for DigitalTwin status notifications")
    p.add_argument("--env-file", default="", help="Optional env file path (KEY=VALUE lines)")
    p.add_argument("--token", default="", help="LINE channel access token (fallback to LINE_CHANNEL_ACCESS_TOKEN)")
    p.add_argument("--to", default="", help="LINE target userId/groupId/roomId (fallback to LINE_TO)")
    p.add_argument("--text", default="DigitalTwin status: verification complete.", help="Message text")
    p.add_argument("--broadcast", action="store_true", help="Use broadcast endpoint instead of push")
    p.add_argument("--validate-only", action="store_true", help="Validate token via /v2/bot/info without sending")
    p.add_argument("--dry-run", action="store_true", help="Print request payload only, do not call LINE API")
    return p.parse_args()


def load_env_file(path: str) -> None:
    if not path:
        return
    env_path = Path(path).expanduser().resolve()
    if not env_path.exists():
        raise FileNotFoundError(f"env file not found: {env_path}")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def api_request(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, str]:
    url = f"{LINE_API}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.getcode() or 0), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), body


def main() -> int:
    args = parse_args()

    try:
        load_env_file(args.env_file)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    token = args.token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    to = args.to or os.getenv("LINE_TO", "")

    if args.validate_only:
        if not token:
            print("ERROR: missing token. Provide --token or LINE_CHANNEL_ACCESS_TOKEN.")
            return 2
        if args.dry_run:
            print("DRY-RUN validate: GET /v2/bot/info")
            return 0
        code, body = api_request("GET", "/v2/bot/info", token, None)
        print(f"HTTP {code}")
        print(body if body else "{}")
        return 0 if 200 <= code < 300 else 1

    payload = {"messages": [{"type": "text", "text": args.text}]}
    if not args.broadcast:
        if not to:
            print("ERROR: missing recipient. Provide --to or LINE_TO, or use --broadcast.")
            return 2
        payload["to"] = to
        endpoint = "/v2/bot/message/push"
    else:
        endpoint = "/v2/bot/message/broadcast"

    if not token and not args.dry_run:
        print("ERROR: missing token. Provide --token or LINE_CHANNEL_ACCESS_TOKEN.")
        return 2

    print(f"Mode: {'broadcast' if args.broadcast else 'push'}")
    print(f"Endpoint: {endpoint}")
    print("Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.dry_run:
        print("DRY-RUN: no API call sent")
        return 0

    code, body = api_request("POST", endpoint, token, payload)
    print(f"HTTP {code}")
    print(body if body else "{}")
    return 0 if 200 <= code < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
