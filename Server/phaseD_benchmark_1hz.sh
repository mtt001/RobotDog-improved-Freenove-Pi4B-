#!/usr/bin/env bash
# =============================================================================
# Freenove Robot Dog (Server side)
# phaseD_benchmark_1hz.sh - deterministic 1Hz benchmark harness for Pi vision.
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v1.4 (2026-02-11 21:57)
# Author    : pi (admin) + Codex
# -----------------------------------------------------------------------------
# Revision History:
# - 2026-02-11 21:57 v1.4  Fixed `/vision/metrics` parser to read nested `metrics.client_stream_fps` so active-viewer heartbeat contributes to KPI gates.
# - 2026-02-11 19:33 v1.3  Reduced benchmark self-overhead by consolidating JSON parsing into one Python pass per endpoint.
# - 2026-02-11 19:29 v1.2  Enforced true 1Hz loop pacing with elapsed-time compensation and fixed CPU iowait delta baseline variable.
# - 2026-02-11 19:27 v1.1  Fixed JSON parser helper for shell-safe extraction (avoid stdin redirection conflict in `json_field`).
# - 2026-02-11 19:23 v1.0  Initial 1Hz benchmark harness with tier profiles,
#                          runtime config push, CSV logging, and PASS/WARN/FAIL summary.
# =============================================================================

set -euo pipefail

PI_IP="${PI_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
VISION_API_PORT="${VISION_API_PORT:-8081}"
DURATION_SEC="${DURATION_SEC:-120}"
WARMUP_SEC="${WARMUP_SEC:-20}"
TIER="${TIER:-baseline}" # baseline|light|target|stress
STREAM_PATH="${STREAM_PATH:-robotdog}"
OUT_PREFIX="${OUT_PREFIX:-/tmp/phaseD_benchmark_${TIER}_$(date +%Y%m%d_%H%M%S)}"
CSV_OUT="${CSV_OUT:-${OUT_PREFIX}.csv}"
JSON_OUT="${JSON_OUT:-${OUT_PREFIX}.json}"

case "${TIER}" in
  baseline) YOLO_ENABLED=false; IMGSZ=320; INTERVAL_N=16 ;;
  light)    YOLO_ENABLED=true;  IMGSZ=256; INTERVAL_N=12 ;;
  target)   YOLO_ENABLED=true;  IMGSZ=320; INTERVAL_N=8  ;;
  stress)   YOLO_ENABLED=true;  IMGSZ=416; INTERVAL_N=5  ;;
  *) echo "invalid TIER=${TIER}" >&2; exit 2 ;;
esac

check_http_code() {
  local url="$1" expect="$2" method="${3:-GET}"
  local code
  code="$(curl -sS -m 3 -X "$method" -o /dev/null -w '%{http_code}' "$url" || true)"
  [[ "$code" == "$expect" ]]
}

read_cpu_stat() {
  # shellcheck disable=SC2002
  cat /proc/stat | awk '/^cpu /{print $2,$3,$4,$5,$6,$7,$8,$9}'
}

temp_c() {
  local t
  if command -v vcgencmd >/dev/null 2>&1; then
    t="$(vcgencmd measure_temp 2>/dev/null | sed -n "s/^temp=\\([0-9.]*\\).*/\\1/p")"
  else
    t="$(awk '{printf "%.1f", $1/1000.0}' /sys/class/thermal/thermal_zone0/temp 2>/dev/null || true)"
  fi
  echo "${t:-0}"
}

svc_pid() {
  local name="$1"
  local p
  p="$(systemctl show -p MainPID --value "$name" 2>/dev/null || echo 0)"
  [[ -n "$p" ]] || p=0
  echo "$p"
}

pid_stat() {
  local p="$1"
  if [[ "$p" =~ ^[0-9]+$ ]] && (( p > 1 )); then
    ps -p "$p" -o %cpu,%mem,rss= --no-headers 2>/dev/null | awk '{printf "%s,%s,%s", $1, $2, $3}'
  else
    echo "0,0,0"
  fi
}

echo "== Phase-D Benchmark 1Hz =="
echo "PI_IP=${PI_IP} tier=${TIER} duration=${DURATION_SEC}s warmup=${WARMUP_SEC}s"
echo "CSV_OUT=${CSV_OUT}"
echo "JSON_OUT=${JSON_OUT}"

