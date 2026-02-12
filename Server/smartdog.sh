#!/usr/bin/env bash
# =====================================================================
# Freenove Robot Dog (Server side)
# smartdog.sh - systemd-first supervisor wrapper + housekeeping
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v2.58 - 2026-02-09 15:24
# Author    : pi (admin) + Codex
# Notes     :
#   - Always prefer smartdog.service as the single process owner.
#   - "restart" performs housekeeping for abnormal states:
#       * stop service
#       * kill orphan/non-systemd main.py processes
#       * clear stale pid file
#       * restart service and verify ports 5001/8001
# ---------------------------------------------------------------------
# Revision History (key entries):
# v2.58 (2026-02-09 15:24) : improve local-SFU status reporting and treat SFU API 401 as reachable-but-authenticated.
# v2.57 (2026-02-09 15:15) : add Pi-hosted SFU/viewer service checks + startup supervision + Phase-1 endpoint status.
# v2.56 (2026-02-08 16:29) : add known-IP alias map for clearer device identification in status tables.
# v2.55 (2026-02-08 16:27) : enrich status output with peer device hints + SFU pipeline details + SFU client visibility block.
# v2.54 (2026-02-08 12:53) : supervise optional RTSP publisher service for SFU stream recovery.
# v2.53 (2026-02-08 10:57) : enforce date+time version format and sync to Pi server.
# v2.52 (2026-02-08 10:56) : header version format now includes date + time.
# v2.51 (2026-02-08) : restart recovery retry loop + post-restart validation
#                      to self-heal control/video port abnormal states.
# v2.50 (2026-02-08) : systemd-first start/stop/restart + orphan cleanup +
#                      port verification to enforce single clean root process.
# v2.39 (2025-11-06) : Compact status wrapper and robust port checks.
# =====================================================================

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
DOG_ROOT="$SCRIPT_DIR"
MAIN_PY="$DOG_ROOT/main.py"
LOG="$DOG_ROOT/smartdog.log"
PID_FILE="$DOG_ROOT/smartdog.pid"

PORT_CTRL=5001
PORT_VIDEO=8001
SERVICE_NAME="smartdog.service"
PUBLISHER_SERVICE_NAME="robot-publisher.service"
SFU_SERVICE_NAME="robot-sfu.service"
VIEWER_SERVICE_NAME="robot-viewer.service"
VERSION="v2.58 - 2026-02-09 15:24"
RESTART_MAX_RETRIES=3

# Always change to Server directory
cd "$DOG_ROOT" || { echo "ERROR: Cannot change to $DOG_ROOT"; exit 1; }

# color helpers (only when attached to a tty)
if [ -t 1 ]; then
  C_BOLD='\033[1m'; C_DIM='\033[2m'; C_RED='\033[31m'; C_YELLOW='\033[33m'
  C_GREEN='\033[32m'; C_RESET='\033[0m'
else
  C_BOLD=""; C_DIM=""; C_RED=""; C_YELLOW=""; C_GREEN=""; C_RESET=""
fi

print_banner() {
  echo -e "${C_BOLD}Freenove SmartDog${C_RESET}"
  echo -e "${C_DIM}Systemd-first supervisor wrapper${C_RESET}"
  echo -e "${C_DIM}${VERSION}${C_RESET}"
  echo -e "${C_GREEN}📍 SERVER SIDE${C_RESET}"
  echo
}

service_active() {
  systemctl is-active --quiet "$SERVICE_NAME"
}

service_enabled() {
  systemctl is-enabled --quiet "$SERVICE_NAME"
}

publisher_service_exists() {
  systemctl list-unit-files --type=service 2>/dev/null | awk '{print $1}' | grep -Fxq "$PUBLISHER_SERVICE_NAME"
}

publisher_service_active() {
  systemctl is-active --quiet "$PUBLISHER_SERVICE_NAME"
}

