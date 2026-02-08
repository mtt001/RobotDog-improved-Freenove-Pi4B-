/*
IMU Viewer Client (Color)
Description:
  Three.js color model viewer with IMU polling, diagnostics, and model load status.
Version:
  2026.02.07-5
Revision History:
  2026-02-07 15:14 - Added top-left telemetry line with video FPS overlay.
  2026-02-07 15:06 - Load live_video.js via safe dynamic import so IMU/telemetry still run if missing.
  2026-02-07 14:46 - Added live video auto-selection (H264-first, MJPEG fallback).
  2026-02-07 13:39 - Added live telemetry polling for power/range.
*/

import * as THREE from '/vendor/three/three.module.js';

const threeContainer = document.getElementById('three-container');
import { MTLLoader } from '/vendor/three/MTLLoader.js';
import { OBJLoader } from '/vendor/three/OBJLoader.js';

const statusEl = document.getElementById('status');
const diagEl = document.getElementById('diag');
const errEl = document.getElementById('err');
const modelStatusEl = document.getElementById('modelstatus');
const modelErrEl = document.getElementById('modelerr');
const versionEl = document.getElementById('version');
const versionTimeEl = document.getElementById('versiontime');
const powerEl = document.getElementById('power');
const rangeEl = document.getElementById('range');
const telemetryTopEl = document.getElementById('telemetryTop');
const rollEl = document.getElementById('roll');
const pitchEl = document.getElementById('pitch');
const yawEl = document.getElementById('yaw');
const lastOkEl = document.getElementById('lastok');
let latestBatteryText = '--';
let latestRangeText = '--';
let latestFps = 0;

function renderTopTelemetryLine() {
  if (!telemetryTopEl) return;
  const fpsText = `${latestFps.toFixed(1)}fps`;
  telemetryTopEl.textContent = `Power ${latestBatteryText}  Range ${latestRangeText}  ${fpsText}`;
}

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0e1116);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 2.6, 6);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio || 1);
if (threeContainer) {
  threeContainer.appendChild(renderer.domElement);
}

const ambient = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambient);

const dir = new THREE.DirectionalLight(0xffffff, 0.8);
dir.position.set(4, 6, 2);
scene.add(dir);

const grid = new THREE.GridHelper(10, 20, 0x233040, 0x1a222c);
scene.add(grid);

const dogGroup = new THREE.Group();
scene.add(dogGroup);

// Placeholder
const placeholder = new THREE.Group();
dogGroup.add(placeholder);

const bodyMat = new THREE.MeshStandardMaterial({ color: 0x7f8790, roughness: 0.6, metalness: 0.1 });
const headMat = new THREE.MeshStandardMaterial({ color: 0x6b7280, roughness: 0.5, metalness: 0.1 });
const legMat = new THREE.MeshStandardMaterial({ color: 0x3f444b, roughness: 0.7, metalness: 0.1 });

const body = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.6, 1.0), bodyMat);
body.position.y = 0.8;
placeholder.add(body);

const head = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.5, 0.5), headMat);
head.position.set(1.25, 1.0, 0);
placeholder.add(head);

const legGeom = new THREE.BoxGeometry(0.3, 0.7, 0.3);
const legPositions = [
  [-0.7, 0.35, -0.35],
  [-0.7, 0.35,  0.35],
  [ 0.7, 0.35, -0.35],
  [ 0.7, 0.35,  0.35],
];
for (const [x, y, z] of legPositions) {
  const leg = new THREE.Mesh(legGeom, legMat);
  leg.position.set(x, y, z);
  placeholder.add(leg);
}

camera.lookAt(0, 0.8, 0);

