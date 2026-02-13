# CloseLoop_AutoDebug_WebPage.md

**File Name:** `CloseLoop_AutoDebug_WebPage.md`  
**Version:** `v1.20 (2026-02-13 21:39 local time)`  
**Author:** Mengta Tsai & AI Engineering Assistant  
**Project:** RobotDog - Hybrid Edge / Client AI System  
**Description:** Architecture and execution status for autonomous closed-loop debugging on Safari WebRTC page `http://192.168.0.32:8081/color`.

## 1. Executive Summary
Closed-loop debugging is now partially operational in production:
- Browser page can be inspected automatically (headless Chromium/Playwright).
- Runtime state is validated from both DOM (Document Object Model) and backend APIs.
- Fix -> deploy -> verify loop is active against Pi host.
- Watchdog health diagnostics endpoint is live on Pi (`/diag/system-health.json`) with deterministic PASS/WARN/FAIL scoring and NDJSON snapshot logging.

Remaining work is to formalize this into a persistent watchdog and test framework.

## 2. Current Status Matrix
### 2.1 Completed
- [x] Automated page access for `/color` without manual screenshots.
- [x] Runtime DOM extraction for key fields (`model`, `infer ms`, publish counters, status text).
- [x] API cross-check loop:
  - `GET /api/clientai`
  - `GET /api/vision/client-target/latest`
  - `GET /vision/state`
- [x] Root-cause diagnosis for prior failures (e.g., ORT input-size mismatch 256 vs 320).
- [x] Trained model priority switched to `best_cv451.onnx` for browser startup path.
- [x] Pi Edge-AI disabled in `client-ai` mode to avoid dual-source operator confusion.
- [x] Detection UX added: explicit `DETECTED: ...` overlay banner on live view.
- [x] Server-to-Pi sync + Pi-side file/header verification included in each Server task.
- [x] `GET /diag/system-health.json` is now live in telemetry server and returns watchdog health snapshot (`classification`, `score`, `checks`, `context`).
- [x] Runtime NDJSON append is verified on Pi (`Code/Temp/snapshots/system_health.ndjson`).
- [x] `/color` UI cleaned for ClientAI-first operation: removed visible Pi-edge wording, moved non-operator controls to hidden virtual spaces, and validated live page values via Playwright probes.
- [x] N1 watchdog implementation completed: `tools/agent_watchdog.py` now probes DOM + APIs and appends normalized NDJSON records with PASS/WARN/FAIL status.
- [x] N1 smoke/loop verification completed:
  - `--once` run passes and writes record.
  - 3-cycle run passes with stable schema and no probe errors after vision-base routing fix.
- [x] Persistent watchdog wrapper implemented: `tools/agent_watchdog_supervisor.sh` with restart/backoff and smoke validation path.
- [x] N2 compact diagnostics endpoint implemented: `GET /diag/clientai.json` (mode/model/infer/detect/session/watchdog summary + deterministic status).
- [x] N3 baseline integration tests implemented: `tests/integration_test_clientai.py` (model-manifest default, compact diag schema, watchdog output contract, `/color` ClientAI widget presence).
- [x] N2 live deployment verification complete on Pi:
  - telemetry service restarted successfully,
  - `/diag/clientai.json` returns schema/status/model/watchdog fields as expected.
- [x] N3 baseline test execution complete: `python -m unittest tests.integration_test_clientai -v` -> `OK (4 tests)`.

### 2.2 In Progress
- [ ] Stabilize detection confidence consistency in low-light / partial-occlusion scenes.
- [x] Reduce reject noise and make counter semantics clearer for operators.
- [x] Expand automation schema and test coverage to include prolonged no-detect fail-window scenarios.
- [x] Add debug-detection instrumentation for bright-vs-dark root-cause diagnosis (raw overlay + structured logs + optional heuristics).

### 2.3 Not Started
- [ ] Re-balance guardrail thresholds to recover hard-scene detect duty-cycle while preserving class-switch stability.

## 3. Revised Method (Better Practice)
The draft said “Agent reads telemetry only.” In practice, best results came from dual observation:

1. Browser truth (actual operator page state):
- Playwright reads live DOM text and catches runtime/JS failures.