echo "Applying vision profile..."
curl -sS -m 3 -X POST "http://${PI_IP}:${VISION_API_PORT}/vision/config" \
  -H 'Content-Type: application/json' \
  -d "{\"yolo_enabled\":${YOLO_ENABLED},\"tracking_enabled\":false,\"imgsz\":${IMGSZ},\"interval_n\":${INTERVAL_N},\"conf_threshold\":0.25,\"iou_threshold\":0.45}" >/dev/null || true

echo "Warmup ${WARMUP_SEC}s..."
sleep "${WARMUP_SEC}"

echo "ts,tier,temp_c,cpu_total_pct,cpu_iowait_pct,webrtc_ready,preferred_stream,vision_state,vision_health,vision_error,det_fps,track_fps,infer_ms,stream_fps_client,smartdog_cpu,smartdog_mem,smartdog_rss,sfu_cpu,sfu_mem,sfu_rss,publisher_cpu,publisher_mem,publisher_rss,telemetry_cpu,telemetry_mem,telemetry_rss,viewer_cpu,viewer_mem,viewer_rss" > "${CSV_OUT}"

read -r u n s idle iow irq sirq st <<<"$(read_cpu_stat)"
prev_total=$((u+n+s+idle+iow+irq+sirq+st))
prev_idle=$((idle+iow))
prev_iow="$iow"

sample=0

while (( sample < DURATION_SEC )); do
  loop_t0="$(date +%s.%N)"
  sample=$((sample + 1))
  ts="$(date '+%Y-%m-%d %H:%M:%S')"

  read -r u n s idle iow irq sirq st <<<"$(read_cpu_stat)"
  total=$((u+n+s+idle+iow+irq+sirq+st))
  idle_all=$((idle+iow))
  dt=$((total - prev_total))
  didle=$((idle_all - prev_idle))
  if (( dt <= 0 )); then dt=1; fi
  cpu_total_pct="$(awk -v dt="$dt" -v di="$didle" 'BEGIN{printf "%.1f", 100.0*(dt-di)/dt}')"
  cpu_iowait_pct="$(awk -v dt="$dt" -v iow="$iow" -v piow="$prev_iow" 'BEGIN{d=iow-piow; if(d<0)d=0; printf "%.1f", 100.0*d/dt}')"
  prev_total="$total"
  prev_idle="$idle_all"
  prev_iow="$iow"

  video_json="$(curl -sS -m 2 "http://${PI_IP}:${VISION_API_PORT}/video/status" || echo '{}')"
  vision_json="$(curl -sS -m 2 "http://${PI_IP}:${VISION_API_PORT}/vision/state" || echo '{}')"
  metrics_json="$(curl -sS -m 2 "http://${PI_IP}:${VISION_API_PORT}/vision/metrics" || echo '{}')"

  read -r webrtc_ready preferred_stream <<<"$(python3 - "$video_json" <<'PY'
import json,sys
try:
  o=json.loads(sys.argv[1])
except Exception:
  o={}
wr=((o.get("webrtc") or {}).get("ready"))
ps=o.get("preferred","")
print(("true" if wr else "false"), ps)
PY
)"
  read -r vision_state vision_health det_fps track_fps infer_ms <<<"$(python3 - "$vision_json" <<'PY'
import json,sys
try:
  o=json.loads(sys.argv[1]).get("state",{})
except Exception:
  o={}
print(o.get("state",""), o.get("health",""), o.get("det_fps",0), o.get("track_fps",0), o.get("infer_ms",0))
PY
)"
  vision_error="$(python3 - "$vision_json" <<'PY'
import json,sys
try:
  e=str(json.loads(sys.argv[1]).get("state",{}).get("error",""))
except Exception:
  e=""
print(e.replace(",",";").replace("\n"," "))
PY
)"
stream_fps_client="$(python3 - "$metrics_json" <<'PY'
import json,sys
try:
  o=json.loads(sys.argv[1])
except Exception:
  o={}
m=o.get("metrics") if isinstance(o, dict) else {}
if not isinstance(m, dict):
  m={}
