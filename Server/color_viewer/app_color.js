/*
IMU Viewer Client (Color)
Description:
  Three.js color model viewer with IMU polling, diagnostics, and model load status.
Version:
  2026.02.13-71
Revision History:
  2026-02-13 21:39 - Added Debug Detection mode for `/color` ClientAI diagnostics: optional raw-all-detections overlay (`conf>=0.10` configurable), structured per-frame JSON logging (console/panel), and ball-heuristics toggles (ROI + size gates) with editable thresholds; default runtime behavior remains unchanged when debug is off.
  2026-02-13 21:39 - Tuned guardrail balance for hard-scene recall: reduced `MT_ball` minimum bbox area gate from `0.015` to `0.008` while keeping class-switch debounce active, improving detect duty-cycle without reintroducing transient class flips.
  2026-02-13 21:31 - Added class-stability guardrails for hard scenes: enforce minimum `MT_ball` bbox area gate and require 2-frame confirmation before switching dominant lock from `MT_ball` to non-ball class, reducing transient lighting/occlusion misclass flips.
  2026-02-13 19:28 - Added MT-ball confidence stability guard for hard scenes: browser runtime now applies short-window, IoU-gated drop limiting before advisory publish to suppress one-frame lighting dips (without changing model weights), improving lock consistency for `best`/`mix`.
  2026-02-13 17:47 - Clarified ClientAI publish/reject semantics for operators: publish counters now show `accepted/rejected/local_skip`, status line adds explicit `server_last_reject` reason, and session-aware text explains unarmed skip behavior.
  2026-02-13 15:27 - Added ClientAI model-choice dial + dual-model Mix runtime for `/color`: browser can run `best_cv451` only, `yolov8n` only, or Mix (both), with lock priority `MT_ball > Yolo_Sport_Ball > Dog`, up to 3 class overlays, and per-class box colors (MT green, YOLO classes non-green).
  2026-02-13 15:03 - Polished `Vision/Stream Metrics` for ClientAI-first operations: removed Pi Edge wording from visible metrics, switched infer/model display to ClientAI-focused fields in `client-ai` mode, and moved Pi-edge/runtime tuning rows to hidden virtual debug section.
  2026-02-13 10:54 - Fixed missing detection on trained single-class model path: ClientAI decoder now supports 5-channel YOLO outputs (custom one-class exports), class label mapping prioritizes `MT_ball` for `best_cv451`, and added live overlay detect banner (`DETECTED ...`) for clear operator feedback.
  2026-02-13 10:39 - Prioritized trained ClientAI model selection: `/color` now defaults ClientAI policy/runtime fallbacks to `best_cv451.onnx` so browser startup aligns with trained model instead of generic `yolov8n`.
  2026-02-13 10:25 - Simplified ClientAI operator mode on `/color`: when `active_mode=client-ai`, viewer now auto-disables Pi Edge-AI YOLO path, locks YOLO toggle OFF, and suppresses Pi infer metric rows to avoid dual-source confusion.
  2026-02-13 10:18 - Improved ClientAI target quality on `/color`: browser now skips advisory publish when current frame has no detections, preventing `last_target` churn with `top_conf=0.0` and keeping confidence metrics meaningful.
  2026-02-13 10:12 - Added session-aware ClientAI publish gate on `/color`: browser now polls `/api/session`, skips advisory publish while unarmed (instead of flooding rejects), and exposes local publish counters with explicit unarmed status for stable closed-loop diagnostics.
  2026-02-13 09:35 - Fixed ClientAI runtime input-size mismatch on `/color`: browser now prefers model-declared input size (or model-name hint `320`) over Pi detector UI imgsz, and auto-recovers from ORT dimension errors by parsing expected size and retrying.
  2026-02-13 08:48 - Hardened Safari ClientAI runtime startup by explicitly configuring ORT WASM env (`wasmPaths`, `numThreads=1`, `proxy=false`) and added local runtime debug counters/error state in ClientAI status so browser-side infer/publish failures are visible (not masked by server polling).
  2026-02-13 07:55 - Fixed ClientAI browser decode/runtime path on `/color`: corrected YOLO tensor-dimension parsing (`[1,84,8400]` / `[1,8400,84]`), hardened ORT script-loader retry/ready checks, and surfaced local infer timing when server-side advisory target is absent.
  2026-02-12 22:51 - Added real browser-side ClientAI runtime loop on `/color` (ORT bootstrap + model manifest load + frame inference + advisory publish) and local overlay fallback for fresh detections so `client-ai` mode shows boxes immediately even when publish is rejected/stale.
  2026-02-12 22:37 - Fixed ClientAI-mode overlay/runtime confusion on `/color`: metrics header now reflects active mode, ClientAI target snapshot (`/api/vision/client-target/latest`) drives overlay in `client-ai` mode with strict TTL hide, and low-confidence stale-like ghost boxes are suppressed.
  2026-02-12 21:16 - Fixed infer-metric ownership confusion: bottom panel infer now explicitly remains Pi-runtime (`/vision/state`), while ClientAI infer/model are shown in dedicated rows fed from `/api/clientai`.
  2026-02-12 21:00 - Enabled automatic ClientAI capability sync on `/color` startup/heartbeat so default policy can promote `active_mode=client-ai` without requiring manual Apply click after service restart.
  2026-02-12 20:51 - Added explicit metrics-source labeling in `/color`: bottom panel header now renders `Vision/Stream Metrics - Pi` or `- ClientAI`, and infer-label includes source to prevent confusion between Pi edge inference and browser ClientAI latency.
  2026-02-12 19:58 - Hardened `/color` video-resolution dial sync: added startup/post-apply multi-pass `/video/config` re-sync and visibility/focus refresh so selector state tracks persisted backend profile reliably (prevents stale 640/960 display races in Safari).
  2026-02-12 19:41 - Added ClientAI policy/status wiring to original `/color` layout (`/api/clientai`): mode apply/auto controls and live requested/active/fallback/provider/model/infer/publish counters.
  2026-02-12 17:42 - Added post-load video-profile resync timers (`+1.2s`, `+4s`) so Safari refresh reliably reflects backend `/video/config` persisted profile even if initial fetch races service restart/cache.
  2026-02-12 17:33 - Added auto stream-refresh trigger after video-profile apply: emits `robotdog-video-profile-applied` event so live WebRTC path re-negotiates and new resolution takes effect without manual page refresh.
  2026-02-12 17:23 - Added publisher-apply aware video-profile status messaging: `/video/config` now reports persisted profile + publisher restart result so operators know whether WebRTC resolution switched immediately or needs manual intervention.
  2026-02-12 17:07 - Clarified video-profile apply feedback: when active stream is WebRTC, status now explains profile changes apply to H264 fallback path and WebRTC resolution follows publisher config.
  2026-02-12 16:09 - Added explicit web low-voltage behavior line (`Battery State`) and switched warning/beep gating to debounced Pi-side low-battery state fields (`low_battery`, `low_battery_since_ts`, `low_battery_duration_s`).
  2026-02-12 15:53 - Tuned relative-time scope alignment so x-axis follows true uptime dynamically: before 60 minutes axis expands `0 -> uptime`; after 60 minutes it switches to rolling 60-minute window while keeping 5-minute tick cadence.
  2026-02-12 15:45 - Updated diag HUD rendering to prefer LAN-reachable control endpoint (`control_display_host`) and show compact ports/function summary line from Pi `/diag`.
  2026-02-12 15:42 - Refactored power scope to relative-time mission axis (`elapsed = ts - start`) with 60-minute rolling window, dynamic 5-minute ticks, and header format `START: HH:MM:SS | UPTIME: HH:MM:SS`.
  2026-02-12 15:02 - Added battery-scope power-on runtime ticker (`Power On HH:MM:SS`) driven by Pi telemetry uptime so operators can see elapsed on-time directly inside the voltage chart.
  2026-02-12 14:51 - Added compact HUD tuning and stream profile control wiring: merged Live Clients header/summary, removed redundant visible proxy/status/model rows, added `video-profile` selector (`1280/960/640`) via Pi `/video/config`, improved battery-scope label placement, and surfaced 3D model load errors directly inside overlay canvas.
  2026-02-12 14:14 - Polished operator HUD/runtime handling: merged stream detail into status pane with LIVE/STALLED pill, added IMU-telemetry-lost mode (red header + grey matrix placeholders + upper telemetry fallback), mirrored battery scope to left->right 0..40min axis with dynamic low-voltage marker color, and added periodic low-battery triple-beep guard.
  2026-02-12 12:50 - Added live battery trend overlay renderer (25-minute window) with rail/reference/warn dashed lines, plus low-battery warning badge and compact warning messaging.
  2026-02-12 11:38 - Added `Live Clients` widget runtime wiring: polls Pi `/viewer/summary` every 5s and renders healthy heartbeat viewers (device/IP/FPS/age) in HUD.
  2026-02-12 11:16 - Added transient-RTSP warning guard: minor vision transport errors no longer trigger video grey-out; alert remains non-blocking and is rendered as bottom-center warning while stream continues.
  2026-02-12 10:30 - Added target-source tag in overlay label (`[trk]`) when Pi tracking-hold publishes predicted lock, making tracking behavior visible without coupling to control commands.
  2026-02-12 10:22 - Debounced stream-stall overlay activation/clear to reduce intermittent grey flicker on brief probe/FPS dips while preserving outage visibility.
  2026-02-12 10:15 - Removed blocking offline popup dialog (`alert`) for Pi outages; switched to non-blocking inline status notice so stream/IMU auto-recovery does not require user click-to-dismiss.
  2026-02-12 09:51 - Added stream-stall/error visual alert logic (grey live pane + clear overlay text), hid stale vision target boxes to prevent long-linger confusion, and exposed active infer-model source beside `Infer (ms)` for real-time model-path visibility.
  2026-02-11 17:20 - Added live vision target rendering (bbox overlay + label) and detector-health/latency fields from Pi `/vision/state` worker output.
  2026-02-11 14:57 - Wired `Yolo Vision` and `Tracking` action keys to Pi runtime `/vision/state` toggles and added read-only vision state rendering (`disabled/detect_only/tracking/stale`) for D-Phase-A.
  2026-02-11 14:40 - Added Vision/Stream metrics client reporting and bottom-panel rendering; sends stream FPS heartbeat to Pi service for target-FPS auto-throttle decisions.
  2026-02-11 14:40 - Added Pi-service vision performance config runtime knobs UI wiring (`/vision/config`) with apply/reload status feedback.
  2026-02-11 12:57 - Synced Demo button state with safety stops: pressing Relax/Stop-class keys now immediately clears local Demo-running UI.
  2026-02-11 12:08 - Added Horizon toggle command wiring and Demo trigger integration via `/demo`; keeps unsupported controls disabled.
  2026-02-11 11:46 - Added robust action-key wiring: explicit motion-speed payloads, Beep/LED command sequences, and Balance toggle state sync; unsupported keys remain disabled placeholders.
  2026-02-11 10:16 - Fixed `Reset Yaw to Right` wiring, added auto yaw-right reset on IMU live connect/recover, and aligned control naming from north->right.
  2026-02-11 09:59 - Added experimental `Pi-native Roll/Pitch` toggle (default remains swapped mapping) for side-by-side axis-behavior testing.
  2026-02-11 09:44 - Added explicit axis-definition comments at model rotation mapping (`Yaw->Z`, `Pitch->X`, `Roll->Y`) and synchronized UI/README wording.
  2026-02-11 09:40 - Added IMU matrix diagnostics (`Raw Pi`, `modified`, `3D model`) and a side-by-side animated XYZ axes helper using same transform chain as the dog model.
  2026-02-11 09:13 - Added `Reset Yaw to North` control that zeroes current heading via viewer-side yaw offset while preserving roll/pitch behavior.
  2026-02-11 09:04 - Swapped left/right roll display direction by flipping roll sign in body-tilt rotation mapping.
  2026-02-10 22:06 - Fixed root pose-frame issue by splitting yaw and body tilt into parent/child groups; removed pitch-jump guard hack.
  2026-02-10 21:51 - Added pitch-jump guard near high-roll region to block singularity-like branch flips where rolling injects false pitch.
  2026-02-10 21:37 - Aligned live pose axis mapping with simple viewer baseline (`x=-roll`, `z=pitch`) to resolve roll showing as pitch in color model.
  2026-02-10 21:34 - Fixed model-axis mapping (roll now drives lateral tilt) and switched to angle-aware smoothing to prevent large spin when pitch crosses +/-180.
  2026-02-10 21:16 - Reverted to basic IMU mapping/render path (app_simple-style) and disabled advanced tuning controls for stability-first behavior.
  2026-02-10 21:09 - Switched model pose rendering to quaternion+slerp path to remove roll/pitch branch coupling; fixed roll-only movement causing back-pitch artifacts.
  2026-02-10 21:03 - Replaced unstable roll/pitch continuity accumulation with Euler-branch correction + bounded rate limiting to prevent drift/axis flips after motion.
  2026-02-10 20:50 - Added continuity/rate guard for roll/pitch/yaw to suppress Euler singularity spikes (e.g., pitch snapping near roll ~-90).
  2026-02-10 19:18 - Fixed roll direction regression by aligning color-view roll axis sign with verified simple-view behavior.
  2026-02-10 19:10 - Added persistent orientation tuning (invert/offset/reset) and wired live build badge text from proxy version endpoint.
  2026-02-10 18:56 - Add bottom-left live-video overlay status logic: compact IMU line + stale (>1s) red text and greyscale model alert.
  2026-02-10 18:42 - Refactor IMU->model mapping and add yaw unwrapping to prevent +-180 wrap jumps.
  2026-02-10 18:06 - Add YAW_ENABLE toggle to lock yaw at 0 for debugging.
  2026-02-10 17:56 - Invert roll sign to fix left/right roll direction.
  2026-02-10 17:53 - Add base roll offset so the color model rests upright on flat surface.
  2026-02-10 17:48 - Align color model IMU mapping with verified simple model behavior.
  2026-02-10 16:55 - Align IMU axis mapping to Y-forward, X-left-right, Z-up convention.
  2026-02-10 16:34 - Align color model base orientation to match simple model axes.
  2026-02-07 15:14 - Added top-left telemetry line with video FPS overlay.
  2026-02-07 15:06 - Load live_video.js via safe dynamic import so IMU/telemetry still run if missing.
  2026-02-07 14:46 - Added live video auto-selection (H264-first, MJPEG fallback).
  2026-02-07 13:39 - Added live telemetry polling for power/range.
*/

import * as THREE from '/vendor/three/three.module.js';

const threeContainer = document.getElementById('three-container');
import { MTLLoader } from '/vendor/three/MTLLoader.js';
import { OBJLoader } from '/vendor/three/OBJLoader.js';

const YAW_ENABLE = true; // set true to enable yaw. Set false to lock yaw at 0 deg (face right) for debugging.