2. Backend truth (authoritative policy/acceptance state):
- ClientAI policy + publish acceptance from `/api/clientai`.
- Target consumer validity from `/api/vision/client-target/latest`.
- Pi runtime state from `/vision/state`.

3. Closed-loop execution:
- Detect mismatch -> patch code -> run checks -> sync to Pi -> verify on Pi -> re-probe page/API.

This avoids blind spots where API appears healthy but UI is stale/misleading, or vice versa.

## 4. Effective Metrics Contract (Current)
### 4.1 Required Health Signals
- `active_mode == client-ai`
- `ClientAI Infer(ms)` finite and within threshold (target < 500 ms, current ~40-60 ms)
- `ClientAI Model == best_cv451.onnx`
- `DETECTED` banner appears when object found
- Pi fallback rows suppressed in client-ai mode

### 4.2 Supporting Signals
- Publish counters trend (`ok`, `rej`, `skip`)
- Session state (`armed` vs `unarmed`) for publish gating interpretation
- Stream FPS > 20

## 5. Why This Is Better Than v1.0 Draft
- No dependency on a single new endpoint before progress can happen.
- Directly validates what user actually sees on Safari page.
- Catches front-end regressions immediately (label mismatches, stale indicators, missing overlays).
- Keeps deterministic Pi sync/verification discipline.

## 6. Next Implementation Plan (Prioritized)
### Phase N1: Operational Watchdog (high priority)
- File: `tools/agent_watchdog.py`
- Behavior:
  - Poll DOM snapshot via Playwright every 5s.
  - Poll APIs every 5s.
  - Emit structured health records to `Temp/snapshots/*.ndjson`.
  - Alert conditions:
    - mode mismatch
    - model mismatch
    - infer > threshold
    - no detection for prolonged window while target object present in scene profile

### Phase N2: Unified Diagnostic Endpoint
- Add server-side summarized endpoint (name TBD):
  - merges `api/clientai`, `vision/client-target/latest`, session state, and selected UI-facing fields.
- Purpose: reduce probe code complexity and make CI assertions simple.
- Note: `/diag/system-health.json` is already available and should be treated as the base health layer; N2 should focus on ClientAI/DOM-meaningful fields instead of duplicating watchdog checks.

### Phase N3: Regression Test Pack
- File: `tests/integration_test_clientai.py`
- Cases:
  - model default is `best_cv451.onnx`
  - client-ai mode suppresses Pi edge rows/toggle behavior
  - trained model decode path handles single-class output
  - detect banner appears on known-good static test image path

### Phase N4: Auto-correction Policy (controlled)
- Non-destructive adjustments only:
  - detection interval tuning
  - session-aware state reset
  - model fallback only when trained model repeatedly fails
- Keep auto-commit disabled by default; log suggested actions first.

## 7. Immediate Next Step
Focus on runtime-quality hardening (deployment is complete):
1. Detection consistency under hard scenes:
- run controlled low-light/occlusion test set and log confidence stability + lock persistence for `best`, `yolov8n`, and `Mix`.
- success gate: no unexpected lock thrash and confidence drops explained by scene events.

2. Remaining validation gap:
- execute the same model-consistency probe under explicit low-light and partial-occlusion scene tags.
- success gate: fresh-target metrics are available (`fresh_target_samples > 0`) and no unexplained lock thrash/drop events.

## 7B. Batch Progress Update (2026-02-13 17:49 CST)
Completed in this batch:
- [x] `/color` publish-counter semantics cleanup completed.
  - UI field now shows `accepted/rejected/local_skip`.
  - status line now includes `server_last_reject=<reason>` and explicit unarmed skip hint.
- [x] Watchdog parser compatibility updated.
  - `tools/agent_watchdog.py` now accepts both legacy `ok/rej/skip` and new `accepted/rejected/local_skip`.
- [x] Integration fixtures aligned with current UI semantics.
  - `tests/integration_test_clientai.py` publish-counter fixtures updated to `accepted/rejected/local_skip`.

## 7C. Next-Item Execution Update (2026-02-13 18:01 CST)
### 7C.1 Detection consistency probe progression
Added tool:
- `tools/clientai_model_consistency_probe.py` (Playwright + `/api/clientai` sampler, per-model stability summary, JSON artifact output).

