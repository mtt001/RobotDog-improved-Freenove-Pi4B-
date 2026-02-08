#!/usr/bin/env python3
"""
Mac AI WebRTC Client (Subscriber + Motion Authority)
Description:
    - Subscribes to SFU WebRTC video (WHEP-style SDP exchange)
    - Receives frames in Python for AI processing hook
    - Opens DataChannel to authority gateway and can send motion commands
Usage:
    python3 mac_ai_webrtc_client.py \
      --whep-url http://192.168.0.198:8889/robotdog/whep \
      --gateway-url http://192.168.0.198:8787 \
      --authority-token mac-ai-authority
Version:
    2026.02.07-1
Revision History:
    2026-02-07 - Initial version.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription


async def connect_video(whep_url: str):
    pc = RTCPeerConnection()
    pc.addTransceiver("video", direction="recvonly")

    @pc.on("track")
    def on_track(track):
        if track.kind != "video":
            return

        async def reader():
            frames = 0
            t0 = time.time()
            while True:
                frame = await track.recv()
                frames += 1
                # Hook for YOLO/OpenCV inference:
                # img_bgr = frame.to_ndarray(format="bgr24")
                # run_model(img_bgr)
                if time.time() - t0 >= 1.0:
                    print(f"[VIDEO] fps={frames:.1f} size={frame.width}x{frame.height}")
                    frames = 0
                    t0 = time.time()

        asyncio.create_task(reader())

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            whep_url,
            data=pc.localDescription.sdp,
            headers={"Content-Type": "application/sdp"},
        ) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"WHEP subscribe failed: {resp.status} {await resp.text()}")
            answer_sdp = await resp.text()

    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer_sdp, type="answer"))
    return pc


async def connect_control(gateway_url: str, authority_token: str):
    pc = RTCPeerConnection()
    dc = pc.createDataChannel("control")

    @dc.on("open")
    def on_open():
        print("[CTRL] DataChannel open")

    @dc.on("message")
    def on_message(msg):
        print(f"[CTRL] {msg}")

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    payload = {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "peer_id": f"mac-ai-{int(time.time())}",
        "token": authority_token,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{gateway_url}/offer", json=payload) as resp:
            data = await resp.json()

    await pc.setRemoteDescription(RTCSessionDescription(sdp=data["sdp"], type=data["type"]))
    return pc, dc


async def ai_command_loop(dc):
    # Replace with policy output from your planner/controller.
    # This sends stop-heartbeat and sample turn command as placeholder.
    while True:
        await asyncio.sleep(1.0)
        if dc.readyState == "open":
            dc.send(json.dumps({"type": "cmd", "cmd": "CMD_MOVE_STOP#0"}))


async def main_async():
    parser = argparse.ArgumentParser(description="Mac AI WebRTC client")
    parser.add_argument("--whep-url", default="http://192.168.0.198:8889/robotdog/whep")
    parser.add_argument("--gateway-url", default="http://192.168.0.198:8787")
    parser.add_argument("--authority-token", default="mac-ai-authority")
    args = parser.parse_args()

    vpc = await connect_video(args.whep_url)
    cpc, dc = await connect_control(args.gateway_url, args.authority_token)
    cmd_task = asyncio.create_task(ai_command_loop(dc))

    print("[READY] video+control connected")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        cmd_task.cancel()
        await vpc.close()
        await cpc.close()


if __name__ == "__main__":
    asyncio.run(main_async())