publisher_service_enabled() {
  systemctl is-enabled --quiet "$PUBLISHER_SERVICE_NAME"
}

sfu_service_exists() {
  systemctl list-unit-files --type=service 2>/dev/null | awk '{print $1}' | grep -Fxq "$SFU_SERVICE_NAME"
}

sfu_service_active() {
  systemctl is-active --quiet "$SFU_SERVICE_NAME"
}

sfu_service_enabled() {
  systemctl is-enabled --quiet "$SFU_SERVICE_NAME"
}

viewer_service_exists() {
  systemctl list-unit-files --type=service 2>/dev/null | awk '{print $1}' | grep -Fxq "$VIEWER_SERVICE_NAME"
}

viewer_service_active() {
  systemctl is-active --quiet "$VIEWER_SERVICE_NAME"
}

viewer_service_enabled() {
  systemctl is-enabled --quiet "$VIEWER_SERVICE_NAME"
}

ensure_publisher_service() {
  if ! publisher_service_exists; then
    echo -e "${C_YELLOW}Publisher service $PUBLISHER_SERVICE_NAME not installed (SFU RTSP auto-recovery disabled).${C_RESET}"
    return 0
  fi
  if ! publisher_service_enabled; then
    echo "Enabling $PUBLISHER_SERVICE_NAME ..."
    sudo systemctl enable "$PUBLISHER_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
  if publisher_service_active; then
    echo -e "${C_GREEN}$PUBLISHER_SERVICE_NAME already active.${C_RESET}"
  else
    echo "Starting $PUBLISHER_SERVICE_NAME ..."
    sudo systemctl start "$PUBLISHER_SERVICE_NAME" || true
  fi
}

ensure_sfu_service() {
  if ! sfu_service_exists; then
    echo -e "${C_YELLOW}SFU service $SFU_SERVICE_NAME not installed.${C_RESET}"
    return 0
  fi
  if ! sfu_service_enabled; then
    echo "Enabling $SFU_SERVICE_NAME ..."
    sudo systemctl enable "$SFU_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
  if sfu_service_active; then
    echo -e "${C_GREEN}$SFU_SERVICE_NAME already active.${C_RESET}"
  else
    echo "Starting $SFU_SERVICE_NAME ..."
    sudo systemctl start "$SFU_SERVICE_NAME" || true
  fi
}

ensure_viewer_service() {
  if ! viewer_service_exists; then
    echo -e "${C_YELLOW}Viewer service $VIEWER_SERVICE_NAME not installed.${C_RESET}"
    return 0
  fi
  if ! viewer_service_enabled; then
    echo "Enabling $VIEWER_SERVICE_NAME ..."
    sudo systemctl enable "$VIEWER_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
  if viewer_service_active; then
    echo -e "${C_GREEN}$VIEWER_SERVICE_NAME already active.${C_RESET}"
  else
    echo "Starting $VIEWER_SERVICE_NAME ..."
    sudo systemctl start "$VIEWER_SERVICE_NAME" || true
  fi
}

main_pids() {
  pgrep -f "python3.*main.py" || true
}

service_main_pid() {
  systemctl show "$SERVICE_NAME" -p MainPID --value 2>/dev/null || echo 0
}

orphan_main_pids() {
  local svc_pid
  svc_pid="$(service_main_pid)"
  main_pids | awk -v sp="$svc_pid" 'sp==""{sp=0} $1 != sp {print $1}'
}

kill_orphans() {
  local pids
  pids="$(orphan_main_pids | xargs echo || true)"
  if [ -n "${pids// }" ]; then
    echo "Housekeeping: killing orphan main.py PIDs: $pids"
    sudo kill -TERM $pids 2>/dev/null || true
    sleep 1
    local still
    still="$(orphan_main_pids | xargs echo || true)"
    if [ -n "${still// }" ]; then
      echo "Housekeeping: force-killing stubborn orphan PIDs: $still"
      sudo kill -KILL $still 2>/dev/null || true
    fi
  else
    echo "Housekeeping: no orphan main.py processes."
  fi
}