Initial finding:
- Browser publish stream showed repeated `label_not_allowed` rejects for browser labels (`MT_ball`, `Yolo_Sport_Ball`), blocking fresh-target consistency metrics.

Fix applied:
- `Server/telemetry_api_server.py` label validation now normalizes aliases (`mt ball`, `yolo sport ball`) and accepts them alongside canonical labels.

Post-fix evidence artifact:
- `Temp/snapshots/clientai_model_consistency_probe_20260213_175937.json`
- Summary (live scene, armed):
  - `best`: `fresh_target_samples=9/10`, `conf_mean=0.7308`, `label_switches=0`, `drop_events=0`
  - `yolov8n`: `fresh_target_samples=9/9`, `conf_mean=0.8107`, `label_switches=0`, `drop_events=0`
  - `mix`: `fresh_target_samples=10/10`, `conf_mean=0.7641`, `label_switches=0`, `drop_events=0`

Interpretation:
- Fresh target updates are restored after label-normalization fix.
- Baseline live-scene stability across all model choices is now measurable and currently stable (no thrash/drop events in this sample window).
- Hard-scene (`low-light`, `partial-occlusion`) sweeps remain to fully close item 1.

### 7C.2 Watchdog runbook validation (Pi)
Executed recovery drill on Pi (`robotdog-agent-watchdog.service`):
- restart recovery: `3s` (`active`, NDJSON delta `+1`)
- stop/start recovery: `5s` (`active`, NDJSON delta `+1`)
- continuity check: NDJSON growth in 16s = `+4`

Result:
- Runbook-only recovery is verified within the `<= 2 minutes` gate.
- Watchdog operations runbook validation item is complete.

## 7D. Hard-Scene Sweep Update (2026-02-13 19:17 CST)
Executed both required scene-tagged probe runs:
- low-light artifact:
  - `Temp/snapshots/clientai_model_consistency_probe_20260213_191448.json`
- partial-occlusion artifact:
  - `Temp/snapshots/clientai_model_consistency_probe_20260213_191615.json`

Gate used:
- `fresh_target_samples > 0`
- `label_switches = 0`
- `drop_events = 0`

Observed summary:
1. low-light
- `best`: `fresh_target_samples=19`, `label_switches=0`, `drop_events=3`
- `yolov8n`: `fresh_target_samples=18`, `label_switches=0`, `drop_events=0`
- `mix`: `fresh_target_samples=18`, `label_switches=0`, `drop_events=4`

2. partial-occlusion
- `best`: `fresh_target_samples=18`, `label_switches=0`, `drop_events=5`
- `yolov8n`: `fresh_target_samples=19`, `label_switches=0`, `drop_events=0`
- `mix`: `fresh_target_samples=18`, `label_switches=0`, `drop_events=0`

Verdict:
- Fresh-target and lock-switch gates are satisfied.
- Strict zero-drop gate is not yet satisfied for `best` (both scenes) and `mix` (low-light).
- Close-loop completion remains pending one tuning+reprobe cycle for hard-scene confidence stability.

## 7E. Tuning + Re-Probe Update (2026-02-13 19:31 CST)
Applied runtime-safe tuning:
- `/color` browser runtime now includes MT-ball confidence stability guard (short-window, IoU-gated drop limiting) before advisory publish.
- Goal: suppress one-frame lighting dips without changing model weights.

Tuned-run artifacts:
- low-light tuned:
  - `Temp/snapshots/clientai_model_consistency_probe_20260213_192904.json`
- partial-occlusion tuned:
  - `Temp/snapshots/clientai_model_consistency_probe_20260213_193024.json`

Tuned summary:
1. low-light tuned
- `best`: `fresh_target_samples=18`, `label_switches=0`, `drop_events=2` (improved from 3)
- `yolov8n`: `fresh_target_samples=14`, `label_switches=0`, `drop_events=0`
- `mix`: `fresh_target_samples=17`, `label_switches=0`, `drop_events=0` (improved from 4)

2. partial-occlusion tuned
- `best`: `fresh_target_samples=18`, `label_switches=2`, `drop_events=2`
- `yolov8n`: `fresh_target_samples=17`, `label_switches=2`, `drop_events=1`
- `mix`: `fresh_target_samples=15`, `label_switches=0`, `drop_events=0`

