/*
Live Video Selector
Description:
  Prefer H264 HLS when available/playable, otherwise fallback to MJPEG.
Version:
  2026.02.07-7
Revision History:
  2026-02-07 18:45 - Fix title FPS reporting for WebRTC mode (not only H.264 mode).
  2026-02-07 18:41 - Live View title now includes real-time FPS (e.g., Live View 960x540, 21.5 fps).
  2026-02-07 17:04 - Replaced iframe path with true WebRTC WHEP negotiation (RTCPeerConnection).
  2026-02-07 16:38 - Added WebRTC/SFU-first rendering path with HLS and MJPEG fallback.
  2026-02-07 16:33 - Show stream resolution in Live View title (Live View WxH).
  2026-02-07 15:14 - Emit live-video FPS events for telemetry top-bar overlay.
  2026-02-07 14:52 - Overlay now shows explicit stream method/protocol labels.
  2026-02-07 14:46 - Initial add: H264 status probe with MJPEG fallback selection.
*/

function _setText(el, text) {
  if (el) {
    el.textContent = text;
  }
}

export function initLiveVideo() {
  const videoEl = document.getElementById("liveVideo");
  const imgEl = document.getElementById("liveMjpeg");
  const rtcEl = document.getElementById("liveWebrtc");
  const statusEl = document.getElementById("liveStatus");
  const titleEl = document.getElementById("liveTitle");
  if (!videoEl || !imgEl || !rtcEl) {
    return;
  }

  let currentMode = "";
  let h264FrameCount = 0;
  let h264FpsT0 = performance.now();
  let webrtcPc = null;
  let titleWidth = 0;
  let titleHeight = 0;
  let titleFps = 0;

  async function stopWebrtcPc() {
    if (webrtcPc) {
      try {
        webrtcPc.getSenders().forEach((s) => s.track && s.track.stop());
      } catch (_) {}
      try {
        webrtcPc.getReceivers().forEach((r) => r.track && r.track.stop());
      } catch (_) {}
      try {
        webrtcPc.close();
      } catch (_) {}
      webrtcPc = null;
    }
  }

  function publishFps(fps) {
    const v = Number.isFinite(fps) ? Math.max(0, fps) : 0;
    titleFps = v;
    setLiveTitle(titleWidth, titleHeight);
    window.dispatchEvent(
      new CustomEvent("live-video-fps", {
        detail: { fps: v, mode: currentMode || "unknown" },
      }),
    );
  }

  function setLiveTitle(width, height) {
    if (!titleEl) return;
    const w = Number(width) || 0;
    const h = Number(height) || 0;
    titleWidth = w;
    titleHeight = h;
    const fpsText = `${titleFps.toFixed(1)} fps`;
    if (w > 0 && h > 0) {
      titleEl.textContent = `Live View ${w}x${h}, ${fpsText}`;
    } else {
      titleEl.textContent = `Live View, ${fpsText}`;
    }
  }

  function startVideoFpsProbe() {
    if (!("requestVideoFrameCallback" in HTMLVideoElement.prototype)) {
      return;
    }
    const onFrame = (nowMs) => {
      if (currentMode !== "h264" && currentMode !== "webrtc") {
        return;
      }
      h264FrameCount += 1;
      const elapsed = nowMs - h264FpsT0;
      if (elapsed >= 1000) {
        publishFps((h264FrameCount * 1000) / elapsed);
        h264FrameCount = 0;
        h264FpsT0 = nowMs;
      }
      videoEl.requestVideoFrameCallback(onFrame);
    };
    videoEl.requestVideoFrameCallback(onFrame);
  }

  async function useWebrtc(url, detail) {
    const label = detail || "Stream: WebRTC (RTP/UDP via SFU)";
    if (currentMode === "webrtc" && webrtcPc) {
      return;
    }
    await stopWebrtcPc();
    currentMode = "webrtc";
    videoEl.pause();
    videoEl.removeAttribute("src");
    videoEl.srcObject = null;
    videoEl.load();
    imgEl.removeAttribute("src");
    videoEl.style.display = "none";
    imgEl.style.display = "none";
    rtcEl.style.display = "none";
    rtcEl.removeAttribute("src");
    videoEl.style.display = "block";
    const whepUrl = url.endsWith("/whep") ? url : `${url.replace(/\/$/, "")}/whep`;
    const pc = new RTCPeerConnection();
    webrtcPc = pc;
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.ontrack = (ev) => {
      const [stream] = ev.streams;
      if (stream) {
        videoEl.srcObject = stream;
      } else {
        const ms = new MediaStream([ev.track]);
        videoEl.srcObject = ms;
      }
      videoEl.play().catch(() => {});
      setLiveTitle(videoEl.videoWidth, videoEl.videoHeight);
    };
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    const resp = await fetch(whepUrl, {
      method: "POST",
      headers: { "Content-Type": "application/sdp" },
      body: pc.localDescription.sdp,
      cache: "no-store",
    });
    if (!resp.ok) {
      throw new Error(`WHEP POST failed: ${resp.status}`);
    }
    const answerSdp = await resp.text();
    await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
    setLiveTitle(0, 0);
    _setText(statusEl, label);
    publishFps(0);
    h264FrameCount = 0;
    h264FpsT0 = performance.now();
    startVideoFpsProbe();
  }

  function useMjpeg(reason, detail) {
    const label = detail || "Stream: Proprietary MJPEG (TCP bridge)";
    if (currentMode === "mjpeg") {
      if (!imgEl.src) {
        imgEl.src = `/video.mjpeg?ts=${Date.now()}`;
      }
      _setText(statusEl, reason ? `${label} | ${reason}` : label);
      return;
    }
    currentMode = "mjpeg";
    stopWebrtcPc();
    rtcEl.removeAttribute("src");
    rtcEl.style.display = "none";
    videoEl.pause();
    videoEl.removeAttribute("src");
    videoEl.load();
    videoEl.style.display = "none";
    imgEl.style.display = "block";
    imgEl.src = `/video.mjpeg?ts=${Date.now()}`;
    _setText(statusEl, reason ? `${label} | ${reason}` : label);
    publishFps(0);
  }

  function useHls(url, detail) {
    const label = detail || "Stream: H.264 (HLS/MPEG-TS)";
    if (currentMode === "h264" && videoEl.src.includes(url)) {
      return;
    }
    currentMode = "h264";
    stopWebrtcPc();
    rtcEl.removeAttribute("src");
    rtcEl.style.display = "none";
    imgEl.removeAttribute("src");
    imgEl.style.display = "none";
    videoEl.style.display = "block";
    videoEl.src = `${url}?ts=${Date.now()}`;
    videoEl
      .play()
      .then(() => {
        _setText(statusEl, label);
        h264FrameCount = 0;
        h264FpsT0 = performance.now();
        setLiveTitle(videoEl.videoWidth, videoEl.videoHeight);
        startVideoFpsProbe();
      })
      .catch(() => {
        useMjpeg("H264 blocked; fallback", "Stream: Proprietary MJPEG (TCP bridge)");
      });
  }

  videoEl.addEventListener("loadedmetadata", () => {
    setLiveTitle(videoEl.videoWidth, videoEl.videoHeight);
  });
  imgEl.addEventListener("load", () => {
    setLiveTitle(imgEl.naturalWidth, imgEl.naturalHeight);
  });

  async function probe() {
    try {
      const res = await fetch("/video/status", { cache: "no-store" });
      const s = await res.json();
      const webrtcReady = !!(s?.webrtc?.enabled && s?.webrtc?.ready && s?.webrtc?.url);
      const nativeHls = !!videoEl.canPlayType("application/vnd.apple.mpegurl");
      const h264Ready = !!(s?.h264?.enabled && s?.h264?.ready && nativeHls);
      const webrtcLabel = s?.webrtc?.protocol
        ? `Stream: ${s?.webrtc?.method || "WebRTC"} (${s.webrtc.protocol})`
        : "Stream: WebRTC (RTP/UDP via SFU)";
      const h264Label = s?.h264?.protocol
        ? `Stream: ${s?.h264?.method || "H.264"} (${s.h264.protocol})`
        : "Stream: H.264 (HLS/MPEG-TS)";
      const mjpegLabel = s?.mjpeg?.protocol
        ? `Stream: ${s?.mjpeg?.method || "Proprietary MJPEG"} (${s.mjpeg.protocol})`
        : "Stream: Proprietary MJPEG (TCP bridge)";
      if (webrtcReady) {
        try {
          await useWebrtc(s.webrtc.url, webrtcLabel);
          return;
        } catch (e) {
          // WebRTC failed at runtime; continue to HLS/MJPEG fallback chain.
        }
      }
      if (h264Ready) {
        useHls(s.h264.url || "/hls/stream.m3u8", h264Label);
        // H264 fps is measured client-side via requestVideoFrameCallback.
      } else {
        const err = s?.h264?.error ? ` (${s.h264.error.slice(0, 100)})` : "";
        useMjpeg(err ? `fallback${err}` : "", mjpegLabel);
        publishFps(Number(s?.mjpeg?.fps || 0));
      }
    } catch (e) {
      useMjpeg("proxy status unavailable", "Stream: Proprietary MJPEG (TCP bridge)");
    }
  }

  probe();
  setInterval(probe, 4000);
}