cleanup_stale_files() {
  rm -f "$PID_FILE" 2>/dev/null || true
}

wait_ports_ready() {
  local timeout_s="${1:-10}"
  local t=0
  while [ "$t" -lt "$timeout_s" ]; do
    if sudo ss -lnt "sport = :$PORT_CTRL" | sed -n '2,$p' | grep -q . \
      && sudo ss -lnt "sport = :$PORT_VIDEO" | sed -n '2,$p' | grep -q .; then
      return 0
    fi
    sleep 1
    t=$((t+1))
  done
  return 1
}

restart_with_recovery() {
  local attempt=1
  while [ "$attempt" -le "$RESTART_MAX_RETRIES" ]; do
    echo "Recovery restart attempt $attempt/$RESTART_MAX_RETRIES ..."
    sudo systemctl stop "$SERVICE_NAME" || true
    kill_orphans
    cleanup_stale_files
    sudo systemctl restart "$SERVICE_NAME"

    if wait_ports_ready 12; then
      ensure_sfu_service
      ensure_viewer_service
      ensure_publisher_service
      echo -e "${C_GREEN}Restart complete; ports $PORT_CTRL/$PORT_VIDEO are ready.${C_RESET}"
      return 0
    fi

    echo -e "${C_YELLOW}Attempt $attempt did not restore both ports.${C_RESET}"
    attempt=$((attempt+1))
    sleep 1
  done

  echo -e "${C_RED}Recovery failed after $RESTART_MAX_RETRIES attempts.${C_RESET}"
  echo "Hint: check journal logs with:"
  echo "  sudo journalctl -u $SERVICE_NAME -n 80 --no-pager"
  return 1
}