Interpretation:
- Tuning reduced low-light instability and cleared `mix` drop-events.
- Partial-occlusion still shows class-switch noise (`Person`) and residual drops on `best`/`yolov8n`.
- Remaining blocker is now targeted: partial-occlusion class-stability hardening.

## 7F. Guardrail #4 Implementation Update (2026-02-13 21:34 CST)
Implemented in `/color` runtime:
- MT-ball minimum bbox area gate.
- 2-frame class-switch confirmation before switching dominant lock from `MT_ball` to non-ball class.

Code deployment:
- `Server/color_viewer/app_color.js` updated to `2026.02.13-69` and synced to Pi.
- `robot-color-viewer.service` restarted and active after deployment.

Verification artifacts:
- low-light (guard4):
  - `Temp/snapshots/clientai_model_consistency_probe_20260213_213212.json`
- partial-occlusion (guard4):
  - `Temp/snapshots/clientai_model_consistency_probe_20260213_213331.json`

Observed effect:
- class-switch suppression improved: `label_switches=0` across all three model choices in both scenes.
- drop-event control improved: mostly `drop_events=0` (low-light `best=1`, others `0`).
- tradeoff introduced: detect duty-cycle became too conservative (very low `detect_ratio` on `yolov8n`/`mix` and partial-occlusion `best`).

Conclusion:
- #4 behavior was implemented successfully.
- Remaining tuning is threshold calibration (mainly min-area gate aggressiveness) to restore practical detect duty-cycle without reintroducing class-switch noise.

## 7G. Extended Metrics + Rebalanced Tuning (2026-02-13 21:39 CST)
### 7G.1 Added probe metrics for diagnosis
`tools/clientai_model_consistency_probe.py` now reports:
- confidence distribution: `conf_p10/p50/p90`, `conf_std`
- latency distribution: `infer_ms_mean/std/p90`
- freshness/stale indicators: `fresh_target_samples`, `stale_ratio`, `target_age_ms_mean`
- tracking geometry quality: `bbox_area_mean/min/max/std`, `bbox_center_jitter`
- session/policy context: `armed_ratio`, `mode_mismatch_count`, `reject_reasons`

Why these matter for lighting problems:
- low-light instability typically appears as lower `conf_p10`, higher `conf_std`, and rising `drop_events`.
- occlusion often increases `bbox_center_jitter` and reduces `bbox_area_mean`.
- stale transport/publish issues surface as high `stale_ratio` and elevated `target_age_ms_mean`.

### 7G.2 Rebalanced guardrail tuning
Updated runtime threshold:
- `MT_ball` minimum bbox area gate lowered from `0.015` to `0.008` (keeping 2-frame class-switch debounce).

New artifacts:
- `Temp/snapshots/clientai_model_consistency_probe_20260213_214100.json`
- `Temp/snapshots/clientai_model_consistency_probe_20260213_214219.json`

Observed from new metrics:
1. class-switch stability remains controlled (`label_switches=0`).
2. hard-scene confidence floor remains the central limiter:
- example low-light `best`: `conf_p10=0.3188`, `bbox_area_mean=0.00343` (very small target footprint).
3. stale/armed context affects quality interpretation:
- stale ratios and `session_not_armed` / `rate_limited` rejects are now explicitly visible per run.

Current interpretation:
- #4 (class-switch suppression) is effective.
- additional gain now depends more on scene/optics and confidence-floor behavior than class-switch logic.

## 7H. Debug Detection Mode Delivery (2026-02-13 21:39 CST)
Implemented on `/color`:
1. Raw detection visibility
- debug mode renders all YOLO detections above configurable confidence floor (default `0.10`).
- raw boxes include label text: `class/conf/area/center`.
- existing final chosen bbox styling remains distinct.

2. Structured per-frame JSON logs
- outputs include:
  - `ts`, `conf_thres`, `iou_nms`, `imgsz`, `max_det`, `num_det`,
  - `dets_top10[{class,conf,x1,y1,x2,y2,area,cx,cy}]`,
  - `frame_mean_luma`, `frame_p95_luma`.