const statusEl = document.getElementById('status');
const diagEl = document.getElementById('diag');
const errEl = document.getElementById('err');
const portsMapEl = document.getElementById('ports-map');
const modelStatusEl = document.getElementById('modelstatus');
const modelErrEl = document.getElementById('modelerr');
const versionEl = document.getElementById('version');
const versionTimeEl = document.getElementById('versiontime');
const powerEl = document.getElementById('power');
const rangeEl = document.getElementById('range');
const batteryStateEl = document.getElementById('battery-state');
const telemetryTopEl = document.getElementById('telemetryTop');
const streamDetailEl = document.getElementById('stream-detail');
const streamStatePillEl = document.getElementById('stream-state-pill');
const rollEl = document.getElementById('roll');
const pitchEl = document.getElementById('pitch');
const yawEl = document.getElementById('yaw');
const lastOkEl = document.getElementById('lastok');
const rawRollEl = document.getElementById('raw-roll');
const rawPitchEl = document.getElementById('raw-pitch');
const rawYawEl = document.getElementById('raw-yaw');
const modRollEl = document.getElementById('mod-roll');
const modPitchEl = document.getElementById('mod-pitch');
const modYawEl = document.getElementById('mod-yaw');
const modelRollEl = document.getElementById('model-roll');
const modelPitchEl = document.getElementById('model-pitch');
const modelYawEl = document.getElementById('model-yaw');
const imuOverlayEl = document.getElementById('imu-overlay');
const imuCompactEl = document.getElementById('imuCompact');
const imuStatusBoxEl = document.getElementById('imu-status-box');
const imuStatusHeadEl = document.getElementById('imu-status-head');
const buildBadgeEl = document.getElementById('build-badge');
const invRollEl = document.getElementById('inv-roll');
const invPitchEl = document.getElementById('inv-pitch');
const invYawEl = document.getElementById('inv-yaw');
const offRollEl = document.getElementById('off-roll');
const offPitchEl = document.getElementById('off-pitch');
const offYawEl = document.getElementById('off-yaw');
const oriResetEl = document.getElementById('ori-reset');
const resetYawRightEl = document.getElementById('reset-yaw-right');
const usePiNativeAxisEl = document.getElementById('use-pi-native-axis');
const toggleBalanceEl = document.getElementById('toggle-balance');
const toggleHorizonEl = document.getElementById('toggle-horizon');
const triggerDemoEl = document.getElementById('trigger-demo');
const toggleYoloEl = document.getElementById('toggle-yolo');
const toggleTrackingEl = document.getElementById('toggle-tracking');
const visionImgszEl = document.getElementById('vision-imgsz');
const videoProfileEl = document.getElementById('video-profile');
const visionIntervalNEl = document.getElementById('vision-interval-n');
const visionMinFpsEl = document.getElementById('vision-min-fps');
const visionAutoDegradeEl = document.getElementById('vision-auto-degrade');
const visionConfigApplyEl = document.getElementById('vision-config-apply');
const visionConfigReloadEl = document.getElementById('vision-config-reload');
const visionConfigStatusEl = document.getElementById('vision-config-status');
const clientAiModeEl = document.getElementById('clientai-mode');
const clientAiApplyEl = document.getElementById('clientai-apply');
const clientAiAutoEl = document.getElementById('clientai-auto');
const clientAiStatusEl = document.getElementById('clientai-status');
const clientAiRequestedEl = document.getElementById('clientai-requested');
const clientAiActiveEl = document.getElementById('clientai-active');
const clientAiFallbackEl = document.getElementById('clientai-fallback');
const clientAiProviderEl = document.getElementById('clientai-provider');
const clientAiModelChoiceEl = document.getElementById('clientai-model-choice');
const clientAiModelEl = document.getElementById('clientai-model');
const clientAiInferMsEl = document.getElementById('clientai-infer-ms');
const clientAiPublishCountsEl = document.getElementById('clientai-publish-counts');
const debugDetectEnableEl = document.getElementById('debug-detect-enable');
const debugRawConfEl = document.getElementById('debug-raw-conf');
const debugIouNmsEl = document.getElementById('debug-iou-nms');
const debugMaxDetEl = document.getElementById('debug-max-det');
const debugLogConsoleEl = document.getElementById('debug-log-console');
const debugLogPanelEl = document.getElementById('debug-log-panel');
const debugHeuristicsEnableEl = document.getElementById('debug-heuristics-enable');
const debugRoiEnableEl = document.getElementById('debug-roi-enable');
const debugRoiGateYEl = document.getElementById('debug-roi-gate-y');
const debugSizeEnableEl = document.getElementById('debug-size-enable');
const debugMinAreaEl = document.getElementById('debug-min-area');
const debugMaxAreaEl = document.getElementById('debug-max-area');
const debugDetectLogEl = document.getElementById('debug-detect-log');
const vmStreamFpsEl = document.getElementById('vm-stream-fps');
const vmMinFpsEl = document.getElementById('vm-min-fps');
const vmKpiStatusEl = document.getElementById('vm-kpi-status');
const vmImgszEl = document.getElementById('vm-imgsz');
const vmIntervalNEl = document.getElementById('vm-interval-n');
const vmAutoDegradeEl = document.getElementById('vm-auto-degrade');
const vmThrottleActionEl = document.getElementById('vm-throttle-action');
const vmThrottleCountEl = document.getElementById('vm-throttle-count');
const vmStreamPrefEl = document.getElementById('vm-stream-pref');
const vmMjpegFpsEl = document.getElementById('vm-mjpeg-fps');
const vmClientAgeEl = document.getElementById('vm-client-age');
const vmVisionModeEl = document.getElementById('vm-vision-mode');
const vmTargetCountEl = document.getElementById('vm-target-count');
const vmDetFpsEl = document.getElementById('vm-det-fps');
const vmInferMsEl = document.getElementById('vm-infer-ms');
const vmInferKeyEl = document.getElementById('vm-infer-key');
const vmInferModelEl = document.getElementById('vm-infer-model');
const vmClientAiInferMsEl = document.getElementById('vm-clientai-infer-ms');
const vmClientAiModelEl = document.getElementById('vm-clientai-model');
const vmVisionHealthEl = document.getElementById('vm-vision-health');
const vmVisionErrorEl = document.getElementById('vm-vision-error');
const vmHeaderEl = document.getElementById('vm-header');
const visionTargetOverlayEl = document.getElementById('vision-target-overlay');
const visionTargetBoxEl = document.getElementById('vision-target-box');
const visionTargetLabelEl = document.getElementById('vision-target-label');
const liveViewEl = document.getElementById('live-view');
const clientAiDetectBannerEl = document.createElement('div');
const liveStatusEl = document.getElementById('liveStatus');
const streamAlertTextEl = document.getElementById('stream-alert-text');
const streamAlertSubEl = document.getElementById('stream-alert-sub');
const viewerClientsHeadEl = document.getElementById('viewer-clients-head');
const viewerClientsListEl = document.getElementById('viewer-clients-list');
const batteryTrendCanvasEl = document.getElementById('battery-trend-canvas');
const batteryLowWarnEl = document.getElementById('battery-low-warn');
const modelAlertEl = document.getElementById('model-alert');

let latestBatteryText = '--';
let latestRangeText = '--';
let latestBatteryV = null;
let batteryWarnV = 6.4;
let latestLowBatteryActive = false;
let latestLowBatteryDurationS = 0;
let latestLowBatteryPolicy = '';
let latestPowerHistory = null;
let latestFps = 0;
let latestVideoEventMs = 0;
let latestVideoMode = '';
let imuTelemetryLostState = true;
let lowBatteryBeepLastMs = 0;
let lowBatteryBeepBusy = false;
let stallCandidateCount = 0;
let stallClearCount = 0;
const STALL_ASSERT_TICKS = 2;
const STALL_CLEAR_TICKS = 2;
const rawImu = { roll: null, pitch: null, yaw: null };
const modifiedImu = { roll: null, pitch: null, yaw: null };
let latestVisionState = null;
let clientAiStatus = null;
let latestClientTargetSnapshot = null;
let latestClientAiLocalDetections = [];
let clientAiEdgeDisableInFlight = false;
const VIDEO_PROFILE_RESYNC_DELAYS_MS = [0, 1200, 4000, 9000];
let videoProfileResyncTimers = [];
const TARGET_RENDER_MIN_CONF = 0.60;
const CLIENT_TARGET_MAX_AGE_MS = 1500;
const CLIENTAI_LOCAL_TARGET_MAX_AGE_MS = 1200;
const CLIENTAI_LOCAL_RENDER_MIN_CONF = 0.35;
const CLIENTAI_ALLOWED_LABELS = new Set(['MT_ball', 'Yolo_Sport_Ball', 'Dog', 'Person', 'Cat']);
const CLIENTAI_ORT_CDN = 'https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js';
const CLIENTAI_ORT_FALLBACK = 'https://unpkg.com/onnxruntime-web/dist/ort.min.js';
const CLIENTAI_PREFERRED_MODEL = 'best_cv451.onnx';
const CLIENTAI_YOLO_MODEL_FALLBACK = 'yolov8n_cv451.onnx';
const CLIENTAI_MODEL_CHOICE_BEST = 'best';
const CLIENTAI_MODEL_CHOICE_YOLO = 'yolov8n';
const CLIENTAI_MODEL_CHOICE_MIX = 'mix';
const CLIENTAI_MAX_RENDER_CLASSES = 3;
const CLIENTAI_STABLE_CONF_LABEL = 'MT_ball';
const CLIENTAI_STABLE_LOCK_CONF = 0.75;
const CLIENTAI_STABLE_MAX_DROP = 0.12;
const CLIENTAI_STABLE_MAX_AGE_MS = 1500;
const CLIENTAI_STABLE_MIN_IOU = 0.12;
const CLIENTAI_MT_BALL_MIN_AREA = 0.008;
const CLIENTAI_CLASS_SWITCH_CONFIRM_FRAMES = 2;
const CLIENTAI_CLASS_SWITCH_HOLD_MS = 1200;
const CLIENTAI_DEBUG_RAW_CONF_DEFAULT = 0.10;
const CLIENTAI_DEBUG_NMS_DEFAULT = 0.45;
const CLIENTAI_DEBUG_MAXDET_DEFAULT = 60;
const CLIENTAI_DEBUG_LOG_TOPK = 10;
const CLIENTAI_BOX_STYLE = {
  MT_ball: { border: 'rgba(36,255,156,0.92)', labelBg: 'rgba(36,255,156,0.92)', labelFg: '#071216' },
  Yolo_Sport_Ball: { border: 'rgba(255,218,92,0.96)', labelBg: 'rgba(255,218,92,0.96)', labelFg: '#231a00' },
  Dog: { border: 'rgba(91,212,255,0.96)', labelBg: 'rgba(91,212,255,0.96)', labelFg: '#03131a' },
  Person: { border: 'rgba(255,160,92,0.96)', labelBg: 'rgba(255,160,92,0.96)', labelFg: '#241103' },
  Cat: { border: 'rgba(246,131,247,0.96)', labelBg: 'rgba(246,131,247,0.96)', labelFg: '#250629' },
  _default: { border: 'rgba(146,189,255,0.96)', labelBg: 'rgba(146,189,255,0.96)', labelFg: '#0a1223' },
};
const clientAiRuntime = {
  running: false,
  manifest: null,
  modelReady: false,
  modelChoice: CLIENTAI_MODEL_CHOICE_BEST,
  inferSession: null,
  inferSessionBest: null,
  inferSessionYolo: null,
  modelName: '',
  modelNameBest: '',
  modelNameYolo: '',
  provider: 'unknown',
  frameId: 0,
  inferEveryN: 8,
  inferMsAvg: null,
  inputSize: 256,
  inputSizeBest: 256,
  inputSizeYolo: 256,
  tickBusy: false,
  lastInferMs: null,
  inferAttempts: 0,
  inferSuccess: 0,
  postOk: 0,
  postFail: 0,
  postSkipUnarmed: 0,
  lastError: '',
  ortScriptSrc: '',
  sessionArmed: false,
  sessionKnown: false,
  stableByLabel: {},
  classSwitchState: {
    dominantLabel: '',
    pendingLabel: '',
    pendingCount: 0,
    holdMtBall: null,
  },
  debug: {
    enabled: false,
    rawConfThres: CLIENTAI_DEBUG_RAW_CONF_DEFAULT,
    iouNms: CLIENTAI_DEBUG_NMS_DEFAULT,
    maxDet: CLIENTAI_DEBUG_MAXDET_DEFAULT,
    logConsole: true,
    logPanel: false,
    heuristicsEnabled: false,
    roiGateEnabled: false,
    roiGateY: 0.45,
    sizeGateEnabled: false,
    minArea: CLIENTAI_MT_BALL_MIN_AREA,
    maxArea: 0.30,
    rawDetections: [],
  },
};
const clientAiSampleCanvas = document.createElement('canvas');
const clientAiSampleCtx = clientAiSampleCanvas.getContext('2d', { willReadFrequently: true });
const clientAiLumaCanvas = document.createElement('canvas');
const clientAiLumaCtx = clientAiLumaCanvas.getContext('2d', { willReadFrequently: true });

if (liveViewEl) {
  clientAiDetectBannerEl.id = 'clientai-detect-banner';
  clientAiDetectBannerEl.style.position = 'absolute';
  clientAiDetectBannerEl.style.left = '12px';
  clientAiDetectBannerEl.style.bottom = '12px';
  clientAiDetectBannerEl.style.padding = '4px 8px';
  clientAiDetectBannerEl.style.border = '1px solid rgba(0,255,170,0.65)';
  clientAiDetectBannerEl.style.borderRadius = '8px';
  clientAiDetectBannerEl.style.background = 'rgba(0,32,24,0.82)';
  clientAiDetectBannerEl.style.color = '#00ffb5';
  clientAiDetectBannerEl.style.fontSize = '11px';
  clientAiDetectBannerEl.style.fontWeight = '700';
  clientAiDetectBannerEl.style.display = 'none';
  clientAiDetectBannerEl.style.pointerEvents = 'none';
  liveViewEl.appendChild(clientAiDetectBannerEl);
}

function setClientAiDetectBanner(text = '', visible = false) {
  if (!clientAiDetectBannerEl) return;
  clientAiDetectBannerEl.textContent = text || '';
  clientAiDetectBannerEl.style.display = visible ? 'block' : 'none';
}

function parseDebugFloat(el, fallback, minV, maxV) {
  const v = Number(el?.value);
  if (!Number.isFinite(v)) return fallback;
  return Math.max(minV, Math.min(maxV, v));
}

function parseDebugInt(el, fallback, minV, maxV) {
  const v = Math.round(Number(el?.value));
  if (!Number.isFinite(v)) return fallback;
  return Math.max(minV, Math.min(maxV, v));
}

function syncClientAiDebugConfigFromUi() {
  const dbg = clientAiRuntime.debug;
  dbg.enabled = String(debugDetectEnableEl?.value || 'off') === 'on';
  dbg.rawConfThres = parseDebugFloat(debugRawConfEl, CLIENTAI_DEBUG_RAW_CONF_DEFAULT, 0.01, 0.99);
  dbg.iouNms = parseDebugFloat(debugIouNmsEl, CLIENTAI_DEBUG_NMS_DEFAULT, 0.05, 0.95);
  dbg.maxDet = parseDebugInt(debugMaxDetEl, CLIENTAI_DEBUG_MAXDET_DEFAULT, 5, 120);
  dbg.logConsole = String(debugLogConsoleEl?.value || 'on') === 'on';
  dbg.logPanel = String(debugLogPanelEl?.value || 'off') === 'on';
  dbg.heuristicsEnabled = String(debugHeuristicsEnableEl?.value || 'off') === 'on';
  dbg.roiGateEnabled = String(debugRoiEnableEl?.value || 'off') === 'on';
  dbg.roiGateY = parseDebugFloat(debugRoiGateYEl, 0.45, 0.0, 1.0);
  dbg.sizeGateEnabled = String(debugSizeEnableEl?.value || 'off') === 'on';
  dbg.minArea = parseDebugFloat(debugMinAreaEl, CLIENTAI_MT_BALL_MIN_AREA, 0.0001, 1.0);
  dbg.maxArea = parseDebugFloat(debugMaxAreaEl, 0.30, 0.001, 1.0);
  if (dbg.maxArea < dbg.minArea) {
    const tmp = dbg.maxArea;
    dbg.maxArea = dbg.minArea;
    dbg.minArea = tmp;
  }
  if (debugDetectLogEl) debugDetectLogEl.style.display = (dbg.enabled && dbg.logPanel) ? 'block' : 'none';
}

function hideDebugRawOverlay() {
  if (!visionTargetOverlayEl) return;
  const extras = visionTargetOverlayEl.querySelectorAll('.vision-target-debug-box');
  extras.forEach((el) => el.remove());
}

function debugClassColor(label) {
  const text = String(label || 'cls');
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = ((hash * 31) + text.charCodeAt(i)) >>> 0;
  const h = hash % 360;
  return `hsl(${h} 92% 62%)`;
}

