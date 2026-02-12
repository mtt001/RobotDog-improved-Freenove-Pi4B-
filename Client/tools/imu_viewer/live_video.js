/*
Live Video Selector
Description:
  Prefer H264 HLS when available/playable, otherwise fallback to MJPEG.
Version:
  2026.02.12-14
Revision History:
  2026-02-12 17:33 - Added automatic WebRTC renegotiation hook on `robotdog-video-profile-applied` event so resolution profile changes become visible without manual Safari refresh.
  2026-02-12 17:07 - Ensured Live View title always shows resolution (`WxH`) by using `/video/status` fallback dimensions/profile when browser media metadata is not yet available.
  2026-02-12 12:50 - Upgraded top-left client overlay line to show device + client IP + current FPS + heartbeat age (e.g. `Client: Mac Safari 192.168.0.x | 29.9fps | 6.2s`) using viewer-heartbeat ack metadata.
  2026-02-12 11:32 - Added viewer heartbeat emitter (`/viewer/heartbeat`) with best-effort device/browser hints (UA-CH when available, GPU renderer, screen/viewport/activity) to support Pi-side active viewer/operator summary (`/viewer/summary`).
  2026-02-12 11:23 - Added best-effort browser device classification (Mac/iPhone/iPad Safari family) and rendered it in live header label (`Client: ...`) beside stream title/FPS.
  2026-02-12 10:07 - Fix Safari/Pi power-cycle auto-recovery by resetting WebRTC session on failed/disconnected/closed states and allowing probe-driven renegotiation.
  2026-02-11 11:12 - Disabled MJPEG UI fallback path in `/color`; now prefer WebRTC, then HLS, else show explicit no-stream status without broken MJPEG image placeholder.
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
  const clientDeviceEl = document.getElementById("live-client-device");
  if (!videoEl || !imgEl || !rtcEl) {
    return;
  }

  let currentMode = "";
  let h264FrameCount = 0;
  let h264FpsT0 = performance.now();
  let webrtcPc = null;
  let titleWidth = 0;
  let titleHeight = 0;
  let fallbackWidth = 960;
  let fallbackHeight = 540;
  let titleFps = 0;
  let webrtcRetryAtMs = 0;
  let webrtcConnecting = false;
  let viewerHints = {};
  let viewerGpuRenderer = "";
  let lastInteractionMs = Date.now();
  let viewerClientIp = "";
  let viewerHeartbeatLastOkMs = 0;
  let viewerDeviceLabel = "Web Browser";
  const viewerId = (() => {
    const key = "robotdog_viewer_id_v1";
    try {
      let v = localStorage.getItem(key);
      if (!v) {
        v = (typeof crypto !== "undefined" && crypto.randomUUID)
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        localStorage.setItem(key, v);
      }
      return v;
    } catch (_) {
      return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
  })();

  function detectClientDeviceLabel() {
    const ua = String(navigator.userAgent || "");
    const platform = String(navigator.platform || "");
    const maxTouch = Number(navigator.maxTouchPoints || 0);
    if (/iPhone/i.test(ua)) {
      return "Client: iPhone Safari";
    }
    if (/iPad/i.test(ua) || (platform === "MacIntel" && maxTouch > 1)) {
      return "Client: iPad Safari";
    }
    if (/Macintosh|Mac OS X/i.test(ua)) {
      return "Client: Mac Safari";
    }
    if (/Android/i.test(ua)) {
      return "Client: Android Browser";
    }
    return "Client: Web Browser";
  }

  function detectClientDeviceShortLabel() {
    return detectClientDeviceLabel().replace(/^Client:\s*/, "").trim();
  }

  function renderClientOverlay() {
    if (!clientDeviceEl) return;
    const fps = Number.isFinite(titleFps) ? titleFps.toFixed(1) : "0.0";
    const ageSec = viewerHeartbeatLastOkMs > 0
      ? ((Date.now() - viewerHeartbeatLastOkMs) / 1000).toFixed(1)
      : "--";
    const ip = viewerClientIp || "-";
    const label = viewerDeviceLabel || detectClientDeviceShortLabel();
    clientDeviceEl.textContent = `Client: ${label} ${ip} | ${fps}fps | ${ageSec}s`;
  }

  function detectGpuRenderer() {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) return "";
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      if (ext) {
        return String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || "");
      }
      return String(gl.getParameter(gl.RENDERER) || "");
    } catch (_) {
      return "";
    }
  }

  async function collectViewerHints() {
    const out = {};
    try {
      const uad = navigator.userAgentData;
      if (uad && typeof uad.getHighEntropyValues === "function") {
        const high = await uad.getHighEntropyValues([
          "platform",
          "platformVersion",
          "model",
          "architecture",
          "bitness",
          "uaFullVersion",
        ]);
        Object.assign(out, high || {});
      }
    } catch (_) {}
    return out;
  }

  async function sendViewerHeartbeat() {
    try {
      const payload = {
        viewer_id: viewerId,
        device_label: detectClientDeviceShortLabel(),
        user_agent: navigator.userAgent || "",
        platform: navigator.platform || "",
        language: navigator.language || "",
        timezone: (Intl.DateTimeFormat().resolvedOptions() || {}).timeZone || "",
        page_path: window.location.pathname || "",
        stream_mode: currentMode || "",
        fps: Number.isFinite(titleFps) ? Number(titleFps) : 0,
        is_visible: document.visibilityState === "visible",
        active_recent_ms: Math.max(0, Date.now() - lastInteractionMs),
        screen_w: Number(window.screen?.width || 0),
        screen_h: Number(window.screen?.height || 0),
        viewport_w: Number(window.innerWidth || 0),
        viewport_h: Number(window.innerHeight || 0),
        dpr: Number(window.devicePixelRatio || 1),
        gpu_renderer: viewerGpuRenderer || "",
        hints: viewerHints || {},
      };
      const res = await fetch("/viewer/heartbeat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      });
      const data = await res.json().catch(() => ({}));
      const ack = data?.ack || {};
      viewerClientIp = String(ack.client_ip || viewerClientIp || "");
      viewerDeviceLabel = String(ack.device_label || payload.device_label || viewerDeviceLabel);
      viewerHeartbeatLastOkMs = Date.now();
      renderClientOverlay();
    } catch (_) {}
  }

  async function stopWebrtcPc() {
    webrtcConnecting = false;
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
    renderClientOverlay();
    window.dispatchEvent(
      new CustomEvent("live-video-fps", {
        detail: { fps: v, mode: currentMode || "unknown" },
      }),
    );
  }

  viewerDeviceLabel = detectClientDeviceShortLabel();
  if (clientDeviceEl) renderClientOverlay();
  viewerGpuRenderer = detectGpuRenderer();
  collectViewerHints().then((h) => {
    viewerHints = h || {};
  });
  const markInteraction = () => {
    lastInteractionMs = Date.now();
  };
  window.addEventListener("pointerdown", markInteraction, { passive: true });
  window.addEventListener("keydown", markInteraction);
  window.addEventListener("touchstart", markInteraction, { passive: true });
  document.addEventListener("visibilitychange", () => {
    sendViewerHeartbeat();
  });
  sendViewerHeartbeat();
  setInterval(sendViewerHeartbeat, 5000);
  setInterval(renderClientOverlay, 1000);

  function setLiveTitle(width, height) {
    if (!titleEl) return;
    const w0 = Number(width) || 0;
    const h0 = Number(height) || 0;
    const w = w0 > 0 ? w0 : fallbackWidth;
    const h = h0 > 0 ? h0 : fallbackHeight;
    titleWidth = w;
    titleHeight = h;
    const fpsText = `${titleFps.toFixed(1)} fps`;
    if (w > 0 && h > 0) {
      titleEl.textContent = `Live View ${w}x${h}, ${fpsText}`;
    } else {
      titleEl.textContent = `Live View, ${fpsText}`;
    }
  }

  function updateFallbackResolutionFromStatus(statusPayload) {
    const h264 = statusPayload?.h264 || {};
    let w = Number(h264.width) || 0;
    let h = Number(h264.height) || 0;
    if (!(w > 0 && h > 0)) {
      const profile = String(h264.profile || "");
      const m = profile.match(/^(\d+)x(\d+)$/);
      if (m) {
        w = Number(m[1]) || 0;
        h = Number(m[2]) || 0;
      }
    }
    if (w > 0 && h > 0) {
      fallbackWidth = w;
      fallbackHeight = h;
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
    const now = Date.now();
    if (webrtcConnecting && now < webrtcRetryAtMs) {
      return;
    }
    if (currentMode === "webrtc" && webrtcPc && webrtcPc.connectionState === "connected") {
      return;
    }
    webrtcConnecting = true;
    webrtcRetryAtMs = now + 1200;
    await stopWebrtcPc();
    webrtcConnecting = true;
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
    pc.onconnectionstatechange = () => {
      const st = pc.connectionState;
      if (st === "connected") {
        webrtcRetryAtMs = 0;
        webrtcConnecting = false;
        _setText(statusEl, label);
        return;
      }
      if (st === "failed" || st === "disconnected" || st === "closed") {
        if (webrtcPc === pc) {
          stopWebrtcPc();
          currentMode = "";
          publishFps(0);
          webrtcRetryAtMs = Date.now() + 800;
        }
      }
    };
    pc.oniceconnectionstatechange = () => {
      const st = pc.iceConnectionState;
      if (st === "failed" || st === "disconnected" || st === "closed") {
        if (webrtcPc === pc) {
          stopWebrtcPc();
          currentMode = "";
          publishFps(0);
          webrtcRetryAtMs = Date.now() + 800;
        }
      }
    };
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
    webrtcConnecting = false;
    setLiveTitle(0, 0);
    _setText(statusEl, label);
    publishFps(0);
    h264FrameCount = 0;
    h264FpsT0 = performance.now();
    startVideoFpsProbe();
  }

  function useNoStream(reason, detail) {
    const label = detail || "Stream unavailable";
    if (currentMode === "nostream") {
      _setText(statusEl, reason ? `${label} | ${reason}` : label);
      return;
    }
    currentMode = "nostream";
    stopWebrtcPc();
    rtcEl.removeAttribute("src");
    rtcEl.style.display = "none";
    videoEl.pause();
    videoEl.removeAttribute("src");
    videoEl.load();
    videoEl.style.display = "none";
    imgEl.removeAttribute("src");
    imgEl.style.display = "none";
    _setText(statusEl, reason ? `${label} | ${reason}` : label);
    publishFps(0);
    setLiveTitle(0, 0);
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
        useNoStream("H264 blocked", "Stream: H.264 (HLS/MPEG-TS)");
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
      updateFallbackResolutionFromStatus(s);
      if (!(Number(titleWidth) > 0 && Number(titleHeight) > 0)) {
        setLiveTitle(0, 0);
      }
      const webrtcReady = !!(s?.webrtc?.enabled && s?.webrtc?.ready && s?.webrtc?.url);
      const nativeHls = !!videoEl.canPlayType("application/vnd.apple.mpegurl");
      const h264Ready = !!(s?.h264?.enabled && s?.h264?.ready && nativeHls);
      const webrtcLabel = s?.webrtc?.protocol
        ? `Stream: ${s?.webrtc?.method || "WebRTC"} (${s.webrtc.protocol})`
        : "Stream: WebRTC (RTP/UDP via SFU)";
      const h264Label = s?.h264?.protocol
        ? `Stream: ${s?.h264?.method || "H.264"} (${s.h264.protocol})`
        : "Stream: H.264 (HLS/MPEG-TS)";
      if (webrtcReady) {
        try {
          await useWebrtc(s.webrtc.url, webrtcLabel);
          return;
        } catch (e) {
          webrtcConnecting = false;
          webrtcRetryAtMs = Date.now() + 1500;
          // WebRTC failed at runtime; continue to HLS/MJPEG fallback chain.
        }
      }
      if (h264Ready) {
        useHls(s.h264.url || "/hls/stream.m3u8", h264Label);
        // H264 fps is measured client-side via requestVideoFrameCallback.
      } else {
        const err = s?.h264?.error ? s.h264.error.slice(0, 120) : "no playable WebRTC/HLS source";
        useNoStream(err, "Stream: WebRTC/H264 unavailable");
      }
    } catch (e) {
      useNoStream("proxy status unavailable", "Stream: WebRTC/H264 unavailable");
    }
  }

  function forceWebrtcRenegotiate(reason) {
    stopWebrtcPc();
    currentMode = "";
    publishFps(0);
    webrtcConnecting = false;
    webrtcRetryAtMs = 0;
    setTimeout(() => {
      probe();
    }, 120);
  }

  probe();
  setInterval(probe, 4000);
  window.addEventListener("robotdog-video-profile-applied", () => {
    forceWebrtcRenegotiate("video-profile-applied");
  });
}