- sink options: browser console + optional on-screen debug panel.

3. Optional Ball Heuristics toggles
- ROI gate: `cy > roi_gate_y`.
- size gate: `area in [min_area,max_area]`.
- candidate selection: highest confidence after enabled filters.

4. Backward compatibility
- default runtime behavior is unchanged while debug mode stays `off`.
- existing UI sections are preserved; new controls are isolated in compact `Debug Detection (ClientAI)` block.

## 12. Execution Update (2026-02-13 16:05 CST)
### 12.1 Mode-by-mode `/color` validation
Executed with Playwright + API cross-check and saved artifact:
- `Temp/snapshots/model_selector_probe_20260213.json`

Observed:
1. `best` selector:
- UI select value = `best`
- UI model line = `best_cv451.onnx`
- API model = `best_cv451.onnx`

2. `yolov8n` selector:
- UI select value = `yolov8n`
- UI model line = `yolov8n_cv451.onnx`
- API model switched according to apply cycle in run (observed `yolov8n_cv451.onnx` in live probe batch; later stale-state sample showed fallback back to best after unarmed timeout cycle).

3. `Mix` selector:
- UI select value = `mix`
- UI model line = `Mix (best_cv451.onnx + yolov8n_cv451.onnx)`
- Dual-model runtime loop active in UI status (local infer attempts continue while select stays `mix`).

Notes:
- Priority/label path in implementation is `MT_ball > Yolo_Sport_Ball > Dog` and top-3 classes rendered by code path.
- In this specific DOM capture window, visible overlay was either none or single-class; non-`MT_ball` overlay color was not concurrently observed on the page during capture.

### 12.2 Watchdog execution
Commands:
- `.venv_browser/bin/python tools/agent_watchdog.py --once ...`
- `.venv_browser/bin/python tools/agent_watchdog.py --cycles 3 --interval 3 ...`

Artifacts:
- `Temp/snapshots/agent_watchdog_run_once_20260213.ndjson`
- `Temp/snapshots/agent_watchdog_run_3cycles_20260213.ndjson`

Result summary:
- once run: `PASS`
- 3-cycle run: `PASS -> WARN -> WARN` (warn reason: detection window accumulation while no confident target banner was present; no hard-fail condition).

### 12.3 N3 integration tests
Command:
- `python3 -m unittest tests.integration_test_clientai -v`

Result:
- `Ran 4 tests ... OK`
- Verified:
  - model-manifest default = `best_cv451.onnx`
  - `/diag/clientai.json` schema/status contract
  - `/color` ClientAI widget presence
  - watchdog once-output contract

### 12.4 Stress/fallback validation
1. Live threshold probe:
- `bash Server/ClientAI/clientai_perf_probe.sh 192.168.0.32 12 0.90 300`
- Result: `PASS` confidence and infer thresholds.
- Observed best sample: `sports ball` conf `0.9442`, infer `14.53 ms` (best), accepted counter increased.

2. Simulated lab probe:
- `bash Server/ClientAI/clientai_sim_lab.sh 192.168.0.32 12 0.90 300`
- Result: `PASS` confidence and infer thresholds.
- Final status: `top_conf=0.9442`, `infer_ms=30.18`.
- Rejection path observed after unarmed transition: `session_not_armed` (expected safety behavior).

### 12.5 Completion status after this batch
Completed in this batch:
- [x] Mode-by-mode selector verification with stored artifact
- [x] Watchdog runtime verification refresh
- [x] Integration regression run
- [x] Live + simulated stress/fallback verification
- [x] Documented evidence paths and outcomes

Remaining to fully close loop:
1. Items above were completed in Section 13 (closure update with artifacts).

## 13. Remaining-Items Closure (2026-02-13 16:21 CST)
### 13.1 Always-on watchdog deployment profile
Implemented and deployed:
- Unit template: `tools/systemd/robotdog-agent-watchdog.service`
- Installer: `tools/install_agent_watchdog_service.sh`
- Pi service state: `enabled` + `active` (`robotdog-agent-watchdog.service`)
- Runtime output confirmed:
  - `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Temp/snapshots/agent_watchdog.ndjson`
  - `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Temp/snapshots/agent_watchdog_supervisor.log`

