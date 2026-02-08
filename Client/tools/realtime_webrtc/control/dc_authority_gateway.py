#!/usr/bin/env python3
"""
WebRTC DataChannel Authority Gateway
Description:
    Accepts WebRTC peers for command/telemetry DataChannel.
    Enforces motion authority (Mac AI role) and forwards allowed commands to Pi TCP control port.
Usage:
    python3 dc_authority_gateway.py --pi-host 192.168.0.32 --pi-port 5001 --listen 0.0.0.0 --http-port 8787
Version:
    2026.02.07-1
Revision History:
    2026-02-07 - Initial version.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import time
from typing import Dict

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

MOTION_CMDS = {
    "CMD_MOVE_FORWARD",
    "CMD_MOVE_BACKWARD",
    "CMD_MOVE_LEFT",
    "CMD_MOVE_RIGHT",
    "CMD_TURN_LEFT",
    "CMD_TURN_RIGHT",
    "CMD_MOVE_STOP",
    "CMD_RELAX",
    "CMD_STOP_PWM",
}


class PiBridge:
    def __init__(self, host: str, port: int, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: str) -> None:
        if not command.endswith("\n"):
            command += "\n"
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.settimeout(self.timeout)
            s.sendall(command.encode("utf-8"))

    def query_line(self, command: str) -> str:
        if not command.endswith("\n"):
            command += "\n"
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.settimeout(self.timeout)
            s.sendall(command.encode("utf-8"))
            return s.recv(2048).decode("utf-8", errors="ignore").strip()


class GatewayState:
    def __init__(self, bridge: PiBridge, authority_token: str):
        self.bridge = bridge
        self.authority_token = authority_token
        self.pcs = set()
        self.channels: Dict[str, object] = {}
        self.authority_peer_id: str | None = None
        self.telemetry_task: asyncio.Task | None = None

    def _is_authority(self, peer_id: str) -> bool:
        return self.authority_peer_id == peer_id

    async def broadcast(self, msg: dict):
        dead = []
        text = json.dumps(msg)
        for pid, ch in self.channels.items():
            try:
                ch.send(text)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.channels.pop(pid, None)
            if self.authority_peer_id == pid:
                self.authority_peer_id = None

    async def telemetry_loop(self):
        while True:
            await asyncio.sleep(0.2)
            try:
                p = await asyncio.to_thread(self.bridge.query_line, "CMD_POWER")
                d = await asyncio.to_thread(self.bridge.query_line, "CMD_SONIC")
                msg = {
                    "type": "telemetry",
                    "ts": time.time(),
                    "power_raw": p,
                    "range_raw": d,
                    "authority_peer_id": self.authority_peer_id,
                }
                await self.broadcast(msg)
            except Exception as e:
                await self.broadcast({"type": "telemetry_error", "error": str(e), "ts": time.time()})


async def create_app(state: GatewayState):
    app = web.Application()

    async def health(_):
        return web.json_response(
            {
                "ok": True,
                "authority_peer_id": state.authority_peer_id,
                "peers": len(state.channels),
                "ts": time.time(),
            }
        )

    async def offer(request: web.Request):
        payload = await request.json()
        peer_id = str(payload.get("peer_id") or f"peer-{int(time.time()*1000)}")
        token = str(payload.get("token") or "")

        pc = RTCPeerConnection()
        state.pcs.add(pc)

        @pc.on("datachannel")
        def on_datachannel(channel):
            state.channels[peer_id] = channel

            if token and token == state.authority_token:
                state.authority_peer_id = peer_id

            channel.send(
                json.dumps(
                    {
                        "type": "hello",
                        "peer_id": peer_id,
                        "authority": state._is_authority(peer_id),
                        "ts": time.time(),
                    }
                )
            )

            @channel.on("message")
            def on_message(message):
                try:
                    data = json.loads(message)
                except Exception:
                    return
                if data.get("type") != "cmd":
                    return
                cmd = str(data.get("cmd", "")).strip()
                cmd0 = cmd.split("#", 1)[0]
                if cmd0 not in MOTION_CMDS:
                    return
                if not state._is_authority(peer_id):
                    channel.send(json.dumps({"type": "reject", "reason": "not_authority", "cmd": cmd}))
                    return
                try:
                    state.bridge.send(cmd)
                    channel.send(json.dumps({"type": "ack", "cmd": cmd, "ts": time.time()}))
                except Exception as e:
                    channel.send(json.dumps({"type": "error", "cmd": cmd, "error": str(e)}))

            @channel.on("close")
            def on_close():
                state.channels.pop(peer_id, None)
                if state.authority_peer_id == peer_id:
                    state.authority_peer_id = None

        offer_sdp = RTCSessionDescription(sdp=payload["sdp"], type=payload["type"])
        await pc.setRemoteDescription(offer_sdp)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.json_response(
            {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "peer_id": peer_id,
                "authority": state._is_authority(peer_id),
            }
        )

    async def on_shutdown(_app):
        coros = [pc.close() for pc in list(state.pcs)]
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    app.router.add_get("/healthz", health)
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)
    return app


async def main_async():
    parser = argparse.ArgumentParser(description="WebRTC DataChannel authority gateway")
    parser.add_argument("--pi-host", default="192.168.0.32")
    parser.add_argument("--pi-port", type=int, default=5001)
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--http-port", type=int, default=8787)
    parser.add_argument("--authority-token", default="mac-ai-authority")
    args = parser.parse_args()

    state = GatewayState(PiBridge(args.pi_host, args.pi_port), args.authority_token)
    state.telemetry_task = asyncio.create_task(state.telemetry_loop())

    app = await create_app(state)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, args.listen, args.http_port)
    await site.start()

    print(f"DataChannel gateway listening on http://{args.listen}:{args.http_port}")
    print(f"Authority token: {args.authority_token}")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main_async())
