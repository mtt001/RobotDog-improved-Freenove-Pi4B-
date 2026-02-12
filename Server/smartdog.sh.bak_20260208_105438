#!/usr/bin/env bash
# =====================================================================
# Freenove Robot Dog (Server side)
# smartdog.sh - direct status wrapper for main.py (compact, readable)
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v2.39 – 2025-11-06
# Author    : pi (admin) + ChatGPT assistant
# Notes     :
#   - simplified port detection: port is "active" when LISTEN or any
#     ESTABLISHED connection exists (robust across IPv4/IPv6 and ss variants).
#   - keeps battery probe, start/stop/status helpers and concise comments.
# ---------------------------------------------------------------------
# Revision History (key entries):
# v2.39 (2025-11-06) : Compact & readable refactor. Treat port active when
#                      LISTEN or ESTABLISHED. Added stable ss filters and
#                      battery probe locking. Kept helpful comments.
# v2.38 (2025-11-06) : Use ss 'sport = :PORT' filter for reliable detection.
# v2.37 (2025-11-06) : Improved IPv4/IPv6 parsing and port extraction logic.
# v2.36 (2025-11-06) : ADS7830 probe changes; logging & flock protections.
# v2.34 (2025-11-04) : Initial fixes to python path and port/client status checks.
# =====================================================================

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
DOG_ROOT="$SCRIPT_DIR"
MAIN_PY="$DOG_ROOT/main.py"
LOG="$DOG_ROOT/smartdog.log"
PID_FILE="$DOG_ROOT/smartdog.pid"

PORT_CTRL=5001
PORT_VIDEO=8001
VERSION="v2.39 – 2025-11-06"

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
  echo -e "${C_DIM}Direct launcher (no systemd)${C_RESET}"
  echo -e "${C_DIM}${VERSION}${C_RESET}"
  echo -e "${C_GREEN}📍 SERVER SIDE${C_RESET}"
  echo
}

is_running() {    # PID_FILE is to check whether the recorded PID still exists before reporting status, avoiding duplicated launches.  (PID: process ID)
  [ -f "$PID_FILE" ] || return 1
  local _pid; _pid="$(cat "$PID_FILE" 2>/dev/null)"
  sudo kill -0 "$_pid" 2>/dev/null
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
  # Truncate log to last 1000 lines before starting
  if [ -f "$LOG" ]; then
    tail -n 1000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  fi
  if is_running; then echo -e "${C_YELLOW}Already running (PID $(cat "$PID_FILE")).${C_RESET}"; return; fi
  [[ -f "$MAIN_PY" ]] || { echo -e "${C_RED}ERROR: main.py not found at: $MAIN_PY${C_RESET}"; return 1; }
  
  # Output to both terminal and log file using tee
  sudo /usr/bin/python3 "$MAIN_PY" -tn 2>&1 | tee -a "$LOG" &
  echo $! > "$PID_FILE"
  sleep 1
  if pgrep -f "python3.*main.py" >/dev/null 2>&1; then
    echo -e "${C_GREEN}Started successfully.${C_RESET}"
  else
    echo -e "${C_RED}Failed to start. Check log: $LOG${C_RESET}"
  fi
}

stop() {
  print_banner
  
  # First, try to kill any python3 main.py processes directly (both parent and children)
  echo "Killing all main.py processes..."
  
  # Kill with SIGTERM first (graceful)
  sudo pkill -15 -f "python3.*main.py" 2>/dev/null || true
  sleep 1
  
  # Check if still running
  if pgrep -f "python3.*main.py" >/dev/null 2>&1; then
    echo "Forcing kill with SIGKILL..."
    sudo pkill -9 -f "python3.*main.py" 2>/dev/null || true
    sleep 1
  fi
  
  # Also try the PID file method for safety
  if [ -f "$PID_FILE" ]; then
    local _pid; _pid="$(cat "$PID_FILE")"
    echo "Also killing PID from file: $_pid"
    sudo kill -9 "$_pid" 2>/dev/null || true
  fi
  
  sleep 1
  
  # Final verification - kill any remaining orphaned processes
  if pgrep -f "python3.*main.py" >/dev/null 2>&1; then
    echo "Warning: Some main.py processes still alive. Force killing..."
    sudo pkill -9 -f "python3.*main.py" 2>/dev/null || true
    sleep 1
  fi
  
  rm -f "$PID_FILE"
  
  # Verify all processes are gone
  if ! pgrep -f "python3.*main.py" >/dev/null 2>&1; then
    echo -e "${C_GREEN}All processes killed successfully.${C_RESET}"
  else
    echo -e "${C_RED}WARNING: Some processes still running!${C_RESET}"
    ps aux | grep -E "[m]ain.py"
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

  echo "==== Process ===="
  ps -eo user,pid,ppid,pcpu,start,time,cmd | head -n 1
  # detect any main.py (started with or without -tn); fallback to pidfile check
  ps -eo user,pid,ppid,pcpu,start,time,cmd | grep -E "[m]ain.py" || echo "Not running."
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
  echo "Usage: $(basename "$0") {start|stop|restart|status}"
  echo
  echo "Note: Running without arguments defaults to 'start'"
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
    stop
    sleep 1
    # Clean log file on restart
    > "$LOG"
    echo "Log file cleared."
    start
    ;;
  status)  status  ;;
  *)       usage   ;;
esac