# Read battery voltage via project ADS7830.py (flock+timeout to avoid I2C hangs).
print_battery_status() {
  local LOCK="/var/lock/ads7830.lock" probe V
  sudo touch "$LOCK" 2>/dev/null || true
  probe=$(sudo flock -n "$LOCK" -c "timeout 3 /usr/bin/python3 \"$DOG_ROOT/ADS7830.py\"" 2>/dev/null || true)
  probe=$(printf "%s" "$probe" | tr -d '\000\r' | sed -n '1p' | tr -d '[:space:]')
  if [[ ! "$probe" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Battery voltage: N/A"; return
  fi
  V="$(printf "%.2f" "$probe")"
  if awk -v v="$V" 'BEGIN{exit !(v<6.40)}'; then
    echo -e "Battery voltage: ${C_RED}${C_BOLD}${V} V${C_RESET}  ${C_RED}${C_BOLD}LOW — charge/replace battery (< 6.40 V)!${C_RESET}"
  elif awk -v v="$V" 'BEGIN{exit !(v<7.20)}'; then
    echo -e "Battery voltage: ${C_YELLOW}${V} V${C_RESET}  (OK / medium)"
  else
    echo -e "Battery voltage: ${C_GREEN}${V} V${C_RESET}  (good)"
  fi
}

start() {
  print_banner
  [[ -f "$MAIN_PY" ]] || { echo -e "${C_RED}ERROR: main.py not found at: $MAIN_PY${C_RESET}"; return 1; }

  if ! service_enabled; then
    echo "Enabling $SERVICE_NAME ..."
    sudo systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
  fi

  if service_active; then
    echo -e "${C_YELLOW}$SERVICE_NAME already active.${C_RESET}"
  else
    echo "Starting $SERVICE_NAME ..."
    sudo systemctl start "$SERVICE_NAME"
  fi

  kill_orphans
  cleanup_stale_files
  ensure_sfu_service
  ensure_viewer_service
  ensure_publisher_service

  if wait_ports_ready 12; then
    echo -e "${C_GREEN}Started successfully via systemd; ports $PORT_CTRL/$PORT_VIDEO are ready.${C_RESET}"
  else
    echo -e "${C_RED}Start warning: service active but ports not fully ready yet.${C_RESET}"
    return 1
  fi
}

stop() {
  print_banner
  echo "Stopping $SERVICE_NAME ..."
  sudo systemctl stop "$SERVICE_NAME" || true
  kill_orphans

  # If anything still remains, hard stop all main.py processes.
  if main_pids | grep -q .; then
    echo "Final cleanup: force-killing all remaining main.py processes."
    sudo pkill -KILL -f "python3.*main.py" 2>/dev/null || true
  fi

  cleanup_stale_files
  if ! main_pids | grep -q .; then
    echo -e "${C_GREEN}Stopped cleanly; no main.py process remains.${C_RESET}"
  else
    echo -e "${C_RED}WARNING: process still running:${C_RESET}"
    pgrep -af "python3.*main.py" || true
    return 1
  fi
}

# Return success if port has a LISTEN socket or any ESTABLISHED sockets.
port_active_or_established() {
  local P="$1" LISTEN_OUT EST_OUT
  LISTEN_OUT="$(sudo ss -tnl "sport = :$P" 2>/dev/null | sed -n '2,$p' || true)"
  EST_OUT="$(sudo ss -tn state established "sport = :$P" 2>/dev/null | sed -n '2,$p' || true)"
  [ -n "$LISTEN_OUT" ] || [ -n "$EST_OUT" ]
}

get_publisher_env_var() {
  local key="$1" envs
  envs="$(systemctl show "$PUBLISHER_SERVICE_NAME" -p Environment --value 2>/dev/null || true)"
  printf "%s\n" "$envs" | tr ' ' '\n' | sed -n "s/^${key}=//p" | head -n 1
}

get_sfu_host() {
  local v
  v="$(get_publisher_env_var "SFU_HOST")"
  if [ -n "$v" ]; then
    echo "$v"
  else
    echo "192.168.0.198"
  fi
}

get_stream_path() {
  local v
  v="$(get_publisher_env_var "STREAM_PATH")"
  if [ -n "$v" ]; then
    echo "$v"
  else
    echo "robotdog"
  fi
}

get_local_pi_ip() {
  hostname -I 2>/dev/null | awk '{print $1}'
}

resolve_host_name() {
  local ip="$1" h
  h="$(getent hosts "$ip" 2>/dev/null | awk '{print $2; exit}' || true)"
  if [ -z "$h" ] && command -v avahi-resolve-address >/dev/null 2>&1; then
    h="$(avahi-resolve-address "$ip" 2>/dev/null | awk '{print $2; exit}' || true)"
  fi
  echo "${h:-n/a}"
}

mac_for_ip() {
  local ip="$1" m
  m="$(ip neigh show "$ip" 2>/dev/null | awk '{print $5; exit}' || true)"
  if [ -z "$m" ] && command -v arp >/dev/null 2>&1; then
    m="$(arp -n "$ip" 2>/dev/null | awk '/ether/ {print $3; exit}' || true)"
  fi
  echo "${m:-n/a}"
}

device_hint_for_peer() {
  local ip="$1" host="$2" sfu_host="$3" local_ip="$4" h_lc
  h_lc="$(printf "%s" "$host" | tr '[:upper:]' '[:lower:]')"
  if [ "$ip" = "127.0.0.1" ] || [ "$ip" = "::1" ]; then
    echo "Local loopback"
    return
  fi
  if [ -n "$local_ip" ] && [ "$ip" = "$local_ip" ]; then
    echo "This Pi (local)"
    return
  fi
  if [ "$ip" = "$sfu_host" ]; then
    if [ -n "$local_ip" ] && [ "$sfu_host" = "$local_ip" ]; then
      echo "This Pi (SFU host)"
    else
      echo "SFU host (remote)"
    fi
    return
  fi
  if printf "%s" "$h_lc" | grep -Eq 'iphone|ipad|ios'; then
    echo "iOS device (likely Safari)"
    return
  fi
  if printf "%s" "$h_lc" | grep -Eq 'mac|macbook|imac'; then
    echo "Mac client"
    return
  fi
  echo "LAN client (unclassified)"
}

known_peer_alias() {
  # Edit this map with your stable LAN IPs for exact labels in `smartdog status`.
  case "$1" in
    192.168.0.198) echo "Mac mini (SFU host)" ;;
    192.168.0.32)  echo "Raspberry Pi (server)" ;;
    *)             echo "" ;;
  esac
}