print(m.get("client_stream_fps",0))
PY
)"

  smartdog_p="$(svc_pid smartdog.service)"; smartdog_m="$(pid_stat "$smartdog_p")"
  sfu_p="$(svc_pid robot-sfu.service)"; sfu_m="$(pid_stat "$sfu_p")"
  pub_p="$(svc_pid robot-publisher.service)"; pub_m="$(pid_stat "$pub_p")"
  tele_p="$(svc_pid robot-telemetry.service)"; tele_m="$(pid_stat "$tele_p")"
  view_p="$(svc_pid robot-color-viewer.service)"; view_m="$(pid_stat "$view_p")"

  echo "${ts},${TIER},$(temp_c),${cpu_total_pct},${cpu_iowait_pct},${webrtc_ready},${preferred_stream},${vision_state},${vision_health},${vision_error},${det_fps},${track_fps},${infer_ms},${stream_fps_client},${smartdog_m},${sfu_m},${pub_m},${tele_m},${view_m}" >> "${CSV_OUT}"
  loop_t1="$(date +%s.%N)"
  sleep_s="$(awk -v s="$loop_t0" -v e="$loop_t1" 'BEGIN{d=1.0-(e-s); if(d<0)d=0; printf "%.3f", d}')"
  sleep "$sleep_s"
done

python3 - "${CSV_OUT}" "${JSON_OUT}" <<'PY'
import csv, json, sys, statistics
csv_path, out_path = sys.argv[1], sys.argv[2]
rows = []
with open(csv_path, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

def fnum(row, k):
    try:
        return float((row.get(k) or "0").strip())
    except Exception:
        return 0.0

def pct(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    i = int(round((len(s)-1) * p))
    return s[max(0, min(len(s)-1, i))]

temps = [fnum(r, "temp_c") for r in rows]
cpus = [fnum(r, "cpu_total_pct") for r in rows]
det = [fnum(r, "det_fps") for r in rows]
inf = [fnum(r, "infer_ms") for r in rows]
sfps = [fnum(r, "stream_fps_client") for r in rows if fnum(r, "stream_fps_client") > 0]
webrtc_ok = sum(1 for r in rows if (r.get("webrtc_ready") or "").lower() == "true")
errors = [r.get("vision_error","") for r in rows if r.get("vision_error","").strip()]

result = "PASS"
reasons = []
if pct(temps, 0.95) >= 80.0:
    result = "FAIL"; reasons.append("temp_p95>=80C")
elif pct(temps, 0.95) >= 78.0:
    if result != "FAIL": result = "WARN"
    reasons.append("temp_p95>=78C")
if pct(cpus, 0.95) > 90.0:
    result = "FAIL"; reasons.append("cpu_p95>90")
elif pct(cpus, 0.95) > 85.0 and result != "FAIL":
    result = "WARN"; reasons.append("cpu_p95>85")
if sfps:
    if pct(sfps, 0.95) < 18.0:
        result = "FAIL"; reasons.append("stream_fps_p95<18")
    elif pct(sfps, 0.95) < 20.0 and result != "FAIL":
        result = "WARN"; reasons.append("stream_fps_p95<20")
else:
    if result != "FAIL":
        result = "WARN"
    reasons.append("no_client_fps_samples")
if errors and result != "FAIL":
    result = "WARN"
    reasons.append("vision_errors_present")

summary = {
    "result": result,
    "reasons": reasons,
    "samples": len(rows),
    "temp_c": {"avg": statistics.fmean(temps) if temps else 0.0, "p95": pct(temps, 0.95), "max": max(temps) if temps else 0.0},
    "cpu_total_pct": {"avg": statistics.fmean(cpus) if cpus else 0.0, "p95": pct(cpus, 0.95), "max": max(cpus) if cpus else 0.0},
    "det_fps": {"avg": statistics.fmean(det) if det else 0.0, "p95": pct(det, 0.95)},
    "infer_ms": {"avg": statistics.fmean(inf) if inf else 0.0, "p95": pct(inf, 0.95)},
    "stream_fps_client": {"avg": statistics.fmean(sfps) if sfps else 0.0, "p95": pct(sfps, 0.95) if sfps else 0.0},
    "webrtc_ready_ratio": (webrtc_ok / len(rows)) if rows else 0.0,
    "vision_error_count": len(errors),
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY

echo "Done. CSV=${CSV_OUT} JSON=${JSON_OUT}"