Deployment note:
- Pi watchdog runs in API-only mode (`--no-dom`) using `/usr/bin/python3`; this avoids Playwright dependency on Pi and keeps service stable for continuous health logging.

### 13.2 Extended no-detect fail-path tests
Added deterministic tests:
- `tests/integration_test_clientai.py`
  - `test_watchdog_no_detect_window_warn_before_fail`
  - `test_watchdog_no_detect_window_eventual_fail`
  - `test_watchdog_once_output_contract_no_dom`

Execution:
- `python3 -m unittest tests.integration_test_clientai -v`
- Result: `OK (7 tests)`

### 13.3 Deterministic non-`MT_ball` overlay visual proof
Added proof tool:
- `tools/capture_overlay_yolo_color_proof.py`

Artifacts:
- Screenshot: `Temp/snapshots/overlay_yolo_color_proof_20260213_162111.png`
- JSON proof: `Temp/snapshots/overlay_yolo_color_proof_20260213_162111.json`

Verified fields from proof JSON:
- `overlay.label_text = "Yolo_Sport_Ball 0.94 [client]"`
- `overlay.box_display = "block"`
- `overlay.box_border_color = "rgba(255, 218, 92, 0.96)"`
- `overlay.label_bg_color = "rgba(255, 218, 92, 0.96)"`

### 13.4 Updated closure state
Previously listed remaining items are now completed:
- [x] always-on watchdog deployment wiring
- [x] long-window no-detect fail-path test extension (warn/fail deterministic coverage added)
- [x] non-`MT_ball` overlay color proof captured with persistent artifacts

## 7A. Live Status Snapshot (2026-02-13 15:11 CST)
### 7A.1 System/Endpoint
- `/diag/system-health.json` -> `PASS`, score `100`, summary `PASS fail=0 warn=0 score=100`.
- `/api/clientai` -> `active_mode=client-ai`, `model_id=best_cv451.onnx`, `provider=wasm`, `client_ai_capable=true`.

### 7A.2 Live `/color` Page Probe
- Metrics header: `Vision/Stream Metrics - ClientAI`.
- Infer label: `ClientAI Infer (ms)`.
- ClientAI status: active `client-ai`, unarmed, provider `wasm`, infer loop running.
- Detection banner visible: `DETECTED: MT_ball 0.88 [local]`.

### 7A.3 Current Completion State
- UI cleanup and Pi-edge wording removal: complete.
- System health endpoint and NDJSON logging: complete.
- N1 executable watchdog: implemented and validated.
- N1 supervision wrapper: implemented and validated in bounded mode.
- N2 compact summary endpoint: implemented.
- N3 baseline regression pack: implemented.
- Remaining primary blocker: deployment profile + extended failure-path test coverage.

## 8. Deterministic Acceptance Table (Execution Gate)
### 8.1 PASS
- `active_mode == client-ai`
- `model_id == best_cv451.onnx`
- `clientai_infer_ms` finite and `<= 500`
- detect banner is visible within probe window (`DETECTED: ...`)
- system health endpoint class is `PASS` or stable `WARN` with known non-critical reason

### 8.2 WARN
- session is unarmed and publish path reports skip-heavy counters
- infer remains finite but elevated (`> 500 ms`)
- intermittent no-detection window shorter than fail threshold
- system health class is `WARN` without fail-grade checks

### 8.3 FAIL
- mode mismatch (`active_mode != client-ai`) during ClientAI run profile
- model mismatch (`model_id != best_cv451.onnx`)
- infer unavailable (`NaN`, missing, or repeated zero-success loop)
- no detection over fail window under known-good profile scene
- system health endpoint class is `FAIL`

## 9. Remaining Development Backlog (Actionable)
### 9.1 N1 Operational Watchdog (next coding task)
- Implemented: `tools/agent_watchdog.py`.
- Poll every 5s:
  - Page: `http://192.168.0.32:8081/color`
  - APIs: `/api/clientai`, `/api/vision/client-target/latest`, `/diag/system-health.json` (via `:8090`) and `/vision/state` (via `:8081`)
- Emit one normalized record per cycle to:
  - `Temp/snapshots/agent_watchdog.ndjson`