print_established_clients_detail() {
  local port="$1" title="$2" sfu_host local_ip raw idx
  sfu_host="$(get_sfu_host)"
  local_ip="$(get_local_pi_ip)"
  raw="$(sudo ss -tnp state established "sport = :$port" 2>/dev/null | sed -n '2,$p' || true)"
  echo "==== Established Clients (${title}:${port}) ===="
  if [ -z "$raw" ]; then
    echo -e "${C_YELLOW}No active client.${C_RESET}"
    echo
    return
  fi
  printf "%-3s %-21s %-21s %-25s %-30s %-18s %s\n" "#" "Peer Address" "Hostname" "Alias" "Device Hint" "MAC" "Process"
  idx=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    idx=$((idx+1))
    local peer host mac hint proc alias
    peer="$(printf "%s\n" "$line" | awk '{print $5}')"
    host="$(resolve_host_name "${peer%%:*}")"
    mac="$(mac_for_ip "${peer%%:*}")"
    alias="$(known_peer_alias "${peer%%:*}")"
    hint="$(device_hint_for_peer "${peer%%:*}" "$host" "$sfu_host" "$local_ip")"
    proc="$(printf "%s\n" "$line" | sed -n 's/.*users:\((.*)\)$/\1/p')"
    [ -n "$proc" ] || proc="n/a"
    [ -n "$alias" ] || alias="n/a"
    printf "%-3s %-21s %-21s %-25s %-30s %-18s %s\n" "$idx" "$peer" "$host" "$alias" "$hint" "$mac" "$proc"
  done <<< "$raw"
  echo
}

probe_rtsp_describe_status() {
  local host="$1" path="$2"
  python3 - "$host" "$path" <<'PY' 2>/dev/null
import socket, sys
host = sys.argv[1].strip()
path = "/" + sys.argv[2].strip().lstrip("/")
req = (f"DESCRIBE rtsp://{host}:8554{path} RTSP/1.0\r\n"
       "CSeq: 1\r\n"
       "Accept: application/sdp\r\n\r\n").encode()
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect((host, 8554))
    s.sendall(req)
    head = (s.recv(2048).decode("utf-8", "ignore").splitlines() or ["<empty>"])[0]
    print(head)
except Exception as e:
    print(f"RTSP_CHECK_FAIL: {e}")
finally:
    try:
        s.close()
    except Exception:
        pass
PY
}

probe_whep_options_status() {
  local host="$1" path="$2"
  curl -sS -m 3 -i -X OPTIONS "http://${host}:8889/${path}/whep" 2>/dev/null | head -n 1
}

probe_viewer_page_status() {
  local host="$1"
  curl -sS -m 3 -i "http://${host}:8080/webrtc_view.html" 2>/dev/null | head -n 1
}

