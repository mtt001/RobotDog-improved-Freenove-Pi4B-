#!/usr/bin/env bash
# =====================================================================
# Freenove Robot Dog (Server side)
# smartdog.sh - systemd-first supervisor wrapper + housekeeping
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v2.53 – 2026-02-08 10:57
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
VERSION="v2.53 – 2026-02-08 10:57"
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

  echo "==== Established Clients (control:$PORT_CTRL) ===="
  if sudo ss -tn state established "sport = :$PORT_CTRL" 2>/dev/null | sed -n '2,$p' | grep -q .; then
    sudo ss -tn state established "sport = :$PORT_CTRL"
  else
    echo -e "${C_YELLOW}No active client.${C_RESET}"
  fi
  echo

  echo "==== Established Clients (video:$PORT_VIDEO) ===="
  if sudo ss -tn state established "sport = :$PORT_VIDEO" 2>/dev/null | sed -n '2,$p' | grep -q .; then
    sudo ss -tn state established "sport = :$PORT_VIDEO"
  else
    echo -e "${C_YELLOW}No active client.${C_RESET}"
  fi
  echo

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