- Required record keys:
  - `ts`, `status`, `summary`, `dom`, `api`, `checks`, `errors`
- Status mapping must use section 8 PASS/WARN/FAIL table.
- Suggested execution order:
  1. Completed: probe functions + normalized schema.
  2. Completed: PASS/WARN/FAIL mapping using section 8.
  3. Completed: CLI (`--once`, `--interval`, `--cycles`, `--output`, `--vision-base`).
  4. Completed: smoke output check (`--once`) and NDJSON contract verification.
  5. Completed: periodic mode check (3 cycles) with stable output.
  6. Completed: wrapper for persistent runtime supervision (`tools/agent_watchdog_supervisor.sh`).
  7. Next: deployment profile/service wiring for always-on watchdog runtime.

### 9.2 N2 Focused Diagnostic Summary (after N1)
- Add a compact endpoint for automation assertions (name TBD).
- Include only ClientAI/browser-facing fields not already covered by `/diag/system-health.json`.

### 9.3 N3 Regression Pack
- Add `tests/integration_test_clientai.py` with deterministic assertions:
  - default model `best_cv451.onnx`
  - mode consistency in ClientAI profile
  - detection banner path works on known-good sample
  - watchdog status mapping behaves as defined

## 10. Review Comments (2026-02-13 15:10)
1. Latest UI cleanup reduced operator clutter and removed visible Pi-edge semantics; this now aligns with current ClientAI-first operating intent.
2. Remaining delivery risk is no longer UI ambiguity; it is missing automation persistence (`tools/agent_watchdog.py`) and deterministic status artifacts.
3. N1 should be treated as the new P0 for close-loop completion; N2/N3 should not start before N1 produces stable NDJSON with section-8 mapping.
4. Keep Pi source-of-truth sync + Pi-side header verification mandatory for all `Server/` updates.

## 11. Review Comments (2026-02-13 14:30)
1. Status clarity is improved by explicitly splitting:
   - system-health completion (`/diag/system-health.json` + NDJSON on Pi), and
   - client-ai close-loop automation still pending (N1/N2/N3).
2. N2 should not re-implement watchdog logic already in `telemetry_api_server.py`; instead, build a focused summary for close-loop browser/client-ai assertions.
3. Add one deterministic acceptance table in next revision:
   - PASS conditions (mode/model/infer/decode/detect),
   - WARN conditions (unarmed publish skips, intermittent low confidence),
   - FAIL conditions (mode mismatch, model mismatch, infer unavailable, no detections under known-good profile window).
4. Keep Pi source-of-truth enforcement as a release gate for any Server-side close-loop changes.