probe_sfu_path_clients_api() {
  local host="$1" path="$2"
  python3 - "$host" "$path" <<'PY' 2>/dev/null
import json, sys, urllib.request
import urllib.error
host = sys.argv[1].strip()
path = sys.argv[2].strip().lstrip("/")
url = f"http://{host}:9997/v3/paths/get/{path}"
try:
    with urllib.request.urlopen(url, timeout=2) as r:
        data = json.load(r)
    readers = data.get("readers")
    if isinstance(readers, list):
        rc = len(readers)
    elif isinstance(readers, int):
        rc = readers
    else:
        rc = "n/a"
    source_ready = data.get("sourceReady")
    tracks = data.get("tracks")
    if isinstance(tracks, list):
        tc = len(tracks)
    else:
        tc = "n/a"
    print(f"API OK | sourceReady={source_ready} | readers={rc} | tracks={tc}")
except urllib.error.HTTPError as e:
    if e.code == 401:
        print("API_AUTH_REQUIRED: HTTP 401")
    else:
        print(f"API_HTTP_ERROR: HTTP {e.code}")
except Exception as e:
    print(f"API_UNAVAILABLE: {e}")
PY
}

print_sfu_streaming_status() {
  local sfu_host stream_path rtsp_status whep_status viewer_status api_status uplink_count local_ip
  sfu_host="$(get_sfu_host)"
  stream_path="$(get_stream_path)"
  local_ip="$(get_local_pi_ip)"

  rtsp_status="$(probe_rtsp_describe_status "$sfu_host" "$stream_path")"
  whep_status="$(probe_whep_options_status "$sfu_host" "$stream_path")"
  viewer_status="$(probe_viewer_page_status "$sfu_host")"
  api_status="$(probe_sfu_path_clients_api "$sfu_host" "$stream_path")"
  uplink_count="$(sudo ss -tn state established "dport = :8554" 2>/dev/null | awk -v host="$sfu_host" '$5 ~ "^"host":" {c++} END{print c+0}')"

  echo "==== SFU Streaming Detail ===="
  echo "SFU host           : $sfu_host"
  echo "Stream path        : $stream_path"
  if [ -n "$local_ip" ] && [ "$sfu_host" = "$local_ip" ]; then
    if publisher_service_active; then
      echo -e "Pi->SFU RTSP uplink: ${C_GREEN}local-host mode${C_RESET} (publisher service active)"
    else
      echo -e "Pi->SFU RTSP uplink: ${C_RED}local-host mode but publisher inactive${C_RESET}"
    fi
  elif [ "$uplink_count" -gt 0 ]; then
    echo -e "Pi->SFU RTSP uplink: ${C_GREEN}active${C_RESET} (connections: $uplink_count)"
  else
    echo -e "Pi->SFU RTSP uplink: ${C_YELLOW}not established${C_RESET}"
  fi
  echo "RTSP check (8554)  : ${rtsp_status:-n/a}"
  echo "WHEP check (8889)  : ${whep_status:-n/a}"
  echo "Viewer page (8080) : ${viewer_status:-n/a}"
  echo "Transport model    : Pi publish=RTSP(TCP) -> SFU relay; SFU readers=RTSP(TCP/UDP) or WebRTC(SRTP/UDP preferred)"
  echo "Client roles       : Mac mtDogMain reads RTSP path; iOS Safari reads WebRTC/WHEP path"
  echo

  echo "==== SFU Stream Clients (path:${stream_path}) ===="
  echo "SFU API (9997)     : ${api_status:-n/a}"
  echo "Note               : API_AUTH_REQUIRED means endpoint is reachable but credentials are required."
  echo
}