function renderDebugRawDetections(rawDetections = []) {
  hideDebugRawOverlay();
  if (!visionTargetOverlayEl) return;
  const dbg = clientAiRuntime.debug;
  if (!dbg.enabled) return;
  const list = Array.isArray(rawDetections) ? rawDetections : [];
  list.slice(0, dbg.maxDet).forEach((det, idx) => {
    const box = document.createElement('div');
    box.className = 'vision-target-debug-box';
    box.style.position = 'absolute';
    box.style.left = `${clamp01(det.x1) * 100}%`;
    box.style.top = `${clamp01(det.y1) * 100}%`;
    box.style.width = `${Math.max(0, clamp01(det.x2) - clamp01(det.x1)) * 100}%`;
    box.style.height = `${Math.max(0, clamp01(det.y2) - clamp01(det.y1)) * 100}%`;
    box.style.border = `1px dashed ${debugClassColor(det.label)}`;
    box.style.borderRadius = '3px';
    box.style.boxShadow = '0 0 0 1px rgba(0,0,0,.35) inset';
    box.style.pointerEvents = 'none';
    box.style.opacity = idx < 10 ? '0.95' : '0.45';
    const labelEl = document.createElement('div');
    const area = Math.max(0, (Number(det.x2 || 0) - Number(det.x1 || 0)) * (Number(det.y2 || 0) - Number(det.y1 || 0));
    const cx = (Number(det.x1 || 0) + Number(det.x2 || 0)) / 2;
    const cy = (Number(det.y1 || 0) + Number(det.y2 || 0)) / 2;
    labelEl.textContent = `${det.label} ${Number(det.conf || 0).toFixed(2)} a=${area.toFixed(3)} c=(${cx.toFixed(2)},${cy.toFixed(2)})`;
    labelEl.style.position = 'absolute';
    labelEl.style.top = '-19px';
    labelEl.style.left = '0';
    labelEl.style.fontSize = '10px';
    labelEl.style.padding = '1px 4px';
    labelEl.style.borderRadius = '3px';
    labelEl.style.whiteSpace = 'nowrap';
    labelEl.style.background = 'rgba(0,0,0,.68)';
    labelEl.style.color = '#f1f6ff';
    box.appendChild(labelEl);
    visionTargetOverlayEl.appendChild(box);
  });
}

function resolveClientAiModelChoice(choiceLike) {
  const value = String(choiceLike || '').trim().toLowerCase();
  if (value === CLIENTAI_MODEL_CHOICE_MIX) return CLIENTAI_MODEL_CHOICE_MIX;
  if (value === CLIENTAI_MODEL_CHOICE_YOLO) return CLIENTAI_MODEL_CHOICE_YOLO;
  return CLIENTAI_MODEL_CHOICE_BEST;
}

function getClientAiStateModelId() {
  const choice = resolveClientAiModelChoice(clientAiRuntime.modelChoice);
  if (choice === CLIENTAI_MODEL_CHOICE_YOLO) {
    return String(clientAiRuntime.modelNameYolo || CLIENTAI_YOLO_MODEL_FALLBACK);
  }
  return String(clientAiRuntime.modelNameBest || CLIENTAI_PREFERRED_MODEL);
}

function getClientAiDisplayModelLabel() {
  const choice = resolveClientAiModelChoice(clientAiRuntime.modelChoice);
  if (choice === CLIENTAI_MODEL_CHOICE_MIX) {
    const best = String(clientAiRuntime.modelNameBest || CLIENTAI_PREFERRED_MODEL);
    const yolo = String(clientAiRuntime.modelNameYolo || CLIENTAI_YOLO_MODEL_FALLBACK);
    return `Mix (${best} + ${yolo})`;
  }
  if (choice === CLIENTAI_MODEL_CHOICE_YOLO) {
    return String(clientAiRuntime.modelNameYolo || CLIENTAI_YOLO_MODEL_FALLBACK);
  }
  return String(clientAiRuntime.modelNameBest || CLIENTAI_PREFERRED_MODEL);
}

function clearClientAiModelSessions() {
  clientAiRuntime.modelReady = false;
  clientAiRuntime.inferSession = null;
  clientAiRuntime.inferSessionBest = null;
  clientAiRuntime.inferSessionYolo = null;
  clientAiRuntime.modelName = '';
  clientAiRuntime.modelNameBest = '';
  clientAiRuntime.modelNameYolo = '';
  clientAiRuntime.inputSize = 256;
  clientAiRuntime.inputSizeBest = 256;
  clientAiRuntime.inputSizeYolo = 256;
}

function refreshVisionMetricsHeader() {
  if (!vmHeaderEl) return;
  const activeMode = String(clientAiStatus?.active_mode || '').toLowerCase();
  if (activeMode === 'client-ai') {
    vmHeaderEl.textContent = 'Vision/Stream Metrics - ClientAI';
    return;
  }
  vmHeaderEl.textContent = 'Vision/Stream Metrics';
}

function renderTopTelemetryLine() {
  if (!telemetryTopEl) return;
  const telemetryLost = isImuStale(Date.now());
  const powerText = telemetryLost ? '-.--V' : latestBatteryText;
  const rangeText = telemetryLost ? '-.--cm' : latestRangeText;
  const fpsText = `${latestFps.toFixed(1)}fps`;
  telemetryTopEl.textContent = `Power ${powerText}  Range ${rangeText}  ${fpsText}`;
}

function drawDashedLine(ctx, x1, y1, x2, y2, color, dash = [4, 3], lw = 1) {
  ctx.save();
  ctx.setLineDash(dash);
  ctx.strokeStyle = color;
  ctx.lineWidth = lw;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.restore();
}

function formatDurationHms(totalSec) {
  const sec = Math.max(0, Math.floor(Number(totalSec) || 0));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatClockHms(tsSec) {
  const ts = Number(tsSec);
  if (!Number.isFinite(ts) || ts <= 0) return '--:--:--';
  const d = new Date(ts * 1000);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

function renderBatteryStateLine() {
  if (!batteryStateEl) return;
  const vtxt = Number.isFinite(latestBatteryV) ? `${Number(latestBatteryV).toFixed(2)}V` : '--';
  const wtxt = Number.isFinite(batteryWarnV) ? `${Number(batteryWarnV).toFixed(2)}V` : '--';
  if (latestLowBatteryActive) {
    const dur = formatDurationHms(latestLowBatteryDurationS || 0);
    const policy = latestLowBatteryPolicy ? ` ${latestLowBatteryPolicy}` : '';
    batteryStateEl.textContent = `LOW ${vtxt} <= ${wtxt} (since ${dur})${policy}`;
    batteryStateEl.style.color = '#ff9b9b';
    return;
  }
  batteryStateEl.textContent = `NORMAL ${vtxt} > ${wtxt}`;
  batteryStateEl.style.color = '#93ffbf';
}

function renderBatteryTrendOverlay() {
  const canvas = batteryTrendCanvasEl;
  if (!canvas) return;
  const parent = canvas.parentElement;
  const cssW = Math.max(120, Math.floor(parent?.clientWidth || 300));
  const cssH = Math.max(80, Math.floor(parent?.clientHeight || 120));
  const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
  if (canvas.width !== cssW * dpr || canvas.height !== cssH * dpr) {
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
  }
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  const railMin = Number(latestPowerHistory?.rail_min_v ?? 5.5);
  const railMax = Number(latestPowerHistory?.rail_max_v ?? 8.5);
  const refV = Number(latestPowerHistory?.ref_v ?? 7.0);
  const warnV = Number(latestPowerHistory?.warn_v ?? batteryWarnV ?? 6.4);
  const windowMin = Math.max(60, Number(latestPowerHistory?.window_min ?? 60));
  const points = Array.isArray(latestPowerHistory?.points) ? latestPowerHistory.points : [];
  const nowTs = Number(latestPowerHistory?.ts ?? (Date.now() / 1000));
  const windowSec = Math.max(60, windowMin * 60);
  const padL = 28;
  const padR = 8;
  const padT = 10;
  const padB = 18;
  const pw = Math.max(10, cssW - padL - padR);
  const ph = Math.max(10, cssH - padT - padB);
  const x0 = padL;
  const y0 = padT;
  const x1 = padL + pw;
  const y1 = padT + ph;

  const historyStartTs = Number(latestPowerHistory?.history_start_ts || 0);
  const uptimeSRaw = Number(latestPowerHistory?.uptime_s);
  const uptimeS = Number.isFinite(uptimeSRaw) && uptimeSRaw >= 0
    ? uptimeSRaw
    : (historyStartTs > 0 ? Math.max(0, nowTs - historyStartTs) : 0);
  const elapsedNowMin = Math.max(0, uptimeS / 60.0);
  // Dynamic scope alignment: grow from 0->uptime until full window, then roll.
  const axisSpanMin = elapsedNowMin <= windowMin
    ? Math.max(1 / 60, elapsedNowMin)
    : windowMin;
  const windowEndMin = elapsedNowMin;
  const windowStartMin = Math.max(0, windowEndMin - axisSpanMin);
  const toX = (elapsedMin) => {
    const t = Math.max(windowStartMin, Math.min(windowEndMin, Number(elapsedMin || windowStartMin)));
    return x0 + ((t - windowStartMin) / Math.max(0.001, axisSpanMin)) * pw;
  };
  const toY = (v) => {
    const clamped = Math.max(railMin, Math.min(railMax, Number(v || railMin)));
    const t = (clamped - railMin) / Math.max(0.001, (railMax - railMin));
    return y1 - (t * ph);
  };

  ctx.fillStyle = 'rgba(7,14,24,0.45)';
  ctx.fillRect(x0, y0, pw, ph);
  ctx.strokeStyle = 'rgba(180,210,255,0.28)';
  ctx.lineWidth = 1;
  ctx.strokeRect(x0, y0, pw, ph);

  drawDashedLine(ctx, x0, toY(refV), x1, toY(refV), 'rgba(255,255,255,.65)', [5, 4], 1);
  drawDashedLine(ctx, x0, toY(warnV), x1, toY(warnV), 'rgba(255,82,82,.9)', [6, 4], 1);
  const leftLabelX = 2;
  ctx.fillStyle = 'rgba(255,255,255,.9)';
  ctx.fillText(`${refV.toFixed(1)}V`, leftLabelX, toY(refV) - 2);
  ctx.fillStyle = 'rgba(255,120,120,.95)';
  ctx.fillText(`${warnV.toFixed(1)}V`, leftLabelX, toY(warnV) - 2);

  ctx.fillStyle = 'rgba(180,210,255,.85)';
  ctx.font = '10px system-ui, -apple-system, Segoe UI';
  ctx.fillText(`${railMax.toFixed(1)}V`, leftLabelX, y0 + 8);
  ctx.fillText(`${railMin.toFixed(1)}V`, leftLabelX, y1 - 2);
  ctx.fillStyle = 'rgba(235,245,255,.92)';
  const firstTickMin = Math.ceil(windowStartMin / 5) * 5;
  for (let m = firstTickMin; m <= Math.ceil(windowEndMin); m += 5) {
    if (m < windowStartMin || m > windowEndMin) continue;
    const tx = toX(m);
    drawDashedLine(ctx, tx, y1, tx, y1 + 4, 'rgba(185,205,235,.42)', [1, 0], 1);
    ctx.fillText(`${m}`, tx - 4, cssH - 3);
  }
  ctx.fillText('min', x1 - 10, y1 - 4);
  if (Number.isFinite(uptimeS) && uptimeS >= 0) {
    ctx.fillStyle = 'rgba(255,220,140,.95)';
    ctx.fillText(`START: ${formatClockHms(historyStartTs)} | UPTIME: ${formatDurationHms(uptimeS)}`, x0 + 4, y0 + 10);
  }

  if (points.length >= 2) {
    ctx.strokeStyle = 'rgba(122,214,255,.98)';
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    let started = false;
    for (const p of points) {
      const ts = Number(p?.ts || 0);
      const bv = Number(p?.battery_v);
      if (!Number.isFinite(ts) || !Number.isFinite(bv)) continue;
      if (!(historyStartTs > 0)) continue;
      const elapsedMin = Math.max(0, (ts - historyStartTs) / 60.0);
      if (elapsedMin < windowStartMin || elapsedMin > windowEndMin) continue;
      const x = toX(elapsedMin);
      const y = toY(bv);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    if (started) ctx.stroke();
  }

  if (Number.isFinite(latestBatteryV)) {
    const lowNow = Number.isFinite(latestBatteryV) && latestBatteryV <= warnV;
    let markerX = x1 - 1;
    if (points.length > 0) {
      const lastPoint = points[points.length - 1];
      const lastTs = Number(lastPoint?.ts || nowTs);
      const elapsedMin = historyStartTs > 0 ? Math.max(0, (lastTs - historyStartTs) / 60.0) : elapsedNowMin;
      markerX = toX(elapsedMin);
    }
    const y = toY(latestBatteryV);
    const x = markerX;
    ctx.fillStyle = lowNow ? 'rgba(255,96,96,.98)' : 'rgba(36,255,156,.98)';
    ctx.beginPath();
    ctx.arc(x, y, 2.8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = lowNow ? 'rgba(255,160,160,.98)' : 'rgba(235,245,255,.98)';
    ctx.fillText(`${Number(latestBatteryV).toFixed(2)}V`, Math.max(x0 + 2, x - 18), y - 14);
  }

  const lowNow = !!latestLowBatteryActive;
  if (batteryLowWarnEl) {
    batteryLowWarnEl.style.display = lowNow ? 'block' : 'none';
    if (lowNow) {
      const dur = formatDurationHms(latestLowBatteryDurationS || 0);
      batteryLowWarnEl.textContent = `Low Battery ${Number(latestBatteryV || 0).toFixed(2)}V (${dur})`;
    }
  }
}

function syncStreamStatusLine(forceStalled = false) {
  const raw = String(liveStatusEl?.textContent || '');
  const cleaned = raw.replace(/^stream:\s*/i, '').trim() || 'WebRTC (RTP/UDP via SFU)';
  const noStreamText = cleaned.toLowerCase().includes('unavailable')
    || cleaned.toLowerCase().includes('nostream')
    || cleaned.toLowerCase().includes('blocked')
    || cleaned.toLowerCase().includes('proxy status unavailable');
  const stalled = !!forceStalled || noStreamText || latestFps < 0.3;
  if (streamDetailEl) streamDetailEl.textContent = cleaned;
  if (streamStatePillEl) {
    streamStatePillEl.textContent = stalled ? 'STALLED' : 'LIVE';
    streamStatePillEl.classList.toggle('stalled', stalled);
  }
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

const yawGroup = new THREE.Group();
const bodyTiltGroup = new THREE.Group();
const dogGroup = new THREE.Group();
scene.add(yawGroup);
yawGroup.add(bodyTiltGroup);
bodyTiltGroup.add(dogGroup);
const axisYawGroup = new THREE.Group();
const axisTiltGroup = new THREE.Group();
scene.add(axisYawGroup);
axisYawGroup.add(axisTiltGroup);
axisYawGroup.position.set(-2.8, 0.55, 0);
const axisHelper = new THREE.AxesHelper(1.1);
axisTiltGroup.add(axisHelper);
const axisOrigin = new THREE.Mesh(
  new THREE.SphereGeometry(0.06, 12, 8),
  new THREE.MeshStandardMaterial({ color: 0xe6f2ff, roughness: 0.3, metalness: 0.1 }),
);
axisTiltGroup.add(axisOrigin);

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
if (modelAlertEl) {
  modelAlertEl.style.display = 'none';
  modelAlertEl.textContent = '';
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
          // Align model length to +X to match simple placeholder orientation.
          let box = new THREE.Box3().setFromObject(obj);
          const size = new THREE.Vector3();
          box.getSize(size);
          if (size.z > size.x) {
            obj.rotation.y += Math.PI / 2;
          }

          // Correct base roll so the model stands upright on the ground plane.
          obj.rotation.z += Math.PI / 2;

          box = new THREE.Box3().setFromObject(obj);
          const center = new THREE.Vector3();
          box.getCenter(center);
          obj.position.sub(center);
          box = new THREE.Box3().setFromObject(obj);
          obj.position.y -= box.min.y;

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
        if (modelAlertEl) {
          modelAlertEl.style.display = 'none';
          modelAlertEl.textContent = '';
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
        if (modelAlertEl) {
          modelAlertEl.style.display = 'block';
          modelAlertEl.textContent = `3D model error: ${err?.message || 'failed to load Pug.obj'}`;
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
    if (modelAlertEl) {
      modelAlertEl.style.display = 'block';
      modelAlertEl.textContent = `3D model error: ${err?.message || 'failed to load Pug.mtl'}`;
    }
  }
);

const target = { roll: 0, pitch: 0, yaw: 0 };
const smooth = { roll: 0, pitch: 0, yaw: 0 };
const alpha = 0.15;
const imuMap = Object.freeze({
  rollFrom: 'pitch',
  pitchFrom: 'roll',
  yawFrom: 'yaw',
});
const BASIC_IMU_MODE = true;
const orientationToolsEl = document.getElementById('orientation-tools');
const yawTrack = {
  hasPrevRaw: false,
  prevRaw: 0,
  unwrapped: 0,
};
let yawNorthOffsetDeg = 0;
let lastSensorYawRawDeg = 0;
let usePiNativeAxis = false;
let imuSeeded = false;
let imuWasLive = false;
const offlineState = {
  consecutiveFailures: 0,
  lastOkMs: 0,
  noticeReason: '',
};
const OFFLINE_NOTICE_THRESHOLD = 10; // ~1s at 100ms polling
const IMU_STALE_MS = 1000;
const TUNING_STORAGE_KEY = 'imu_color_orientation_tuning_v1';
const defaultOrientationTuning = Object.freeze({
  invRoll: false,
  invPitch: false,
  invYaw: false,
  offRoll: 0,
  offPitch: 0,
  offYaw: 0,
});
const orientationTuning = loadOrientationTuning();

function clampOffset(v) {
  if (!Number.isFinite(v)) return 0;
  return Math.max(-180, Math.min(180, v));
}

function loadOrientationTuning() {
  return { ...defaultOrientationTuning };
}

function saveOrientationTuning() {
  // Intentionally no-op in basic mode.
}

function syncOrientationTuningUi() {
  if (invRollEl) invRollEl.checked = !!orientationTuning.invRoll;
  if (invPitchEl) invPitchEl.checked = !!orientationTuning.invPitch;
  if (invYawEl) invYawEl.checked = !!orientationTuning.invYaw;
  if (offRollEl) offRollEl.value = String(Number(orientationTuning.offRoll).toFixed(1));
  if (offPitchEl) offPitchEl.value = String(Number(orientationTuning.offPitch).toFixed(1));
  if (offYawEl) offYawEl.value = String(Number(orientationTuning.offYaw).toFixed(1));
}

function applyOrientationTuning(mapped) {
  if (BASIC_IMU_MODE) {
    return {
      roll: mapped.roll,
      pitch: mapped.pitch,
      yawRaw: mapped.yawRaw,
    };
  }
  const rollSigned = orientationTuning.invRoll ? -mapped.roll : mapped.roll;
  const pitchSigned = orientationTuning.invPitch ? -mapped.pitch : mapped.pitch;
  const yawRawSigned = orientationTuning.invYaw ? -mapped.yawRaw : mapped.yawRaw;
  return {
    roll: rollSigned + orientationTuning.offRoll,
    pitch: pitchSigned + orientationTuning.offPitch,
    yawRaw: yawRawSigned + orientationTuning.offYaw,
  };
}

function degToRad(d) {
  return (d * Math.PI) / 180;
}

function shortestDegDelta(nextDeg, prevDeg) {
  let d = nextDeg - prevDeg;
  while (d > 180) d -= 360;
  while (d < -180) d += 360;
  return d;
}

function smoothAngleDeg(currentDeg, targetDeg, factor) {
  const delta = shortestDegDelta(targetDeg, currentDeg);
  return currentDeg + delta * factor;
}

function fmtDeg(v) {
  return Number.isFinite(v) ? Number(v).toFixed(1) : '--';
}

function renderImuMatrix(telemetryLost = false) {
  if (telemetryLost) {
    const lost = '-.--';
    if (rawRollEl) rawRollEl.textContent = lost;
    if (rawPitchEl) rawPitchEl.textContent = lost;
    if (rawYawEl) rawYawEl.textContent = lost;
    if (modRollEl) modRollEl.textContent = lost;
    if (modPitchEl) modPitchEl.textContent = lost;
    if (modYawEl) modYawEl.textContent = lost;
    if (modelRollEl) modelRollEl.textContent = lost;
    if (modelPitchEl) modelPitchEl.textContent = lost;
    if (modelYawEl) modelYawEl.textContent = lost;
    return;
  }
  if (rawRollEl) rawRollEl.textContent = fmtDeg(rawImu.roll);
  if (rawPitchEl) rawPitchEl.textContent = fmtDeg(rawImu.pitch);
  if (rawYawEl) rawYawEl.textContent = fmtDeg(rawImu.yaw);
  if (modRollEl) modRollEl.textContent = fmtDeg(modifiedImu.roll);
  if (modPitchEl) modPitchEl.textContent = fmtDeg(modifiedImu.pitch);
  if (modYawEl) modYawEl.textContent = fmtDeg(modifiedImu.yaw);
  if (modelRollEl) modelRollEl.textContent = fmtDeg(smooth.roll);
  if (modelPitchEl) modelPitchEl.textContent = fmtDeg(smooth.pitch);
  if (modelYawEl) modelYawEl.textContent = fmtDeg(YAW_ENABLE ? smooth.yaw : 0);
}

function normalizeDeg(d) {
  let out = d;
  while (out > 180) out -= 360;
  while (out < -180) out += 360;
  return out;
}

function unwrapYaw(rawYawDeg, nowMs) {
  if (!yawTrack.hasPrevRaw) {
    yawTrack.hasPrevRaw = true;
    yawTrack.prevRaw = rawYawDeg;
    yawTrack.unwrapped = rawYawDeg;
    return yawTrack.unwrapped;
  }
  const delta = shortestDegDelta(rawYawDeg, yawTrack.prevRaw);
  yawTrack.prevRaw = rawYawDeg;
  yawTrack.unwrapped += delta;
  return yawTrack.unwrapped;
}

function mapImuToModel(data, nowMs) {
  const sensorRollRaw = Number(data?.roll ?? 0);
  const sensorPitchRaw = Number(data?.pitch ?? 0);
  const sensorYawRaw = Number(data?.[imuMap.yawFrom] ?? 0);
  lastSensorYawRawDeg = sensorYawRaw;
  const mapped = applyOrientationTuning({
    roll: usePiNativeAxis ? sensorRollRaw : Number(data?.[imuMap.rollFrom] ?? 0),
    pitch: usePiNativeAxis ? sensorPitchRaw : Number(data?.[imuMap.pitchFrom] ?? 0),
    yawRaw: sensorYawRaw,
  });
  const yawZeroedRaw = normalizeDeg(mapped.yawRaw - yawNorthOffsetDeg);
  return {
    roll: mapped.roll,
    pitch: mapped.pitch,
    yawRaw: yawZeroedRaw,
    yaw: unwrapYaw(yawZeroedRaw, nowMs || Date.now()),
  };
}

function renderCompactImu(stale = false) {
  if (imuOverlayEl) {
    imuOverlayEl.classList.toggle('stale', !!stale);
  }
  if (!imuCompactEl) return;
  if (!imuSeeded) {
    imuCompactEl.textContent = 'Pitch --  Roll --  Yaw --';
    return;
  }
  const pitchTxt = Number.isFinite(smooth.pitch) ? smooth.pitch.toFixed(1) : '--';
  const rollTxt = Number.isFinite(smooth.roll) ? smooth.roll.toFixed(1) : '--';
  const yawTxt = Number.isFinite(smooth.yaw) ? smooth.yaw.toFixed(1) : '--';
  imuCompactEl.textContent = `Pitch ${pitchTxt}  Roll ${rollTxt}  Yaw ${yawTxt}`;
}

function setImuTelemetryLostUi(isLost) {
  if (imuTelemetryLostState === !!isLost) return;
  imuTelemetryLostState = !!isLost;
  if (imuStatusBoxEl) imuStatusBoxEl.classList.toggle('telemetry-lost', imuTelemetryLostState);
  if (imuStatusHeadEl) {
    imuStatusHeadEl.textContent = imuTelemetryLostState
      ? 'IMU Attitude -- Telemetry Lost --'
      : 'IMU Attitude';
  }
  renderTopTelemetryLine();
}

function isImuStale(nowMs) {
  const lastOk = Number(offlineState.lastOkMs || 0);
  if (!lastOk) return true;
  return (nowMs - lastOk) > IMU_STALE_MS;
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
  latestBatteryV = battery;
  if (typeof data?.battery_warn_v === 'number') {
    batteryWarnV = Number(data.battery_warn_v);
  }
  if (typeof data?.low_battery === 'boolean') {
    latestLowBatteryActive = !!data.low_battery;
  }
  if (typeof data?.low_battery_duration_s === 'number') {
    latestLowBatteryDurationS = Number(data.low_battery_duration_s || 0);
  }
  if (typeof data?.low_battery_policy === 'string') {
    latestLowBatteryPolicy = String(data.low_battery_policy || '');
  }

  if (powerEl) {
    powerEl.textContent = powerText;
  }
  if (rangeEl) {
    rangeEl.textContent = rangeText;
  }
  renderBatteryStateLine();
  renderTopTelemetryLine();
  renderBatteryTrendOverlay();
}

function updateDiag(data) {
  const hostIp = String(data?.control_display_host || data?.pi_host || '--');
  const hostPort = Number(data?.control_display_port ?? data?.pi_port ?? 0);
  const host = hostPort > 0 ? `${hostIp}:${hostPort}` : hostIp;
  const ok = data?.last_ok_ts ? 'ok' : 'no link';
  diagEl.textContent = `${ok} @ ${host}`;
  if (portsMapEl) {
    portsMapEl.textContent = String(data?.ports_summary || '--');
  }
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
    const version = data?.version || '--';
    const tsText = data?.ts ? new Date(data.ts * 1000).toLocaleString() : '--';
    versionEl.textContent = version;
    versionTimeEl.textContent = tsText;
    if (buildBadgeEl) {
      buildBadgeEl.textContent = `Build: ${version} | ${tsText}`;
    }
  } catch (e) {
    versionEl.textContent = 'version error';
    versionTimeEl.textContent = '--';
    if (buildBadgeEl) {
      buildBadgeEl.textContent = 'Build: unavailable';
    }
  }
}

function setVisionConfigStatus(msg, isError = false) {
  if (!visionConfigStatusEl) return;
  visionConfigStatusEl.textContent = msg || '--';
  visionConfigStatusEl.style.color = isError ? '#ff8080' : '#9fb1c4';
}

function syncVisionConfigUi(cfg) {
  if (!cfg) return;
  if (visionImgszEl) {
    const imgszText = String(cfg.imgsz ?? 320);
    const hasOption = Array.from(visionImgszEl.options || []).some((opt) => String(opt.value) === imgszText);
    if (!hasOption) {
      const opt = document.createElement('option');
      opt.value = imgszText;
      opt.textContent = imgszText;
      visionImgszEl.appendChild(opt);
    }
    visionImgszEl.value = imgszText;
  }
  if (visionIntervalNEl) visionIntervalNEl.value = String(cfg.interval_n ?? 5);
  if (visionMinFpsEl) visionMinFpsEl.value = String(cfg.min_stream_fps ?? 20);
  if (visionAutoDegradeEl) visionAutoDegradeEl.value = String(!!cfg.auto_degrade);
}

function syncVideoProfileUi(profile) {
  if (!videoProfileEl) return;
  const value = String(profile || '960x540');
  const hasOption = Array.from(videoProfileEl.options || []).some((opt) => String(opt.value) === value);
  if (!hasOption) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = value;
    videoProfileEl.appendChild(opt);
  }
  videoProfileEl.value = value;
  videoProfileEl.dataset.serverProfile = value;
}

function clearVideoProfileResyncTimers() {
  for (const id of videoProfileResyncTimers) {
    clearTimeout(id);
  }
  videoProfileResyncTimers = [];
}

function scheduleVideoProfileResync() {
  if (!videoProfileEl) return;
  clearVideoProfileResyncTimers();
  for (const delay of VIDEO_PROFILE_RESYNC_DELAYS_MS) {
    const timerId = setTimeout(() => {
      fetchVideoConfig();
    }, delay);
    videoProfileResyncTimers.push(timerId);
  }
}

async function fetchVisionConfig() {
  try {
    const res = await fetch('/vision/config', { cache: 'no-store' });
    const data = await res.json();
    if (!data?.ok) {
      setVisionConfigStatus(`Vision config load failed: ${data?.error || 'unknown'}`, true);
      return;
    }
    syncVisionConfigUi(data.config);
    const c = data.config || {};
    setVisionConfigStatus(`Vision cfg: imgsz=${c.imgsz} N=${c.interval_n} minFps=${c.min_stream_fps} auto=${c.auto_degrade ? 'on' : 'off'} yolo=${c.yolo_enabled ? 'on' : 'off'} track=${c.tracking_enabled ? 'on' : 'off'}`);
  } catch (e) {
    setVisionConfigStatus('Vision config endpoint unavailable', true);
  }
}

async function fetchVideoConfig() {
  if (!videoProfileEl) return;
  try {
    const res = await fetch('/video/config', { cache: 'no-store' });
    const data = await res.json();
    if (!data?.ok) return;
    syncVideoProfileUi(data?.config?.profile || '960x540');
  } catch (e) {
    // non-fatal for runtime
  }
}

async function applyVideoConfig() {
  if (!videoProfileEl) return;
  const profile = String(videoProfileEl.value || '960x540');
  try {
    const res = await fetch('/video/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    });
    const data = await res.json();
    if (data?.ok) {
      const appliedProfile = data?.config?.profile || profile;
      syncVideoProfileUi(appliedProfile);
      const apply = data?.config?.publisher_apply || {};
      const restartAttempted = !!apply?.restart_attempted;
      const restartOk = !!apply?.restart_ok;
      const restartErr = String(apply?.restart_error || '').trim();
      let note = '';
      if (restartAttempted && restartOk) {
        note = ' (saved + publisher restarted; WebRTC should switch shortly)';
      } else if (restartAttempted && !restartOk) {
        const compactErr = restartErr ? `: ${restartErr.slice(0, 80)}` : '';
        note = ` (saved, auto-restart failed${compactErr}; run: sudo systemctl restart robot-publisher.service)`;
      } else {
        note = ' (saved; apply on next publisher restart/power cycle)';
      }
      setVisionConfigStatus(`Applied: video=${appliedProfile}${note}`);
      scheduleVideoProfileResync();
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('robotdog-video-profile-applied', {
          detail: {
            profile: appliedProfile,
            restart_ok: restartOk,
            restart_attempted: restartAttempted,
          },
        }));
      }, restartOk ? 1800 : 0);
      return;
    }
    setVisionConfigStatus(`Video profile apply failed: ${data?.error || 'unknown'}`, true);
  } catch (e) {
    setVisionConfigStatus('Video profile apply failed: endpoint unavailable', true);
  }
}

async function applyVisionConfig() {
  const payload = {
    imgsz: Number(visionImgszEl?.value || 320),
    interval_n: Number(visionIntervalNEl?.value || 5),
    min_stream_fps: Number(visionMinFpsEl?.value || 20),
    auto_degrade: String(visionAutoDegradeEl?.value || 'true') === 'true',
  };
  setVisionConfigStatus('Applying vision config...');
  try {
    const res = await fetch('/vision/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!data?.ok) {
      setVisionConfigStatus(`Apply failed: ${data?.error || 'unknown'}`, true);
      return;
    }
    syncVisionConfigUi(data.config);
    const c = data.config || {};
    setVisionConfigStatus(`Applied: imgsz=${c.imgsz} N=${c.interval_n} minFps=${c.min_stream_fps} auto=${c.auto_degrade ? 'on' : 'off'} yolo=${c.yolo_enabled ? 'on' : 'off'} track=${c.tracking_enabled ? 'on' : 'off'}`);
  } catch (e) {
    setVisionConfigStatus('Apply failed: endpoint unavailable', true);
  }
}

function bindVisionConfigControls() {
  if (visionConfigApplyEl) {
    visionConfigApplyEl.addEventListener('click', () => {
      applyVisionConfig();
      applyVideoConfig();
    });
  }
  if (visionConfigReloadEl) {
    visionConfigReloadEl.addEventListener('click', () => {
      fetchVisionConfig();
      fetchVideoConfig();
    });
  }
}

function clientAiApiBase() {
  const proto = window.location.protocol === 'https:' ? 'https:' : 'http:';
  const host = window.location.hostname || '192.168.0.32';
  return `${proto}//${host}:8090`;
}

function detectClientAiCapability() {
  const hasWebGpu = !!(navigator && navigator.gpu);
  const hasWasm = typeof WebAssembly === 'object';
  return {
    client_ai_capable: hasWebGpu || hasWasm,
    provider: hasWebGpu ? 'webgpu' : (hasWasm ? 'wasm' : 'unknown'),
  };
}

function setClientAiStatus(msg, isError = false) {
  if (!clientAiStatusEl) return;
  clientAiStatusEl.textContent = msg || '--';
  clientAiStatusEl.style.color = isError ? '#ff8080' : '#9fb1c4';
}

function renderClientAiStatus(st) {
  if (!st) return;
  clientAiStatus = st;
  refreshVisionMetricsHeader();
  if (clientAiRequestedEl) clientAiRequestedEl.value = String(st.requested_mode || '--');
  if (clientAiActiveEl) clientAiActiveEl.value = String(st.active_mode || '--');
  if (clientAiFallbackEl) clientAiFallbackEl.value = String(st.fallback_reason || 'none');
  if (clientAiProviderEl) clientAiProviderEl.value = String(st.provider || '--');
  if (clientAiModelEl) clientAiModelEl.value = getClientAiDisplayModelLabel();
  const serverInferMs = Number(st?.last_target?.infer_ms);
  const inferMs = Number.isFinite(serverInferMs) ? serverInferMs : Number(clientAiRuntime.lastInferMs);
  if (clientAiInferMsEl) clientAiInferMsEl.value = Number.isFinite(inferMs) ? inferMs.toFixed(1) : '--';
  if (vmClientAiInferMsEl) vmClientAiInferMsEl.textContent = Number.isFinite(inferMs) ? inferMs.toFixed(1) : '--';
  if (vmClientAiModelEl) vmClientAiModelEl.textContent = getClientAiDisplayModelLabel();
  const accepted = Number(st.accepted_count || 0);
  const rejected = Number(st.rejected_count || 0);
  if (clientAiPublishCountsEl) {
    clientAiPublishCountsEl.value = `accepted:${accepted} / rejected:${rejected} / local_skip:${clientAiRuntime.postSkipUnarmed}`;
  }
  if (clientAiModeEl && st.requested_mode) clientAiModeEl.value = String(st.requested_mode);
  if (clientAiModelChoiceEl) clientAiModelChoiceEl.value = resolveClientAiModelChoice(clientAiRuntime.modelChoice);
  const modeText = st.manual_override ? 'manual' : 'auto';
  const err = clientAiRuntime.lastError ? `, localErr=${clientAiRuntime.lastError}` : '';
  const armedText = clientAiRuntime.sessionKnown
    ? (clientAiRuntime.sessionArmed ? 'armed' : 'unarmed')
    : 'session?';
  const lastReject = String(st.last_reject || '').trim();
  const rejectReason = lastReject || (rejected > 0 ? 'unknown' : 'none');
  const skipHint = clientAiRuntime.sessionKnown && !clientAiRuntime.sessionArmed
    ? ', unarmed -> local_skip increments (no server post)'
    : '';
  setClientAiStatus(
    `ClientAI ${st.active_mode || '--'} (${modeText}), ${armedText}, provider=${st.provider || '--'}, capable=${st.client_ai_capable ? 'yes' : 'no'}, local infer=${clientAiRuntime.inferSuccess}/${clientAiRuntime.inferAttempts}, local post ok/fail=${clientAiRuntime.postOk}/${clientAiRuntime.postFail}, local_skip=${clientAiRuntime.postSkipUnarmed}, server accepted/rejected=${accepted}/${rejected}, server_last_reject=${rejectReason}${skipHint}${err}`,
    !!clientAiRuntime.lastError,
  );
}

async function pollClientSessionStatus() {
  try {
    const res = await fetch(`${clientAiApiBase()}/api/session`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data?.ok) throw new Error(data?.error || 'session_status_error');
    clientAiRuntime.sessionArmed = !!data.armed;
    clientAiRuntime.sessionKnown = true;
  } catch (e) {
    clientAiRuntime.sessionKnown = false;
  }
}

async function pollClientAiStatus() {
  if (!clientAiStatusEl) return;
  try {
    const res = await fetch(`${clientAiApiBase()}/api/clientai`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data?.ok) throw new Error(data?.error || 'clientai status error');
    renderClientAiStatus(data);
  } catch (e) {
    setClientAiStatus('ClientAI status unavailable', true);
  }
}

async function pollClientTargetLatest() {
  try {
    const res = await fetch(`${clientAiApiBase()}/api/vision/client-target/latest`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data?.ok) throw new Error(data?.error || 'target snapshot error');
    latestClientTargetSnapshot = data;
    renderVisionTargetOverlay(latestVisionState);
  } catch (e) {
    latestClientTargetSnapshot = null;
    renderVisionTargetOverlay(latestVisionState);
  }
}

async function postClientAiState(patch = {}) {
  const capability = detectClientAiCapability();
  const body = {
    ...capability,
    model_id: getClientAiStateModelId(),
    ...patch,
  };
  const res = await fetch(`${clientAiApiBase()}/api/clientai`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.ok) {
    throw new Error(data?.error || `HTTP ${res.status}`);
  }
  renderClientAiStatus(data);
}

function bindClientAiControls() {
  if (!clientAiStatusEl) return;
  if (clientAiModelChoiceEl) {
    clientAiModelChoiceEl.addEventListener('change', async () => {
      clientAiRuntime.modelChoice = resolveClientAiModelChoice(clientAiModelChoiceEl.value);
      latestClientAiLocalDetections = [];
      clearClientAiModelSessions();
      try {
        await ensureClientAiModelReady();
      } catch (e) {
        clientAiRuntime.lastError = String(e?.message || e || 'model_switch_failed');
      }
      renderVisionTargetOverlay(latestVisionState);
    });
  }
  if (clientAiApplyEl) {
    clientAiApplyEl.addEventListener('click', async () => {
      try {
        await postClientAiState({
          mode: String(clientAiModeEl?.value || 'edge-ai'),
          model_id: getClientAiStateModelId(),
        });
      } catch (e) {
        setClientAiStatus(`ClientAI apply failed: ${e.message || e}`, true);
      }
    });
  }
  if (clientAiAutoEl) {
    clientAiAutoEl.addEventListener('click', async () => {
      try {
        await postClientAiState({ action: 'reset_auto' });
      } catch (e) {
        setClientAiStatus(`ClientAI auto failed: ${e.message || e}`, true);
      }
    });
  }
}

function bindClientAiDebugControls() {
  const els = [
    debugDetectEnableEl,
    debugRawConfEl,
    debugIouNmsEl,
    debugMaxDetEl,
    debugLogConsoleEl,
    debugLogPanelEl,
    debugHeuristicsEnableEl,
    debugRoiEnableEl,
    debugRoiGateYEl,
    debugSizeEnableEl,
    debugMinAreaEl,
    debugMaxAreaEl,
  ];
  els.forEach((el) => {
    if (!el) return;
    el.addEventListener('change', () => {
      syncClientAiDebugConfigFromUi();
      if (!clientAiRuntime.debug.enabled) {
        hideDebugRawOverlay();
      }
    });
    el.addEventListener('input', () => {
      syncClientAiDebugConfigFromUi();
    });
  });
  syncClientAiDebugConfigFromUi();
}

let lastClientAiCapabilitySyncMs = 0;
async function syncClientAiCapabilityAuto() {
  const now = Date.now();
  if ((now - lastClientAiCapabilitySyncMs) < 3000) return;
  lastClientAiCapabilitySyncMs = now;
  try {
    await postClientAiState({});
  } catch (e) {
    // Non-fatal: polling path still updates display and fallback status.
  }
}

function renderVisionMetrics(metrics) {
  if (!metrics) return;
  refreshVisionMetricsHeader();
  if (vmStreamFpsEl) vmStreamFpsEl.textContent = Number.isFinite(metrics.client_stream_fps) ? Number(metrics.client_stream_fps).toFixed(1) : '--';
  if (vmMinFpsEl) vmMinFpsEl.textContent = Number.isFinite(metrics.min_stream_fps) ? Number(metrics.min_stream_fps).toFixed(1) : '--';
  if (vmKpiStatusEl) vmKpiStatusEl.textContent = String(metrics.kpi_status || '--');
  if (vmImgszEl) vmImgszEl.textContent = String(metrics.imgsz ?? '--');
  if (vmIntervalNEl) vmIntervalNEl.textContent = String(metrics.interval_n ?? '--');
  if (vmAutoDegradeEl) vmAutoDegradeEl.textContent = metrics.auto_degrade ? 'on' : 'off';
  if (vmThrottleActionEl) vmThrottleActionEl.textContent = String(metrics.last_throttle_action || '--');
  if (vmThrottleCountEl) vmThrottleCountEl.textContent = String(metrics.throttle_count ?? '--');
  if (vmStreamPrefEl) vmStreamPrefEl.textContent = String(metrics.server_preferred_stream || '--');
  if (vmMjpegFpsEl) vmMjpegFpsEl.textContent = Number.isFinite(metrics.server_mjpeg_fps) ? Number(metrics.server_mjpeg_fps).toFixed(1) : '--';
  if (vmClientAgeEl) vmClientAgeEl.textContent = Number.isFinite(metrics.client_metric_age_s) ? `${Number(metrics.client_metric_age_s).toFixed(1)}s` : '--';
  if (vmVisionModeEl) vmVisionModeEl.textContent = metrics.yolo_enabled ? (metrics.tracking_enabled ? 'tracking' : 'detect_only') : 'disabled';
}

function syncVisionButtons(state) {
  if (!state) return;
  const activeMode = String(clientAiStatus?.active_mode || '').toLowerCase();
  const clientMode = activeMode === 'client-ai';
  const yoloOn = !!state.yolo_enabled;
  const forcedYoloOn = clientMode ? false : yoloOn;
  const trackingOn = !!state.tracking_enabled;
  if (clientMode && yoloOn && !clientAiEdgeDisableInFlight) {
    clientAiEdgeDisableInFlight = true;
    sendVisionStateAction('toggle_yolo').finally(() => {
      clientAiEdgeDisableInFlight = false;
    });
  }
  if (toggleYoloEl) {
    toggleYoloEl.dataset.state = forcedYoloOn ? 'on' : 'off';
    toggleYoloEl.textContent = clientMode ? 'Vision AI LOCKED OFF' : (forcedYoloOn ? 'Yolo Vision ON' : 'Yolo Vision OFF');
    toggleYoloEl.classList.toggle('green', forcedYoloOn);
    toggleYoloEl.classList.remove('placeholder');
    toggleYoloEl.disabled = clientMode;
  }
  if (toggleTrackingEl) {
    const trkOn = clientMode ? false : trackingOn;
    toggleTrackingEl.dataset.state = trkOn ? 'on' : 'off';
    toggleTrackingEl.textContent = trkOn ? 'Tracking ON' : 'Tracking OFF';
    toggleTrackingEl.classList.toggle('blue', trkOn);
    toggleTrackingEl.classList.remove('placeholder');
    toggleTrackingEl.disabled = clientMode || !forcedYoloOn;
  }
  if (vmVisionModeEl) vmVisionModeEl.textContent = String(state.state || '--');
  if (vmTargetCountEl) vmTargetCountEl.textContent = String(state.target_count ?? '--');
  if (vmDetFpsEl) vmDetFpsEl.textContent = Number.isFinite(state.det_fps) ? Number(state.det_fps).toFixed(1) : '--';
  const inferModel = inferModelAlias(state);
  if (vmInferKeyEl) vmInferKeyEl.textContent = clientMode ? 'ClientAI Infer (ms)' : 'Infer (ms)';
  if (clientMode) {
    const serverInferMs = Number(clientAiStatus?.last_target?.infer_ms);
    const clientInferMs = Number.isFinite(serverInferMs) ? serverInferMs : Number(clientAiRuntime.lastInferMs);
    if (vmInferModelEl) vmInferModelEl.textContent = getClientAiDisplayModelLabel();
    if (vmInferMsEl) vmInferMsEl.textContent = Number.isFinite(clientInferMs) ? clientInferMs.toFixed(1) : '--';
  } else {
    if (vmInferModelEl) vmInferModelEl.textContent = inferModel;
    if (vmInferMsEl) vmInferMsEl.textContent = Number.isFinite(state.infer_ms) ? Number(state.infer_ms).toFixed(1) : '--';
  }
  if (vmVisionHealthEl) vmVisionHealthEl.textContent = String(state.health || '--');
  if (vmVisionErrorEl) vmVisionErrorEl.textContent = String(state.error || '--');
  renderVisionTargetOverlay(state);
}

function inferModelAlias(state) {
  const path = String(state?.model_path || '').toLowerCase();
  const backend = String(state?.model_backend || '').toLowerCase();
  const src = `${backend}|${path}`;
  if (src.includes('best')) return 'best';
  if (src.includes('yolov8n') || src.includes('yolo11n')) return 'yolov8n';
  if (src.includes('onnx')) return 'onnx';
  return 'unknown';
}

function clamp01(v) {
  return Math.max(0, Math.min(1, Number(v) || 0));
}

function normalizeClientAiLabel(labelLike, source = '') {
  const raw = String(labelLike || '').trim().toLowerCase().replace(/[_-]+/g, ' ');
  const src = String(source || '').trim().toLowerCase();
  if (raw === 'mt ball' || raw === 'mt_ball' || raw === 'mt-ball') return 'MT_ball';
  if (raw === 'sports ball' || raw === 'sport ball' || raw === 'sport_ball' || raw === 'sport-ball') return 'Yolo_Sport_Ball';
  if (raw === 'dog') return 'Dog';
  if (raw === 'person') return 'Person';
  if (raw === 'cat') return 'Cat';
  if (src === 'mt') return 'MT_ball';
  if (src === 'yolo' && raw === 'ball') return 'Yolo_Sport_Ball';
  return String(labelLike || 'target');
}

function clientAiClassPriority(label) {
  const norm = normalizeClientAiLabel(label);
  if (norm === 'MT_ball') return 0;
  if (norm === 'Yolo_Sport_Ball') return 1;
  if (norm === 'Dog') return 2;
  return 9;
}

function styleVisionBox(boxEl, labelEl, label) {
  const style = CLIENTAI_BOX_STYLE[normalizeClientAiLabel(label)] || CLIENTAI_BOX_STYLE._default;
  boxEl.style.border = `2px solid ${style.border}`;
  if (labelEl) {
    labelEl.style.background = style.labelBg;
    labelEl.style.color = style.labelFg;
  }
}

function hideVisionTargetOverlay() {
  if (visionTargetBoxEl) visionTargetBoxEl.style.display = 'none';
  if (visionTargetOverlayEl) {
    const extras = visionTargetOverlayEl.querySelectorAll('.vision-target-box-extra');
    extras.forEach((el) => el.remove());
  }
}

function getVisionBoxPair(index) {
  if (index === 0) {
    return { boxEl: visionTargetBoxEl, labelEl: visionTargetLabelEl };
  }
  if (!visionTargetOverlayEl) return { boxEl: null, labelEl: null };
  const id = `vision-target-box-extra-${index}`;
  let boxEl = visionTargetOverlayEl.querySelector(`#${id}`);
  let labelEl = boxEl ? boxEl.querySelector('.vision-target-label-extra') : null;
  if (!boxEl) {
    boxEl = document.createElement('div');
    boxEl.id = id;
    boxEl.className = 'vision-target-box-extra';
    boxEl.style.position = 'absolute';
    boxEl.style.boxShadow = '0 0 0 1px rgba(0,0,0,.35) inset';
    boxEl.style.borderRadius = '4px';
    boxEl.style.display = 'none';
    labelEl = document.createElement('div');
    labelEl.className = 'vision-target-label-extra';
    labelEl.style.position = 'absolute';
    labelEl.style.top = '-22px';
    labelEl.style.left = '0';
    labelEl.style.fontSize = '12px';
    labelEl.style.borderRadius = '4px';
    labelEl.style.padding = '2px 6px';
    labelEl.style.whiteSpace = 'nowrap';
    boxEl.appendChild(labelEl);
    visionTargetOverlayEl.appendChild(boxEl);
  }
  return { boxEl, labelEl };
}

function normalizeRenderDetections(detections = []) {
  const out = [];
  detections.forEach((item) => {
    const conf = Number(item?.conf);
    if (!Number.isFinite(conf)) return;
    const x1 = clamp01(item?.x1);
    const y1 = clamp01(item?.y1);
    const x2 = clamp01(item?.x2);
    const y2 = clamp01(item?.y2);
    const w = clamp01(x2 - x1);
    const h = clamp01(y2 - y1);
    if (w <= 0 || h <= 0) return;
    const label = normalizeClientAiLabel(item?.label, item?.source);
    out.push({
      label,
      conf: Math.max(0, Math.min(1, conf)),
      x1,
      y1,
      x2,
      y2,
      source: String(item?.source || ''),
    });
  });
  return out;
}

function renderClientAiDetectionsOverlay(detections, tag) {
  const norm = normalizeRenderDetections(detections).slice(0, CLIENTAI_MAX_RENDER_CLASSES);
  hideVisionTargetOverlay();
  if (norm.length === 0) return false;
  norm.forEach((det, idx) => {
    const pair = getVisionBoxPair(idx);
    if (!pair.boxEl) return;
    pair.boxEl.style.display = 'block';
    pair.boxEl.style.left = `${det.x1 * 100}%`;
    pair.boxEl.style.top = `${det.y1 * 100}%`;
    pair.boxEl.style.width = `${(det.x2 - det.x1) * 100}%`;
    pair.boxEl.style.height = `${(det.y2 - det.y1) * 100}%`;
    styleVisionBox(pair.boxEl, pair.labelEl, det.label);
    if (pair.labelEl) {
      pair.labelEl.textContent = `${det.label} ${det.conf.toFixed(2)} ${tag}`;
    }
  });
  const top = norm[0];
  setClientAiDetectBanner(`DETECTED: ${top.label} ${top.conf.toFixed(2)} ${tag}`, true);
  return true;
}

function renderVisionTargetOverlay(state) {
  if (!visionTargetBoxEl) return;
  if (!clientAiRuntime.debug.enabled) {
    hideDebugRawOverlay();
  }
  const activeMode = String(clientAiStatus?.active_mode || '').toLowerCase();
  if (activeMode === 'client-ai') {
    const consumer = latestClientTargetSnapshot?.tracking_consumer;
    const target = consumer?.target;
    const eligible = !!consumer?.eligible && !!target;
    const tsClientMs = Number(target?.ts_client_ms || 0);
    const ageMs = Date.now() - tsClientMs;
    const targetDetections = Array.isArray(target?.detections) ? target.detections : (target?.top_detection ? [target.top_detection] : []);
    const conf = Number(target?.top_detection?.conf);
    const fresh = Number.isFinite(ageMs) && ageMs >= -500 && ageMs <= CLIENT_TARGET_MAX_AGE_MS;
    if (eligible && fresh && Number.isFinite(conf) && conf >= TARGET_RENDER_MIN_CONF) {
      if (renderClientAiDetectionsOverlay(targetDetections, '[client]')) return;
    }
    const localTop = latestClientAiLocalDetections[0];
    const localAgeMs = localTop ? (Date.now() - Number(localTop.ts_client_ms || 0)) : Number.POSITIVE_INFINITY;
    const localFresh = Number.isFinite(localAgeMs) && localAgeMs >= -500 && localAgeMs <= CLIENTAI_LOCAL_TARGET_MAX_AGE_MS;
    const localConf = Number(localTop?.conf);
    if (!localTop || !localFresh || !Number.isFinite(localConf) || localConf < CLIENTAI_LOCAL_RENDER_MIN_CONF) {
      hideVisionTargetOverlay();
      setClientAiDetectBanner('SEARCHING: no confident target', true);
      return;
    }
    renderClientAiDetectionsOverlay(latestClientAiLocalDetections, '[local]');
    return;
  }
  setClientAiDetectBanner('', false);
  if (state?.stale || String(state?.state || '') === 'stale') {
    hideVisionTargetOverlay();
    return;
  }
  const targets = Array.isArray(state?.targets) ? state.targets : [];
  const first = targets.length > 0 ? targets[0] : null;
  if (!first || !Array.isArray(first.bbox) || first.bbox.length < 4) {
    hideVisionTargetOverlay();
    return;
  }
  const firstConf = Number(first.conf);
  if (!Number.isFinite(firstConf) || firstConf < TARGET_RENDER_MIN_CONF) {
    hideVisionTargetOverlay();
    return;
  }
  const nx = clamp01(first.bbox[0]);
  const ny = clamp01(first.bbox[1]);
  const nw = clamp01(first.bbox[2]);
  const nh = clamp01(first.bbox[3]);
  const xPct = nx * 100;
  const yPct = ny * 100;
  const wPct = nw * 100;
  const hPct = nh * 100;
  hideVisionTargetOverlay();
  visionTargetBoxEl.style.display = 'block';
  styleVisionBox(visionTargetBoxEl, visionTargetLabelEl, 'MT_ball');
  visionTargetBoxEl.style.left = `${xPct}%`;
  visionTargetBoxEl.style.top = `${yPct}%`;
  visionTargetBoxEl.style.width = `${wPct}%`;
  visionTargetBoxEl.style.height = `${hPct}%`;
  if (visionTargetLabelEl) {
    const cls = String(first.class ?? 'target');
    const conf = Number.isFinite(first.conf) ? Number(first.conf).toFixed(2) : '--';
    const source = String(first.source || '');
    const tag = source === 'tracking_hold' ? ' [trk]' : '';
    visionTargetLabelEl.textContent = `${cls} ${conf}${tag}`;
  }
}

function clampByteSize(v, fallback = 256) {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(160, Math.min(960, Math.round(n)));
}

function inferClientAiInputSize(modelName, modelDim, fallback = 320) {
  const dim = Number(modelDim);
  if (Number.isFinite(dim) && dim >= 160 && dim <= 960) return Math.round(dim);
  const name = String(modelName || '').toLowerCase();
  if (name.includes('cv451') || name.includes('yolov8n')) return 320;
  return clampByteSize(fallback, 320);
}

function maybeRecoverInputSizeFromOrtError(errLike) {
  const msg = String(errLike?.message || errLike || '');
  const matches = [...msg.matchAll(/Expected:\s*(\d+)/g)];
  if (matches.length === 0) return false;
  const expected = Number(matches[matches.length - 1][1]);
  if (!Number.isFinite(expected) || expected < 160 || expected > 960) return false;
  let changed = false;
  if (Number(clientAiRuntime.inputSizeBest) !== expected) {
    clientAiRuntime.inputSizeBest = expected;
    changed = true;
  }
  if (Number(clientAiRuntime.inputSizeYolo) !== expected) {
    clientAiRuntime.inputSizeYolo = expected;
    changed = true;
  }
  clientAiRuntime.inputSize = expected;
  if (!changed) return false;
  return true;
}

function inferIntervalN() {
  return Math.max(1, Math.min(24, Number(visionIntervalNEl?.value || clientAiRuntime.inferEveryN || 8)));
}

function clientAiDetLabel(index, modelName = '', source = '') {
  const model = String(modelName || '').toLowerCase();
  const src = String(source || '').toLowerCase();
  if (model.includes('best_cv451')) {
    if (Number(index) === 0) return 'MT_ball';
  }
  const labels = [
    'person','bicycle','car','motorcycle','airplane','bus','train','truck','boat','traffic light',
    'fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow',
    'elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee',
    'skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle',
    'wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange',
    'broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant','bed',
    'dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone','microwave','oven',
    'toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear','hair drier','toothbrush',
  ];
  const raw = labels[index] || `cls_${index}`;
  if (src === 'yolo' && raw === 'sports ball') return 'Yolo_Sport_Ball';
  return normalizeClientAiLabel(raw, src);
}

function isAllowedClientAiLabel(label) {
  return CLIENTAI_ALLOWED_LABELS.has(normalizeClientAiLabel(label));
}

function iouBox(a, b) {
  const x1 = Math.max(a.x1, b.x1);
  const y1 = Math.max(a.y1, b.y1);
  const x2 = Math.min(a.x2, b.x2);
  const y2 = Math.min(a.y2, b.y2);
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  const areaA = Math.max(0, a.x2 - a.x1) * Math.max(0, a.y2 - a.y1);
  const areaB = Math.max(0, b.x2 - b.x1) * Math.max(0, b.y2 - b.y1);
  const union = areaA + areaB - inter;
  return union <= 0 ? 0 : inter / union;
}

function nmsBoxes(boxes, thr = 0.45, maxDet = 20) {
  const sorted = boxes.slice().sort((a, b) => b.conf - a.conf);
  const out = [];
  while (sorted.length > 0) {
    const pick = sorted.shift();
    out.push(pick);
    for (let i = sorted.length - 1; i >= 0; i -= 1) {
      if (sorted[i].label === pick.label && iouBox(sorted[i], pick) > thr) sorted.splice(i, 1);
    }
    if (out.length >= Math.max(1, Number(maxDet || 20))) break;
  }
  return out;
}

function decodeYoloOutput(output, inputSize, confThr = 0.30, modelName = '', source = '', opts = {}) {
  if (!output || !output.data || !Array.isArray(output.dims) || output.dims.length !== 3) return [];
  const allowedOnly = opts.allowedOnly !== false;
  const iouNms = Number.isFinite(Number(opts.iouNms)) ? Number(opts.iouNms) : 0.45;
  const maxDet = Number.isFinite(Number(opts.maxDet)) ? Number(opts.maxDet) : 20;
  const dims = output.dims;
  const data = output.data;
  const d1 = Number(dims[1]);
  const d2 = Number(dims[2]);
  if (!Number.isFinite(d1) || !Number.isFinite(d2) || d1 < 5 || d2 < 5) {
    return [];
  }
  const channels = Math.min(d1, d2);
  const count = Math.max(d1, d2);
  const chanFirst = d1 === channels;
  const boxes = [];
  for (let i = 0; i < count; i += 1) {
    const base = chanFirst ? i : i * channels;
    const get = (c) => (chanFirst ? data[(c * count) + i] : data[base + c]);
    const cx = get(0);
    const cy = get(1);
    const w = get(2);
    const h = get(3);
    let bestC = -1;
    let bestV = 0;
    for (let c = 4; c < channels; c += 1) {
      const v = get(c);
      if (v > bestV) {
        bestV = v;
        bestC = c - 4;
      }
    }
    if (bestV < confThr) continue;
    const label = clientAiDetLabel(bestC, modelName, source);
    if (allowedOnly && !isAllowedClientAiLabel(label)) continue;
    const x1 = Math.max(0, Math.min(1, (cx - (w / 2)) / inputSize));
    const y1 = Math.max(0, Math.min(1, (cy - (h / 2)) / inputSize));
    const x2 = Math.max(0, Math.min(1, (cx + (w / 2)) / inputSize));
    const y2 = Math.max(0, Math.min(1, (cy + (h / 2)) / inputSize));
    boxes.push({ label, conf: Math.max(0, Math.min(1, bestV)), x1, y1, x2, y2, source });
  }
  return nmsBoxes(boxes, iouNms, maxDet);
}

function selectClientAiTopDetections(boxes, maxCount = CLIENTAI_MAX_RENDER_CLASSES) {
  if (!Array.isArray(boxes) || boxes.length === 0) return [];
  const grouped = new Map();
  boxes.forEach((item) => {
    const label = normalizeClientAiLabel(item?.label, item?.source);
    const conf = Number(item?.conf);
    if (!Number.isFinite(conf)) return;
    const x1 = clamp01(item?.x1);
    const y1 = clamp01(item?.y1);
    const x2 = clamp01(item?.x2);
    const y2 = clamp01(item?.y2);
    const area = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    if (label === 'MT_ball' && area < CLIENTAI_MT_BALL_MIN_AREA) return;
    const key = label;
    const prev = grouped.get(key);
    const next = {
      ...item,
      label,
      conf: Math.max(0, Math.min(1, conf)),
      x1,
      y1,
      x2,
      y2,
      area,
    };
    if (!prev || next.conf > Number(prev.conf || 0)) {
      grouped.set(key, next);
    }
  });
  return [...grouped.values()]
    .sort((a, b) => {
      const pa = clientAiClassPriority(a.label);
      const pb = clientAiClassPriority(b.label);
      if (pa !== pb) return pa - pb;
      return Number(b.conf || 0) - Number(a.conf || 0);
    })
    .slice(0, Math.max(1, Number(maxCount || 1)));
}

function applyClientAiClassSwitchDebounce(detections = []) {
  const state = clientAiRuntime.classSwitchState || {};
  const nowMs = Date.now();
  if (!Array.isArray(detections) || detections.length === 0) {
    state.pendingLabel = '';
    state.pendingCount = 0;
    clientAiRuntime.classSwitchState = state;
    return [];
  }

  const top = detections[0];
  const topLabel = normalizeClientAiLabel(top?.label, top?.source);
  const previousDominant = normalizeClientAiLabel(state.dominantLabel || '');

  if (topLabel === 'MT_ball') {
    state.dominantLabel = 'MT_ball';
    state.pendingLabel = '';
    state.pendingCount = 0;
    state.holdMtBall = {
      ...top,
      label: 'MT_ball',
      ts_client_ms: nowMs,
    };
    clientAiRuntime.classSwitchState = state;
    return detections;
  }

  if (previousDominant === 'MT_ball') {
    if (state.pendingLabel === topLabel) {
      state.pendingCount = Number(state.pendingCount || 0) + 1;
    } else {
      state.pendingLabel = topLabel;
      state.pendingCount = 1;
    }
    const hold = state.holdMtBall;
    const holdAgeMs = hold ? (nowMs - Number(hold.ts_client_ms || 0)) : Number.POSITIVE_INFINITY;
    if (Number(state.pendingCount || 0) < CLIENTAI_CLASS_SWITCH_CONFIRM_FRAMES && hold && holdAgeMs <= CLIENTAI_CLASS_SWITCH_HOLD_MS) {
      const retained = {
        ...hold,
        label: 'MT_ball',
        conf: Math.max(Number(top.conf || 0), Number(hold.conf || 0)),
      };
      clientAiRuntime.classSwitchState = state;
      return [retained, ...detections.slice(0, CLIENTAI_MAX_RENDER_CLASSES - 1)];
    }
  }

  state.dominantLabel = topLabel;
  state.pendingLabel = '';
  state.pendingCount = 0;
  clientAiRuntime.classSwitchState = state;
  return detections;
}

function applyClientAiBallHeuristics(detections = []) {
  const dbg = clientAiRuntime.debug;
  if (!dbg.enabled || !dbg.heuristicsEnabled) return detections;
  const ballLabels = new Set(['MT_ball', 'Yolo_Sport_Ball']);
  let cands = (Array.isArray(detections) ? detections : [])
    .filter((d) => ballLabels.has(normalizeClientAiLabel(d?.label, d?.source)))
    .map((d) => ({ ...d }));
  if (dbg.roiGateEnabled) {
    cands = cands.filter((d) => {
      const cy = (Number(d.y1 || 0) + Number(d.y2 || 0)) / 2;
      return cy > Number(dbg.roiGateY || 0.45);
    });
  }
  if (dbg.sizeGateEnabled) {
    cands = cands.filter((d) => {
      const area = Math.max(0, (Number(d.x2 || 0) - Number(d.x1 || 0)) * (Number(d.y2 || 0) - Number(d.y1 || 0)));
      return area >= Number(dbg.minArea || 0.0) && area <= Number(dbg.maxArea || 1.0);
    });
  }
  if (cands.length === 0) return [];
  cands.sort((a, b) => Number(b.conf || 0) - Number(a.conf || 0));
  return [cands[0]];
}

function computeFrameLumaStats(videoEl) {
  if (!clientAiLumaCtx || !videoEl || videoEl.videoWidth < 8 || videoEl.videoHeight < 8) {
    return { mean: null, p95: null };
  }
  const w = 96;
  const h = 54;
  clientAiLumaCanvas.width = w;
  clientAiLumaCanvas.height = h;
  clientAiLumaCtx.drawImage(videoEl, 0, 0, w, h);
  const data = clientAiLumaCtx.getImageData(0, 0, w, h).data;
  const hist = new Uint32Array(256);
  let sum = 0;
  const px = w * h;
  for (let i = 0; i < px; i += 1) {
    const o = i * 4;
    const y = Math.max(0, Math.min(255, Math.round((0.2126 * data[o]) + (0.7152 * data[o + 1]) + (0.0722 * data[o + 2]))));
    hist[y] += 1;
    sum += y;
  }
  const mean = sum / Math.max(1, px);
  let cdf = 0;
  let p95 = 255;
  const target = px * 0.95;
  for (let i = 0; i < hist.length; i += 1) {
    cdf += hist[i];
    if (cdf >= target) {
      p95 = i;
      break;
    }
  }
  return { mean: Number(mean.toFixed(2)), p95: Number(p95.toFixed(2)) };
}

function logClientAiDebugFrame(rawDetections = [], inputSize = 0) {
  const dbg = clientAiRuntime.debug;
  if (!dbg.enabled) return;
  const liveVideoEl = document.getElementById('liveVideo');
  const luma = computeFrameLumaStats(liveVideoEl);
  const detTop = (Array.isArray(rawDetections) ? rawDetections : [])
    .slice()
    .sort((a, b) => Number(b.conf || 0) - Number(a.conf || 0))
    .slice(0, CLIENTAI_DEBUG_LOG_TOPK)
    .map((d) => {
      const x1 = clamp01(d.x1);
      const y1 = clamp01(d.y1);
      const x2 = clamp01(d.x2);
      const y2 = clamp01(d.y2);
      const area = Math.max(0, (x2 - x1) * (y2 - y1));
      const cx = (x1 + x2) / 2;
      const cy = (y1 + y2) / 2;
      return {
        class: normalizeClientAiLabel(d.label, d.source),
        conf: Number(Number(d.conf || 0).toFixed(4)),
        x1: Number(x1.toFixed(4)),
        y1: Number(y1.toFixed(4)),
        x2: Number(x2.toFixed(4)),
        y2: Number(y2.toFixed(4)),
        area: Number(area.toFixed(4)),
        cx: Number(cx.toFixed(4)),
        cy: Number(cy.toFixed(4)),
      };
    });
  const payload = {
    ts: new Date().toISOString(),
    conf_thres: Number(dbg.rawConfThres),
    iou_nms: Number(dbg.iouNms),
    imgsz: Number(inputSize || 0),
    max_det: Number(dbg.maxDet),
    num_det: Array.isArray(rawDetections) ? rawDetections.length : 0,
    dets_top10: detTop,
    frame_mean_luma: luma.mean,
    frame_p95_luma: luma.p95,
  };
  if (dbg.logConsole) {
    try {
      console.log('[ClientAI Debug]', JSON.stringify(payload));
    } catch (_) {}
  }
  if (dbg.logPanel && debugDetectLogEl) {
    debugDetectLogEl.textContent = JSON.stringify(payload, null, 2);
  }
}

function applyClientAiConfidenceStability(detections = []) {
  if (!Array.isArray(detections) || detections.length === 0) return [];
  const nowMs = Date.now();
  const out = detections.map((d) => ({ ...d }));
  out.forEach((det) => {
    const label = normalizeClientAiLabel(det?.label, det?.source);
    const conf = Number(det?.conf);
    if (label !== CLIENTAI_STABLE_CONF_LABEL || !Number.isFinite(conf)) return;
    const prev = clientAiRuntime.stableByLabel[label];
    if (prev && (nowMs - Number(prev.ts_client_ms || 0)) <= CLIENTAI_STABLE_MAX_AGE_MS) {
      const prevConf = Number(prev.conf || 0);
      if (Number.isFinite(prevConf) && prevConf >= CLIENTAI_STABLE_LOCK_CONF) {
        const overlap = iouBox(prev, det);
        const floor = Math.max(0, prevConf - CLIENTAI_STABLE_MAX_DROP);
        if (overlap >= CLIENTAI_STABLE_MIN_IOU && conf < floor) {
          det.conf = Math.max(0, Math.min(1, Number(floor.toFixed(4))));
        }
      }
    }
    clientAiRuntime.stableByLabel[label] = {
      x1: Number(det.x1 || 0),
      y1: Number(det.y1 || 0),
      x2: Number(det.x2 || 0),
      y2: Number(det.y2 || 0),
      conf: Number(det.conf || 0),
      ts_client_ms: nowMs,
    };
  });
  return out;
}

async function ensureOrtLoaded() {
  if (window.ort?.InferenceSession) return;
  const sources = [CLIENTAI_ORT_CDN, CLIENTAI_ORT_FALLBACK];
  for (const src of sources) {
    await new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[data-clientai-ort-src="${src}"]`);
      if (window.ort?.InferenceSession) {
        resolve();
        return;
      }
      if (existing && existing.dataset.state === 'loaded') {
        resolve();
        return;
      }
      if (existing && existing.dataset.state === 'error') {
        existing.remove();
      }
      const script = existing || document.createElement('script');
      script.src = src;
      script.async = true;
      script.dataset.clientaiOrt = '1';
      script.dataset.clientaiOrtSrc = src;
      script.dataset.state = 'loading';
      const onLoad = () => {
        script.dataset.state = 'loaded';
        clientAiRuntime.ortScriptSrc = src;
        resolve();
      };
      const onError = () => {
        script.dataset.state = 'error';
        reject(new Error(`ort_load_failed:${src}`));
      };
      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      if (!existing) document.head.appendChild(script);
      setTimeout(() => {
        if (!window.ort?.InferenceSession) onError();
      }, 9000);
    }).catch(() => {});
    if (window.ort?.InferenceSession) return;
  }
  throw new Error('ort_unavailable');
}

async function postClientAiTarget(payload) {
  const res = await fetch(`${clientAiApiBase()}/api/vision/client-target`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.ok) {
    return false;
  }
  return true;
}

async function ensureClientAiModelReady() {
  await ensureOrtLoaded();
  if (window.ort?.env?.wasm) {
    const base = clientAiRuntime.ortScriptSrc
      ? clientAiRuntime.ortScriptSrc.replace(/ort\.min\.js.*$/i, '')
      : 'https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/';
    window.ort.env.wasm.wasmPaths = base;
    window.ort.env.wasm.numThreads = 1;
    window.ort.env.wasm.proxy = false;
  }
  if (!clientAiRuntime.manifest) {
    const manifestRes = await fetch(`${clientAiApiBase()}/api/clientai/model-manifest`, { cache: 'no-store' });
    if (!manifestRes.ok) throw new Error(`manifest_http_${manifestRes.status}`);
    clientAiRuntime.manifest = await manifestRes.json();
  }
  const manifest = clientAiRuntime.manifest || {};
  const models = Array.isArray(manifest.models) ? manifest.models : [];
  if (models.length === 0) throw new Error('model_manifest_empty');
  const bestModel = models.find((m) => String(m?.name || '').includes('best_cv451'))
    || models.find((m) => String(m?.name || '').includes('best'))
    || models.find((m) => m.name === CLIENTAI_PREFERRED_MODEL)
    || models[0];
  const yoloModel = models.find((m) => String(m?.name || '').includes('yolov8n'))
    || models.find((m) => String(m?.name || '').includes('yolo11n'))
    || models.find((m) => m.name === CLIENTAI_YOLO_MODEL_FALLBACK)
    || models[0];
  if (!bestModel?.url || !yoloModel?.url) throw new Error('model_manifest_invalid');
  const capability = detectClientAiCapability();
  const providers = capability.provider === 'webgpu' ? ['webgpu', 'wasm'] : ['wasm'];
  clientAiRuntime.provider = providers[0];
  const choice = resolveClientAiModelChoice(clientAiRuntime.modelChoice);
  if (!clientAiRuntime.inferSessionBest) {
    clientAiRuntime.inferSessionBest = await window.ort.InferenceSession.create(`${clientAiApiBase()}${bestModel.url}`, {
      executionProviders: providers,
      graphOptimizationLevel: 'all',
    });
    clientAiRuntime.modelNameBest = String(bestModel.name || CLIENTAI_PREFERRED_MODEL);
    const firstInputBest = clientAiRuntime.inferSessionBest.inputNames[0];
    const inMetaBest = clientAiRuntime.inferSessionBest.inputMetadata?.[firstInputBest];
    const dimsBest = Array.isArray(inMetaBest?.dimensions) ? inMetaBest.dimensions : [];
    clientAiRuntime.inputSizeBest = inferClientAiInputSize(clientAiRuntime.modelNameBest, Number(dimsBest[2]), 320);
  }
  if ((choice === CLIENTAI_MODEL_CHOICE_YOLO || choice === CLIENTAI_MODEL_CHOICE_MIX) && !clientAiRuntime.inferSessionYolo) {
    clientAiRuntime.inferSessionYolo = await window.ort.InferenceSession.create(`${clientAiApiBase()}${yoloModel.url}`, {
      executionProviders: providers,
      graphOptimizationLevel: 'all',
    });
    clientAiRuntime.modelNameYolo = String(yoloModel.name || CLIENTAI_YOLO_MODEL_FALLBACK);
    const firstInputYolo = clientAiRuntime.inferSessionYolo.inputNames[0];
    const inMetaYolo = clientAiRuntime.inferSessionYolo.inputMetadata?.[firstInputYolo];
    const dimsYolo = Array.isArray(inMetaYolo?.dimensions) ? inMetaYolo.dimensions : [];
    clientAiRuntime.inputSizeYolo = inferClientAiInputSize(clientAiRuntime.modelNameYolo, Number(dimsYolo[2]), 320);
  }
  if (choice === CLIENTAI_MODEL_CHOICE_YOLO) {
    clientAiRuntime.inferSession = clientAiRuntime.inferSessionYolo || clientAiRuntime.inferSessionBest;
    clientAiRuntime.modelName = String(clientAiRuntime.modelNameYolo || clientAiRuntime.modelNameBest || CLIENTAI_YOLO_MODEL_FALLBACK);
    clientAiRuntime.inputSize = Number(clientAiRuntime.inputSizeYolo || clientAiRuntime.inputSizeBest || 320);
  } else {
    clientAiRuntime.inferSession = clientAiRuntime.inferSessionBest;
    clientAiRuntime.modelName = String(clientAiRuntime.modelNameBest || CLIENTAI_PREFERRED_MODEL);
    clientAiRuntime.inputSize = Number(clientAiRuntime.inputSizeBest || 320);
  }
  clientAiRuntime.provider = providers[0];
  clientAiRuntime.modelReady = true;
  await postClientAiState({ provider: clientAiRuntime.provider, model_id: getClientAiStateModelId() });
}

async function inferAndPublishClientAiFrame() {
  if (!clientAiRuntime.modelReady) return;
  const liveVideoEl = document.getElementById('liveVideo');
  if (!liveVideoEl || liveVideoEl.videoWidth < 16 || liveVideoEl.videoHeight < 16) return;
  const choice = resolveClientAiModelChoice(clientAiRuntime.modelChoice);
  const runs = [];
  if (choice === CLIENTAI_MODEL_CHOICE_MIX) {
    if (clientAiRuntime.inferSessionBest) {
      runs.push({
        session: clientAiRuntime.inferSessionBest,
        inputSize: clampByteSize(clientAiRuntime.inputSizeBest, 320),
        modelName: String(clientAiRuntime.modelNameBest || CLIENTAI_PREFERRED_MODEL),
        source: 'mt',
      });
    }
    if (clientAiRuntime.inferSessionYolo) {
      runs.push({
        session: clientAiRuntime.inferSessionYolo,
        inputSize: clampByteSize(clientAiRuntime.inputSizeYolo, 320),
        modelName: String(clientAiRuntime.modelNameYolo || CLIENTAI_YOLO_MODEL_FALLBACK),
        source: 'yolo',
      });
    }
  } else {
    const useYolo = choice === CLIENTAI_MODEL_CHOICE_YOLO;
    const singleSession = useYolo ? (clientAiRuntime.inferSessionYolo || clientAiRuntime.inferSession) : (clientAiRuntime.inferSessionBest || clientAiRuntime.inferSession);
    if (singleSession) {
      runs.push({
        session: singleSession,
        inputSize: clampByteSize(useYolo ? clientAiRuntime.inputSizeYolo : clientAiRuntime.inputSizeBest, 320),
        modelName: useYolo ? String(clientAiRuntime.modelNameYolo || CLIENTAI_YOLO_MODEL_FALLBACK) : String(clientAiRuntime.modelNameBest || CLIENTAI_PREFERRED_MODEL),
        source: useYolo ? 'yolo' : 'mt',
      });
    }
  }
  if (runs.length === 0) return;
  syncClientAiDebugConfigFromUi();
  const dbg = clientAiRuntime.debug;
  const tensorCache = new Map();
  const getTensorForSize = (inputSize) => {
    const size = clampByteSize(inputSize, 320);
    if (tensorCache.has(size)) return tensorCache.get(size);
    clientAiSampleCanvas.width = size;
    clientAiSampleCanvas.height = size;
    clientAiSampleCtx.drawImage(liveVideoEl, 0, 0, size, size);
    const src = clientAiSampleCtx.getImageData(0, 0, size, size).data;
    const hw = size * size;
    const chw = new Float32Array(3 * hw);
    for (let i = 0; i < hw; i += 1) {
      const o = i * 4;
      chw[i] = src[o] / 255.0;
      chw[hw + i] = src[o + 1] / 255.0;
      chw[(2 * hw) + i] = src[o + 2] / 255.0;
    }
    const tensor = new window.ort.Tensor('float32', chw, [1, 3, size, size]);
    tensorCache.set(size, tensor);
    return tensor;
  };

  const t0 = performance.now();
  let allBoxes = [];
  let allRawBoxes = [];
  for (const run of runs) {
    const feeds = {};
    const firstInput = run.session.inputNames[0];
    feeds[firstInput] = getTensorForSize(run.inputSize);
    const outMap = await run.session.run(feeds);
    const outName = run.session.outputNames[0];
    const output = outMap[outName];
    if (dbg.enabled) {
      const rawBoxes = decodeYoloOutput(
        output,
        run.inputSize,
        Number(dbg.rawConfThres),
        run.modelName,
        run.source,
        { allowedOnly: false, iouNms: Number(dbg.iouNms), maxDet: Number(dbg.maxDet) },
      );
      allRawBoxes = allRawBoxes.concat(rawBoxes);
    }
    const boxes = decodeYoloOutput(
      output,
      run.inputSize,
      0.30,
      run.modelName,
      run.source,
      { allowedOnly: true, iouNms: 0.45, maxDet: 20 },
    );
    allBoxes = allBoxes.concat(boxes);
  }
  const inferMs = performance.now() - t0;
  clientAiRuntime.inferSuccess += 1;
  clientAiRuntime.lastInferMs = inferMs;
  clientAiRuntime.inferMsAvg = clientAiRuntime.inferMsAvg == null ? inferMs : ((clientAiRuntime.inferMsAvg * 0.85) + (inferMs * 0.15));
  if (clientAiRuntime.inferMsAvg > 450 && clientAiRuntime.inferEveryN < 20) clientAiRuntime.inferEveryN += 1;
  if (clientAiRuntime.inferMsAvg < 220 && clientAiRuntime.inferEveryN > 4) clientAiRuntime.inferEveryN -= 1;
  if (dbg.enabled) {
    renderDebugRawDetections(allRawBoxes);
    logClientAiDebugFrame(allRawBoxes, Number(runs[0]?.inputSize || clientAiRuntime.inputSize || 0));
  } else {
    hideDebugRawOverlay();
  }

  const topDetections = applyClientAiBallHeuristics(applyClientAiClassSwitchDebounce(
    applyClientAiConfidenceStability(
      selectClientAiTopDetections(allBoxes, CLIENTAI_MAX_RENDER_CLASSES),
    ),
  ));
  latestClientAiLocalDetections = topDetections.map((det) => ({ ...det, ts_client_ms: Date.now() }));
  if (clientAiInferMsEl) clientAiInferMsEl.value = inferMs.toFixed(1);
  if (vmClientAiInferMsEl) vmClientAiInferMsEl.textContent = inferMs.toFixed(1);
  if (vmClientAiModelEl) vmClientAiModelEl.textContent = getClientAiDisplayModelLabel();
  renderVisionTargetOverlay(latestVisionState);
  if (topDetections.length === 0) {
    return;
  }
  if (!clientAiRuntime.sessionArmed) {
    clientAiRuntime.postSkipUnarmed += 1;
    return;
  }
  const posted = await postClientAiTarget({
    ts_client_ms: Date.now(),
    frame_id: clientAiRuntime.frameId,
    model_id: getClientAiStateModelId(),
    provider: clientAiRuntime.provider || detectClientAiCapability().provider,
    infer_ms: inferMs,
    image_w: Number(liveVideoEl.videoWidth || 0),
    image_h: Number(liveVideoEl.videoHeight || 0),
    detections: topDetections,
  });
  if (posted) {
    clientAiRuntime.postOk += 1;
  } else {
    clientAiRuntime.postFail += 1;
  }
}

async function runClientAiRuntimeTick() {
  if (clientAiRuntime.tickBusy) return;
  clientAiRuntime.tickBusy = true;
  try {
    const activeMode = String(clientAiStatus?.active_mode || '').toLowerCase();
    if (activeMode !== 'client-ai') {
      latestClientAiLocalDetections = [];
      hideDebugRawOverlay();
      return;
    }
    await ensureClientAiModelReady();
    clientAiRuntime.frameId += 1;
    clientAiRuntime.inferEveryN = inferIntervalN();
    if ((clientAiRuntime.frameId % clientAiRuntime.inferEveryN) !== 0) return;
    clientAiRuntime.inferAttempts += 1;
    await inferAndPublishClientAiFrame();
    clientAiRuntime.lastError = '';
  } catch (e) {
    if (maybeRecoverInputSizeFromOrtError(e)) {
      clientAiRuntime.lastError = '';
      return;
    }
    clientAiRuntime.lastError = String(e?.message || e || 'infer_unavailable');
    setClientAiStatus(`ClientAI infer unavailable: ${clientAiRuntime.lastError}`, true);
    latestClientAiLocalDetections = [];
  } finally {
    clientAiRuntime.tickBusy = false;
  }
}

function clientAiRuntimeLoop() {
  if (!clientAiRuntime.running) return;
  runClientAiRuntimeTick().finally(() => {
    requestAnimationFrame(clientAiRuntimeLoop);
  });
}

function startClientAiRuntimeLoop() {
  if (clientAiRuntime.running) return;
  clientAiRuntime.running = true;
  requestAnimationFrame(clientAiRuntimeLoop);
}

function updateStreamAlertUi() {
  if (!liveViewEl) return;
  const now = Date.now();
  const ageMs = latestVideoEventMs > 0 ? (now - latestVideoEventMs) : Number.POSITIVE_INFINITY;
  const streamLikelyStalled = ageMs > 5000 || latestFps < 0.3;
  const statusText = String(liveStatusEl?.textContent || '').toLowerCase();
  const noStream = statusText.includes('unavailable') || statusText.includes('nostream') || statusText.includes('proxy status unavailable');
  const visionErr = String(latestVisionState?.error || '');
  const visionErrLower = visionErr.toLowerCase();
  const visionTransient = !!visionErr && (
    visionErrLower.includes('rtsp_read_failed')
    || visionErrLower.includes('rtsp_open_failed')
    || visionErrLower.includes('video_connect_failed')
    || visionErrLower.includes('worker_stream_error')
    || visionErrLower.includes('rtsp_worker_error')
  );
  const visionBad = String(latestVisionState?.health || '').toLowerCase() === 'error';
  const stalledCandidate = streamLikelyStalled || noStream;
  if (stalledCandidate) {
    stallCandidateCount = Math.min(STALL_ASSERT_TICKS + 1, stallCandidateCount + 1);
    stallClearCount = 0;
  } else {
    stallCandidateCount = 0;
    stallClearCount = Math.min(STALL_CLEAR_TICKS + 1, stallClearCount + 1);
  }
  const stalled = stallCandidateCount >= STALL_ASSERT_TICKS;
  const lowBattery = !!latestLowBatteryActive;
  const minorVisionWarn = visionTransient && !stalled;
  const criticalVisionWarn = !minorVisionWarn && (visionBad || (!!visionErr && !visionTransient));
  const showAlert = stalled || minorVisionWarn || criticalVisionWarn || lowBattery;
  syncStreamStatusLine(stalled);
  if (lowBattery) {
    const nowMs = Date.now();
    if (!lowBatteryBeepBusy && (nowMs - lowBatteryBeepLastMs) >= 5000) {
      lowBatteryBeepLastMs = nowMs;
      triggerLowBatteryBeepTriplet();
    }
  }
  if (showAlert) {
    liveViewEl.classList.add('alert-visible');
    if (stalled || criticalVisionWarn) {
      liveViewEl.classList.add('video-stalled');
    } else {
      liveViewEl.classList.remove('video-stalled');
    }
    if (streamAlertTextEl) {
      const title = stalled ? 'Video stream stalled' : (lowBattery ? 'Battery warning' : 'YOLO Vision warning');
      const first = streamAlertTextEl.firstChild;
      if (first && first.nodeType === Node.TEXT_NODE) {
        first.textContent = title;
      } else {
        streamAlertTextEl.prepend(document.createTextNode(title));
      }
    }
    if (streamAlertSubEl) {
      if (stalled && (visionBad || visionErr)) {
        streamAlertSubEl.textContent = `Stream recovering. Vision: ${visionErr || latestVisionState?.health || 'error'}`;
      } else if (stalled) {
        streamAlertSubEl.textContent = `Waiting for stream recovery (${latestVideoMode || 'unknown'})`;
      } else if (minorVisionWarn) {
        streamAlertSubEl.textContent = `${visionErr} (minor warning, auto-recovering)`;
      } else if (lowBattery) {
        streamAlertSubEl.textContent = `Battery ${Number(latestBatteryV || 0).toFixed(2)}V <= warn ${Number(batteryWarnV).toFixed(2)}V (${formatDurationHms(latestLowBatteryDurationS || 0)})`;
      } else {
        streamAlertSubEl.textContent = visionErr || `Vision health: ${latestVisionState?.health || 'error'}`;
      }
    }
    return;
  }
  if (stallClearCount >= STALL_CLEAR_TICKS) {
    liveViewEl.classList.remove('alert-visible');
    liveViewEl.classList.remove('video-stalled');
  }
}

async function sendVisionStateAction(action, payload = {}) {
  const body = { action, ...payload };
  try {
    const res = await fetch('/vision/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data?.ok) {
      latestVisionState = data.state || null;
      syncVisionButtons(latestVisionState);
      return true;
    }
  } catch (e) {
    // ignore and show lightweight status in error line
  }
  if (errEl) errEl.textContent = `vision action failed: ${action}`;
  return false;
}

function bindVisionModeButtons() {
  if (toggleYoloEl) {
    toggleYoloEl.addEventListener('click', async () => {
      await sendVisionStateAction('toggle_yolo');
      await fetchVisionConfig();
    });
  }
  if (toggleTrackingEl) {
    toggleTrackingEl.addEventListener('click', async () => {
      if (toggleTrackingEl.disabled) return;
      await sendVisionStateAction('toggle_tracking');
      await fetchVisionConfig();
    });
  }
}

async function pollVisionState() {
  try {
    const res = await fetch('/vision/state', { cache: 'no-store' });
    const data = await res.json();
    if (data?.ok) {
      latestVisionState = data.state || null;
      syncVisionButtons(latestVisionState);
    }
  } catch (e) {
    // keep UI silent if endpoint is unavailable
    renderVisionTargetOverlay(null);
  }
}

async function postVisionMetricsHeartbeat() {
  try {
    await fetch('/vision/metrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stream_fps: Number(latestFps || 0),
        stream_mode: String(document.getElementById('liveStatus')?.textContent || ''),
      }),
    });
  } catch (e) {
    // non-fatal
  }
}

async function pollVisionMetrics() {
  try {
    const res = await fetch('/vision/metrics', { cache: 'no-store' });
    const data = await res.json();
    if (data?.ok) {
      renderVisionMetrics(data.metrics || {});
    }
  } catch (e) {
    // keep UI silent if endpoint is unavailable
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

function renderViewerClients(summary) {
  if (!viewerClientsListEl) return;
  const ttl = Math.max(5, Number(summary?.ttl_s || 25));
  const viewers = Array.isArray(summary?.viewers) ? summary.viewers : [];
  const healthy = viewers.filter((v) => Number(v?.age_s || 0) <= ttl);
  if (viewerClientsHeadEl) {
    viewerClientsHeadEl.textContent = `Live Clients: ${healthy.length} lives (ttl ${ttl.toFixed(0)}s)`;
  }
  viewerClientsListEl.innerHTML = '';
  if (healthy.length === 0) {
    const row = document.createElement('div');
    row.className = 'viewer-client-row';
    row.textContent = 'No active clients';
    viewerClientsListEl.appendChild(row);
    return;
  }
  healthy.slice(0, 3).forEach((v) => {
    const row = document.createElement('div');
    row.className = 'viewer-client-row';
    const device = String(v?.device_label || 'unknown');
    const ip = String(v?.client_ip || '-');
    const fps = Number.isFinite(v?.fps) ? Number(v.fps).toFixed(1) : '--';
    const age = Number.isFinite(v?.age_s) ? `${Number(v.age_s).toFixed(1)}s` : '--';
    row.textContent = `${device} | ${ip} | ${fps}fps | ${age}`;
    viewerClientsListEl.appendChild(row);
  });
}

async function pollPowerHistory() {
  try {
    const res = await fetch('/telemetry/power_history', { cache: 'no-store' });
    const data = await res.json();
    latestPowerHistory = data || null;
    if (typeof data?.warn_v === 'number') {
      batteryWarnV = Number(data.warn_v);
    }
    if (typeof data?.low_battery === 'boolean') {
      latestLowBatteryActive = !!data.low_battery;
    }
    if (typeof data?.low_battery_duration_s === 'number') {
      latestLowBatteryDurationS = Number(data.low_battery_duration_s || 0);
    }
    if (typeof data?.low_battery_policy === 'string') {
      latestLowBatteryPolicy = String(data.low_battery_policy || '');
    }
    renderBatteryStateLine();
    renderBatteryTrendOverlay();
  } catch (e) {
    // keep silent; chart keeps last good state
  }
}

async function pollViewerSummary() {
  if (!viewerClientsListEl) return;
  try {
    const res = await fetch('/viewer/summary', { cache: 'no-store' });
    const data = await res.json();
    if (data?.ok) {
      renderViewerClients(data.summary || {});
      return;
    }
  } catch (e) {
    // silent fallback below
  }
  if (viewerClientsHeadEl) viewerClientsHeadEl.textContent = 'Live Clients: unavailable';
  viewerClientsListEl.innerHTML = '';
  const row = document.createElement('div');
  row.className = 'viewer-client-row';
  row.textContent = 'Pi viewer summary endpoint not reachable';
  viewerClientsListEl.appendChild(row);
}

function maybeShowOfflineNotice(reason) {
  if (offlineState.consecutiveFailures < OFFLINE_NOTICE_THRESHOLD) {
    return;
  }
  if (offlineState.noticeReason === reason) {
    return;
  }
  offlineState.noticeReason = reason;
  if (errEl) {
    errEl.textContent = `Pi Server not reachable (${reason}); waiting for auto-recovery.`;
  }
}

async function pollImu() {
  try {
    const res = await fetch('/imu', { cache: 'no-store' });
    const data = await res.json();
    if (data.ok) {
      const nowMs = Date.now();
      const isLiveRecover = !imuWasLive;
      rawImu.roll = Number(data.roll);
      rawImu.pitch = Number(data.pitch);
      rawImu.yaw = Number(data.yaw);
      if (isLiveRecover) {
        // On first live sample (initial connect or reconnect), align current heading to right-facing.
        resetYawToRight(rawImu.yaw);
      }
      const mapped = mapImuToModel(data, nowMs);
      modifiedImu.roll = mapped.roll;
      modifiedImu.pitch = mapped.pitch;
      modifiedImu.yaw = mapped.yawRaw;
      statusEl.textContent = 'live';
      imuWasLive = true;
      offlineState.consecutiveFailures = 0;
      offlineState.noticeReason = '';
      offlineState.lastOkMs = nowMs;
      if (errEl && errEl.textContent.startsWith('Pi Server not reachable')) {
        errEl.textContent = '--';
      }
      target.roll = mapped.roll;
      target.pitch = mapped.pitch;
      target.yaw = mapped.yaw;
      if (!imuSeeded) {
        smooth.roll = mapped.roll;
        smooth.pitch = mapped.pitch;
        smooth.yaw = mapped.yaw;
        imuSeeded = true;
      }
      rollEl.textContent = mapped.roll.toFixed(2);
      pitchEl.textContent = mapped.pitch.toFixed(2);
      yawEl.textContent = mapped.yawRaw.toFixed(2);
      renderImuMatrix(false);
      updateLastOkAge(nowMs);
    } else {
      statusEl.textContent = 'offline';
      imuWasLive = false;
      offlineState.consecutiveFailures += 1;
      if (data.last_ok_ts) {
        offlineState.lastOkMs = Math.max(offlineState.lastOkMs, data.last_ok_ts * 1000);
      }
      updateLastOkAge(Date.now());
      maybeShowOfflineNotice('no IMU data');
    }
  } catch (e) {
    statusEl.textContent = 'error';
    imuWasLive = false;
    offlineState.consecutiveFailures += 1;
    updateLastOkAge(Date.now());
    maybeShowOfflineNotice('network error');
  }
}

setInterval(pollImu, 100);
setInterval(pollDiag, 1000);
setInterval(pollTelemetry, 1000);
pollVersion();
pollTelemetry();
renderTopTelemetryLine();
bindVisionConfigControls();
bindClientAiControls();
bindClientAiDebugControls();
syncClientAiCapabilityAuto();
fetchVisionConfig();
fetchVideoConfig();
pollClientAiStatus();
pollClientSessionStatus();
pollClientTargetLatest();
startClientAiRuntimeLoop();
setInterval(pollClientAiStatus, 2000);
setInterval(pollClientSessionStatus, 2000);
setInterval(pollClientTargetLatest, 1000);
setInterval(syncClientAiCapabilityAuto, 15000);
scheduleVideoProfileResync();
bindVisionModeButtons();
pollVisionState();
setInterval(postVisionMetricsHeartbeat, 2000);
setInterval(pollVisionMetrics, 2000);
setInterval(pollVisionState, 2000);
setInterval(updateStreamAlertUi, 1000);
setInterval(pollViewerSummary, 5000);
setInterval(pollPowerHistory, 5000);
setInterval(renderBatteryTrendOverlay, 1000);
setInterval(() => syncStreamStatusLine(false), 1000);
pollVisionMetrics();
pollViewerSummary();
pollPowerHistory();
window.addEventListener('focus', () => {
  fetchVideoConfig();
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    fetchVideoConfig();
  }
});
window.addEventListener('live-video-fps', (ev) => {
  latestFps = Number(ev?.detail?.fps || 0);
  latestVideoEventMs = Date.now();
  latestVideoMode = String(ev?.detail?.mode || '');
  renderTopTelemetryLine();
  syncStreamStatusLine(false);
  updateStreamAlertUi();
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
    syncStreamStatusLine(true);
  }
}
startLiveVideoSafe();
if (BASIC_IMU_MODE && orientationToolsEl) {
  orientationToolsEl.style.display = 'none';
} else {
  syncOrientationTuningUi();
}

function bindOrientationTuningEvents() {
  if (invRollEl) {
    invRollEl.addEventListener('change', () => {
      orientationTuning.invRoll = !!invRollEl.checked;
      saveOrientationTuning();
    });
  }
  if (invPitchEl) {
    invPitchEl.addEventListener('change', () => {
      orientationTuning.invPitch = !!invPitchEl.checked;
      saveOrientationTuning();
    });
  }
  if (invYawEl) {
    invYawEl.addEventListener('change', () => {
      orientationTuning.invYaw = !!invYawEl.checked;
      saveOrientationTuning();
    });
  }
  if (offRollEl) {
    offRollEl.addEventListener('change', () => {
      orientationTuning.offRoll = clampOffset(Number(offRollEl.value));
      syncOrientationTuningUi();
      saveOrientationTuning();
    });
  }
  if (offPitchEl) {
    offPitchEl.addEventListener('change', () => {
      orientationTuning.offPitch = clampOffset(Number(offPitchEl.value));
      syncOrientationTuningUi();
      saveOrientationTuning();
    });
  }
  if (offYawEl) {
    offYawEl.addEventListener('change', () => {
      orientationTuning.offYaw = clampOffset(Number(offYawEl.value));
      syncOrientationTuningUi();
      saveOrientationTuning();
    });
  }
  if (oriResetEl) {
    oriResetEl.addEventListener('click', () => {
      orientationTuning.invRoll = defaultOrientationTuning.invRoll;
      orientationTuning.invPitch = defaultOrientationTuning.invPitch;
      orientationTuning.invYaw = defaultOrientationTuning.invYaw;
      orientationTuning.offRoll = defaultOrientationTuning.offRoll;
      orientationTuning.offPitch = defaultOrientationTuning.offPitch;
      orientationTuning.offYaw = defaultOrientationTuning.offYaw;
      syncOrientationTuningUi();
      saveOrientationTuning();
      yawTrack.hasPrevRaw = false;
    });
  }
}
if (!BASIC_IMU_MODE) {
  bindOrientationTuningEvents();
}

function bindAxisModeToggle() {
  if (!usePiNativeAxisEl) return;
  usePiNativeAxisEl.checked = usePiNativeAxis;
  usePiNativeAxisEl.addEventListener('change', () => {
    usePiNativeAxis = !!usePiNativeAxisEl.checked;
    imuSeeded = false;
  });
}
bindAxisModeToggle();

function bindYawResetAction() {
  if (!resetYawRightEl) return;
  resetYawRightEl.addEventListener('click', () => {
    resetYawToRight();
  });
}
bindYawResetAction();

function resetYawToRight(sensorYawRawDeg = lastSensorYawRawDeg) {
  yawNorthOffsetDeg = Number(sensorYawRawDeg || 0);
  yawTrack.hasPrevRaw = false;
  target.yaw = 0;
  smooth.yaw = 0;
}

function animate() {
  requestAnimationFrame(animate);
  smooth.roll = smoothAngleDeg(smooth.roll, target.roll, alpha);
  smooth.pitch = smoothAngleDeg(smooth.pitch, target.pitch, alpha);
  smooth.yaw = smoothAngleDeg(smooth.yaw, target.yaw, alpha);
  const imuLost = isImuStale(Date.now());
  renderCompactImu(imuLost);
  setImuTelemetryLostUi(imuLost);
  renderImuMatrix(imuLost);

  // Rotation definition in this viewer: Yaw->Z, Pitch->X, Roll->Y.
  // In Three.js here, yaw is applied via parent Y-axis (yawGroup), while body tilt
  // uses X/Z to match model frame after import alignment.
  yawGroup.rotation.y = degToRad(YAW_ENABLE ? smooth.yaw : 0);
  bodyTiltGroup.rotation.x = degToRad(smooth.roll);
  bodyTiltGroup.rotation.z = degToRad(smooth.pitch);
  axisYawGroup.rotation.y = yawGroup.rotation.y;
  axisTiltGroup.rotation.x = bodyTiltGroup.rotation.x;
  axisTiltGroup.rotation.z = bodyTiltGroup.rotation.z;

  renderer.render(scene, camera);
}

animate();

window.addEventListener('resize', () => {
  resizeRenderer();
});

async function sendAction(cmd) {
  try {
    const cmdUpper = String(cmd || '').toUpperCase();
    if (cmdUpper.startsWith('CMD_RELAX') || cmdUpper.startsWith('CMD_MOVE_STOP') || cmdUpper.startsWith('CMD_STOP_PWM')) {
      syncDemoButtonUi(false);
    }
    await fetch('/cmd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd }),
    });
  } catch (e) {
    // ignore
  }
}

async function sendCmdSequence(cmds, delayMs = 100) {
  for (let i = 0; i < cmds.length; i += 1) {
    await sendAction(cmds[i]);
    if (i < cmds.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
}

function syncBalanceButtonUi(isOn) {
  if (!toggleBalanceEl) return;
  const on = !!isOn;
  toggleBalanceEl.dataset.state = on ? 'on' : 'off';
  toggleBalanceEl.textContent = on ? 'Balance ON' : 'Balance OFF';
  toggleBalanceEl.classList.toggle('green', on);
}

function syncHorizonButtonUi(isOn) {
  if (!toggleHorizonEl) return;
  const on = !!isOn;
  toggleHorizonEl.dataset.state = on ? 'on' : 'off';
  toggleHorizonEl.textContent = on ? 'Horizon ON' : 'Horizon OFF';
  toggleHorizonEl.classList.toggle('amber', on);
}

function bindBalanceToggle() {
  if (!toggleBalanceEl) return;
  syncBalanceButtonUi(toggleBalanceEl.dataset.state === 'on');
  toggleBalanceEl.addEventListener('click', async () => {
    const turnOn = toggleBalanceEl.dataset.state !== 'on';
    const cmd = turnOn ? 'CMD_BALANCE#1' : 'CMD_BALANCE#0';
    await sendAction(cmd);
    syncBalanceButtonUi(turnOn);
  });
}
bindBalanceToggle();

function bindHorizonToggle() {
  if (!toggleHorizonEl) return;
  syncHorizonButtonUi(toggleHorizonEl.dataset.state === 'on');
  toggleHorizonEl.addEventListener('click', async () => {
    const turnOn = toggleHorizonEl.dataset.state !== 'on';
    // Mirror mtDogMain logic: OFF -> CMD_HORIZON#0, ON -> apply a modest forward/back trim.
    const cmd = turnOn ? 'CMD_HORIZON#8' : 'CMD_HORIZON#0';
    await sendAction(cmd);
    syncHorizonButtonUi(turnOn);
  });
}
bindHorizonToggle();

async function sendDemoAction(action = 'start', demo = 'helloOne') {
  try {
    const res = await fetch('/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, demo }),
    });
    const data = await res.json().catch(() => ({}));
    return { ok: !!data.ok, data };
  } catch (e) {
    return { ok: false, data: { error: String(e) } };
  }
}

function syncDemoButtonUi(isRunning) {
  if (!triggerDemoEl) return;
  const running = !!isRunning;
  triggerDemoEl.dataset.state = running ? 'running' : 'off';
  triggerDemoEl.textContent = running ? 'Stop Demo' : 'Demo';
  triggerDemoEl.classList.toggle('stop', running);
}

function bindDemoTrigger() {
  if (!triggerDemoEl) return;
  syncDemoButtonUi(false);
  triggerDemoEl.addEventListener('click', async () => {
    const running = triggerDemoEl.dataset.state === 'running';
    if (running) {
      const out = await sendDemoAction('stop');
      syncDemoButtonUi(false);
      if (!out.ok && errEl) errEl.textContent = out?.data?.error || 'demo stop failed';
      return;
    }
    const out = await sendDemoAction('start', 'helloOne');
    if (out.ok) {
      syncDemoButtonUi(true);
      setTimeout(() => syncDemoButtonUi(false), 16000);
    } else if (errEl) {
      errEl.textContent = out?.data?.error || 'demo start failed';
    }
  });
}
bindDemoTrigger();

function bindActionSequences() {
  document.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const action = btn.getAttribute('data-action');
      if (action === 'beep') {
        await sendCmdSequence(['CMD_BUZZER#1', 'CMD_BUZZER#0'], 120);
      } else if (action === 'led') {
        await sendCmdSequence(['CMD_LED_MOD#1', 'CMD_LED#255#0#255#0', 'CMD_LED_MOD#0'], 120);
      }
    });
  });
}
bindActionSequences();

async function triggerLowBatteryBeepTriplet() {
  lowBatteryBeepBusy = true;
  try {
    await sendCmdSequence([
      'CMD_BUZZER#1', 'CMD_BUZZER#0',
      'CMD_BUZZER#1', 'CMD_BUZZER#0',
      'CMD_BUZZER#1', 'CMD_BUZZER#0',
    ], 90);
  } finally {
    lowBatteryBeepBusy = false;
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