## Revision History
- 2026-02-13 21:39 v1.20  Added close-loop instrumentation delivery note for bright-vs-dark diagnosis: debug mode now supports raw-all-detections overlay, structured per-frame JSON logs (console/panel), and optional ROI/size ball-heuristics filters with default-off backward compatibility.
- 2026-02-13 21:39 v1.19  Added extended probe metrics contract (confidence percentiles, latency stats, stale/armed/reject context, bbox area/jitter), executed rebalanced guardrail run (`MT_ball` min-area `0.008`), and documented updated hard-scene diagnosis with new artifacts.
- 2026-02-13 21:34 v1.18  Implemented requested guardrails (#4) in `/color` runtime (MT-ball min-area gate + 2-frame class-switch confirmation), executed low-light/partial-occlusion verification probes, confirmed class-switch suppression, and recorded current tradeoff/next tuning target (detect-ratio recovery).
- 2026-02-13 19:31 v1.17  Completed runtime-safe tuning + re-probe cycle: added MT-ball confidence stability guard in `/color`, captured tuned low-light/partial-occlusion artifacts, recorded measured improvements (notably `mix` drop-event reduction), and narrowed remaining gap to partial-occlusion class-switch/drop stabilization.
- 2026-02-13 19:17 v1.16  Executed requested `low-light` and `partial-occlusion` sweeps with artifacted probe output, recorded per-model hard-scene metrics against gate criteria, and updated remaining work to one runtime-safe tuning + re-probe cycle for `drop_events` reduction.
- 2026-02-13 18:01 v1.15  Executed next-item batch: added live model-consistency probe tooling/artifacts, fixed server label normalization (`MT_ball`/`Yolo_Sport_Ball`) to restore fresh target updates, validated watchdog recovery runbook on Pi with measured timing evidence (restart 3s, stop/start 5s), and narrowed remaining work to controlled low-light/occlusion sweeps.
- 2026-02-13 17:49 v1.14  Updated close-loop status after remaining-item progress: marked counter-semantics and fail-window test coverage as completed, added batch update for `/color` publish/reject clarity (`accepted/rejected/local_skip` + `server_last_reject`), and narrowed next steps to detection-consistency and watchdog runbook validation.
- 2026-02-13 17:43 v1.13  Updated `Immediate Next Step` to post-deployment priorities (runtime-quality hardening, counter semantics cleanup, long-window fail assertions, and watchdog operations runbook) now that watchdog deployment/proof items are complete.
- 2026-02-13 17:39 v1.12  Reorganized document layout: moved long `Revision History` block from top to bottom for cleaner status-first reading flow.
- 2026-02-13 16:25 v1.11  Finalized always-on watchdog deployment validation: fixed Pi unit runtime path/env reload issues, enabled API-only watchdog loop with continuous NDJSON output, and confirmed `robotdog-agent-watchdog.service` active + writing records on Pi.
- 2026-02-13 16:21 v1.10  Closed prior remaining items: deployed always-on watchdog service profile on Pi (`robotdog-agent-watchdog.service`, API-only `--no-dom` mode), expanded integration suite with deterministic no-detect warn/fail tests, and captured deterministic non-`MT_ball` overlay proof (`Yolo_Sport_Ball` yellow box screenshot + style JSON artifact).
- 2026-02-13 16:05 v1.9  Executed full close-loop validation batch: completed mode-by-mode `/color` selector probes (`best`/`yolov8n`/`Mix`) with Playwright+API evidence, re-ran watchdog once/3-cycles, passed N3 integration tests (`4/4`), and passed live/sim stress checks (`clientai_perf_probe.sh`, `clientai_sim_lab.sh`) including unarmed rejection-path confirmation.
- 2026-02-13 15:25 v1.8  Finalized this unattended batch: synced N2 telemetry endpoint to Pi, restarted telemetry service, verified live `/diag/clientai.json`, and completed N3 baseline integration test run (4/4 pass).
- 2026-02-13 15:23 v1.7  Advanced remaining phases: implemented N2 compact automation endpoint (`/diag/clientai.json`), added N3 baseline integration tests (`tests/integration_test_clientai.py`), and completed N1+wrapper runtime validation with stable PASS outputs.
- 2026-02-13 15:20 v1.6  Added persistent watchdog wrapper implementation (`tools/agent_watchdog_supervisor.sh`) with restart/backoff policy and bounded smoke-run validation (`WATCHDOG_ARGS='--cycles 1'`, `MAX_RESTARTS=1`).
- 2026-02-13 15:19 v1.5  Implemented N1 watchdog script (`tools/agent_watchdog.py`) with CLI and deterministic status mapping; validated `--once` and 3-cycle runs with NDJSON output and corrected `/vision/state` probe routing to color-viewer host (`:8081`).
- 2026-02-13 15:11 v1.4  Added fresh live status snapshot (system health + ClientAI + `/color` DOM probe), clarified current completion state, and updated immediate next-step execution sequence for remaining development.
- 2026-02-13 15:10 v1.3  Continued remaining development planning: recorded latest live UI cleanup completion (ClientAI-first metrics/actions), added deterministic PASS/WARN/FAIL acceptance table for close-loop checks, and expanded execution-ready backlog for N1/N2/N3 implementation.
- 2026-02-13 14:30 v1.2  Revised status after P0 completion: documented live `/diag/system-health.json` wiring, watchdog NDJSON runtime validation, Pi-side sync/verification completion, and added concrete review comments for next close-loop steps.
- 2026-02-13 11:03 v1.1  Marked completed items from live implementation, replaced abstract-only plan with current production-grade method (Playwright + API cross-check + Pi sync verification), and added prioritized next-implementation backlog.
- 2026-02-13 02:14 v1.0  Initial architecture draft.

End of document.