function resizeRenderer() {
  if (!threeContainer) return;
  const rect = threeContainer.getBoundingClientRect();
  const width = Math.max(10, rect.width);
  const height = Math.max(10, rect.height);
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
resizeRenderer();
if (window.ResizeObserver && threeContainer) {
  const ro = new ResizeObserver(() => resizeRenderer());
  ro.observe(threeContainer);
}

const mtlLoader = new MTLLoader();
mtlLoader.setPath('/assets/quaternius_pug/');
if (modelStatusEl) {
  modelStatusEl.textContent = 'loading MTL';
}
mtlLoader.load(
  'Pug.mtl',
  (materials) => {
    materials.preload();
    if (modelStatusEl) {
      modelStatusEl.textContent = 'loading OBJ';
    }
    const objLoader = new OBJLoader();
    objLoader.setMaterials(materials);
    objLoader.setPath('/assets/quaternius_pug/');
    objLoader.load(
      'Pug.obj',
      (obj) => {
        obj.rotation.x = -Math.PI / 2;
        let box = new THREE.Box3().setFromObject(obj);
        const center = new THREE.Vector3();
        box.getCenter(center);
        obj.position.sub(center);
        box = new THREE.Box3().setFromObject(obj);
        obj.position.y -= box.min.y;

        const size = new THREE.Vector3();
        box.getSize(size);
        const scale = 2.0 / Math.max(size.x, size.z);
        obj.scale.setScalar(scale);

        dogGroup.add(obj);
        placeholder.visible = false;
        if (modelStatusEl) {
          modelStatusEl.textContent = 'loaded';
        }
        if (modelErrEl) {
          modelErrEl.textContent = '--';
        }
      },
      (xhr) => {
        if (modelStatusEl && xhr?.total) {
          const pct = Math.round((xhr.loaded / xhr.total) * 100);
          modelStatusEl.textContent = `loading OBJ ${pct}%`;
        }
      },
      (err) => {
        placeholder.visible = true;
        if (modelStatusEl) {
          modelStatusEl.textContent = 'OBJ load failed';
        }
        if (modelErrEl) {
          modelErrEl.textContent = err?.message || 'failed to load Pug.obj';
        }
      }
    );
  },
  (xhr) => {
    if (modelStatusEl && xhr?.total) {
      const pct = Math.round((xhr.loaded / xhr.total) * 100);
      modelStatusEl.textContent = `loading MTL ${pct}%`;
    }
  },
  (err) => {
    placeholder.visible = true;
    if (modelStatusEl) {
      modelStatusEl.textContent = 'MTL load failed';
    }
    if (modelErrEl) {
      modelErrEl.textContent = err?.message || 'failed to load Pug.mtl';
    }
  }
);

const target = { roll: 0, pitch: 0, yaw: 0 };
const smooth = { roll: 0, pitch: 0, yaw: 0 };
const alpha = 0.15;
const offlineState = {
  consecutiveFailures: 0,
  lastOkMs: 0,
  lastPopupMs: 0,
};
const FAILURE_THRESHOLD = 10; // ~1s at 100ms polling
const POPUP_COOLDOWN_MS = 30000;

function degToRad(d) {
  return (d * Math.PI) / 180;
}

function updateLastOkAge(nowMs) {
  if (offlineState.lastOkMs > 0) {
    const ago = ((nowMs - offlineState.lastOkMs) / 1000).toFixed(1);
    lastOkEl.textContent = `${ago}s ago`;
  } else {
    lastOkEl.textContent = '--';
  }
}

function updateTelemetryOverlay(data) {
  const battery = typeof data?.battery_v === 'number' ? data.battery_v : null;
  const distance = typeof data?.distance_cm === 'number' ? data.distance_cm : null;
  const powerText = battery !== null ? `${battery.toFixed(2)}V` : '--';
  const rangeText = distance !== null ? `${distance.toFixed(2)}cm` : '--';
  latestBatteryText = powerText;
  latestRangeText = rangeText;

  if (powerEl) {
    powerEl.textContent = powerText;
  }
  if (rangeEl) {
    rangeEl.textContent = rangeText;
  }
  renderTopTelemetryLine();
}

function updateDiag(data) {
  const host = data?.pi_host ? `${data.pi_host}:${data.pi_port}` : '--';
  const ok = data?.last_ok_ts ? 'ok' : 'no link';
  diagEl.textContent = `${ok} @ ${host}`;
  errEl.textContent = data?.last_err ? data.last_err : '--';
}

async function pollDiag() {
  try {
    const res = await fetch('/diag', { cache: 'no-store' });
    const data = await res.json();
    updateDiag(data);
  } catch (e) {
    diagEl.textContent = 'diag error';
    errEl.textContent = 'cannot reach proxy';
  }
}

async function pollVersion() {
  try {
    const res = await fetch('/version', { cache: 'no-store' });
    const data = await res.json();
    versionEl.textContent = data?.version || '--';
    versionTimeEl.textContent = data?.ts ? new Date(data.ts * 1000).toLocaleString() : '--';
  } catch (e) {
    versionEl.textContent = 'version error';
    versionTimeEl.textContent = '--';
  }
}

async function pollTelemetry() {
  try {
    const res = await fetch('/telemetry', { cache: 'no-store' });
    const data = await res.json();
    updateTelemetryOverlay(data);
  } catch (e) {
    updateTelemetryOverlay(null);
  }
}

function maybeShowOfflinePopup(reason) {
  const now = Date.now();
  if (offlineState.consecutiveFailures < FAILURE_THRESHOLD) {
    return;
  }
  if (now - offlineState.lastPopupMs < POPUP_COOLDOWN_MS) {
    return;
  }
  offlineState.lastPopupMs = now;
  const message =
    `Pi Server not reachable (${reason}).\n\n` +
    `Try these steps:\n` +
    `1) Ensure the Pi is powered on and connected to the same network.\n` +
    `2) Confirm the Pi IP/port in the IMU proxy (use --pi-host / --pi-port).\n` +
    `3) Start the Pi server program (smartdog.sh or main.py).\n` +
    `4) Check firewall/router settings, then try again.`;
  alert(message);
}

async function pollImu() {
  try {
    const res = await fetch('/imu', { cache: 'no-store' });
    const data = await res.json();
    if (data.ok) {
      statusEl.textContent = 'live';
      offlineState.consecutiveFailures = 0;
      offlineState.lastOkMs = Date.now();
      target.roll = data.roll;
      target.pitch = data.pitch;
      target.yaw = data.yaw;
      rollEl.textContent = data.roll.toFixed(2);
      pitchEl.textContent = data.pitch.toFixed(2);
      yawEl.textContent = data.yaw.toFixed(2);
      updateLastOkAge(Date.now());
    } else {
      statusEl.textContent = 'offline';
      offlineState.consecutiveFailures += 1;
      if (data.last_ok_ts) {
        offlineState.lastOkMs = Math.max(offlineState.lastOkMs, data.last_ok_ts * 1000);
      }
      updateLastOkAge(Date.now());
      maybeShowOfflinePopup('no IMU data');
    }
  } catch (e) {
    statusEl.textContent = 'error';
    offlineState.consecutiveFailures += 1;
    updateLastOkAge(Date.now());
    maybeShowOfflinePopup('network error');
  }
}

setInterval(pollImu, 100);
setInterval(pollDiag, 1000);
setInterval(pollTelemetry, 1000);
pollVersion();
pollTelemetry();
renderTopTelemetryLine();
window.addEventListener('live-video-fps', (ev) => {
  latestFps = Number(ev?.detail?.fps || 0);
  renderTopTelemetryLine();
});
async function startLiveVideoSafe() {
  try {
    const mod = await import('/live_video.js');
    if (mod && typeof mod.initLiveVideo === 'function') {
      mod.initLiveVideo();
      return;
    }
  } catch (e) {
    // Keep IMU/telemetry UI alive even if live video helper is unavailable.
  }
  const liveStatusEl = document.getElementById('liveStatus');
  if (liveStatusEl) {
    liveStatusEl.textContent = 'Stream helper unavailable; telemetry still active';
  }
}
startLiveVideoSafe();

function animate() {
  requestAnimationFrame(animate);
  smooth.roll += (target.roll - smooth.roll) * alpha;
  smooth.pitch += (target.pitch - smooth.pitch) * alpha;
  smooth.yaw += (target.yaw - smooth.yaw) * alpha;

  dogGroup.rotation.x = degToRad(smooth.pitch);
  dogGroup.rotation.y = degToRad(smooth.yaw);
  dogGroup.rotation.z = degToRad(smooth.roll);

  renderer.render(scene, camera);
}

animate();

window.addEventListener('resize', () => {
  resizeRenderer();
});

async function sendAction(cmd) {
  try {
    await fetch('/cmd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd }),
    });
  } catch (e) {
    // ignore
  }
}

document.querySelectorAll('[data-cmd]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const cmd = btn.getAttribute('data-cmd');
    if (cmd) {
      sendAction(cmd);
    }
  });
});