status() {
  print_banner

  echo "==== Service ===="
  echo -n "$SERVICE_NAME enabled: "
  if service_enabled; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_YELLOW}no${C_RESET}"; fi
  echo -n "$SERVICE_NAME active : "
  if service_active; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_RED}no${C_RESET}"; fi
  echo

  echo "==== Process ===="
  ps -eo user,pid,ppid,pcpu,start,time,cmd | head -n 1
  ps -eo user,pid,ppid,pcpu,start,time,cmd | grep -E "[m]ain.py" || echo "Not running."
  local svc_pid orphans
  svc_pid="$(service_main_pid)"
  orphans="$(orphan_main_pids | xargs echo || true)"
  echo "systemd MainPID: ${svc_pid:-0}"
  if [ -n "${orphans// }" ]; then
    echo -e "${C_RED}Orphan main.py PIDs: $orphans${C_RESET}"
  else
    echo -e "${C_GREEN}Orphan main.py PIDs: none${C_RESET}"
  fi
  echo

  echo "==== SFU Publisher Service ===="
  if publisher_service_exists; then
    echo -n "$PUBLISHER_SERVICE_NAME enabled: "
    if publisher_service_enabled; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_YELLOW}no${C_RESET}"; fi
    echo -n "$PUBLISHER_SERVICE_NAME active : "
    if publisher_service_active; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_RED}no${C_RESET}"; fi
  else
    echo -e "${C_YELLOW}$PUBLISHER_SERVICE_NAME not installed.${C_RESET}"
  fi
  echo

  echo "==== SFU / Viewer Host Services ===="
  if sfu_service_exists; then
    echo -n "$SFU_SERVICE_NAME enabled: "
    if sfu_service_enabled; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_YELLOW}no${C_RESET}"; fi
    echo -n "$SFU_SERVICE_NAME active : "
    if sfu_service_active; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_RED}no${C_RESET}"; fi
  else
    echo -e "${C_YELLOW}$SFU_SERVICE_NAME not installed.${C_RESET}"
  fi
  if viewer_service_exists; then
    echo -n "$VIEWER_SERVICE_NAME enabled: "
    if viewer_service_enabled; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_YELLOW}no${C_RESET}"; fi
    echo -n "$VIEWER_SERVICE_NAME active : "
    if viewer_service_active; then echo -e "${C_GREEN}yes${C_RESET}"; else echo -e "${C_RED}no${C_RESET}"; fi
  else
    echo -e "${C_YELLOW}$VIEWER_SERVICE_NAME not installed.${C_RESET}"
  fi
  echo

  echo "==== Listening Ports ===="
  for P in "$PORT_CTRL" "$PORT_VIDEO"; do
    local NAME="Control"
    [ "$P" = "$PORT_VIDEO" ] && NAME="Video  "
    if port_active_or_established "$P"; then
      echo -e "Port $P ($NAME) ${C_GREEN}active${C_RESET}"
    else
      echo -e "Port $P ($NAME) ${C_RED}not active${C_RESET}"
    fi
  done
  echo

  print_established_clients_detail "$PORT_CTRL" "control"
  print_established_clients_detail "$PORT_VIDEO" "video"
  print_sfu_streaming_status

  print_battery_status
  echo
  echo "==== Last 10 log lines ===="
  if [ -f "$LOG" ]; then tail -n 10 "$LOG"; else echo "No log yet."; fi
}

usage() {
  print_banner
  echo "Usage: $(basename "$0") {start|stop|restart|status|housekeep}"
  echo
  echo "Notes:"
  echo "  - start/stop/restart operate on $SERVICE_NAME"
  echo "  - if installed, start/restart also ensures $SFU_SERVICE_NAME/$VIEWER_SERVICE_NAME/$PUBLISHER_SERVICE_NAME are active"
  echo "  - restart performs housekeeping, retries recovery, and verifies ports"
}

housekeep() {
  print_banner
  echo "Running housekeeping only..."
  kill_orphans
  cleanup_stale_files
  echo "Housekeeping complete."
}

case "$1" in
  start|"")
    if [ -z "$1" ]; then
      echo -e "${C_DIM}No command specified, defaulting to 'start'${C_RESET}"
      echo -e "${C_DIM}To stop: $(basename "$0") stop${C_RESET}"
      echo
    fi
    start
    ;;
  stop)    stop    ;;
  restart)
    print_banner
    echo "Restarting with housekeeping..."
    restart_with_recovery || exit 1
    ;;
  status)  status  ;;
  housekeep) housekeep ;;
  *)       usage   ;;
esac
