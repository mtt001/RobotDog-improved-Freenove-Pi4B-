#!/bin/bash
# =====================================================================
#  File:        syncPi.sh
#  Purpose:     Two-way sync utility between MacBook and Raspberry Pi
#  Description: Keeps Freenove Robot Dog code identical on both systems
#               (Pi ↔ Mac), supports compare / pull / push, and logs actions.
# ---------------------------------------------------------------------
#  Author:      MT
#  Created:     2025-10-29
#  Last Update: 2025-10-29
# ---------------------------------------------------------------------
#  Usage:
#     ./syncPi.sh compare   # show differences only
#     ./syncPi.sh pull      # copy from Pi → Mac
#     ./syncPi.sh push      # copy from Mac → Pi
#     ./syncPi.sh           # interactive menu
# =====================================================================

# === Configuration ===
# previous static MAC_PATH replaced with location-aware logic so the script
# works when placed in either Code/ (project root) or Code/Server/.
PI_USER=pi
PI_HOST=192.168.0.32
PI_PATH="/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/"

# Resolve script directory and project root so MAC_PATH and LOG_FILE are correct
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "Server" ]; then
  PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
  PROJECT_ROOT="$SCRIPT_DIR"
fi

MAC_PATH="${PROJECT_ROOT}/Server/"
LOG_FILE="${PROJECT_ROOT}/syncPi.log"

RSYNC_OPTS="-avc --delete --exclude=.DS_Store --exclude=__pycache__"
# ...existing code...
log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg" | tee -a "$LOG_FILE"
}

confirm_proceed() {
  local prompt="${1:-Proceed? [y/N]: }"
  read -r -p "$prompt" answer
  case "$answer" in
    [yY]|[yY][eE][sS]) return 0 ;;
    *) return 1 ;;
  esac
}

# show diffs (dry-run + itemize) and return number of changed lines
show_diffs() {
  local direction="$1"   # "push" or "pull" or "compare"
  local out
  if [ "$direction" = "push" ]; then
    log "Dry-run (Mac → Pi): listing changes..."
    out=$(rsync -n --itemize-changes $RSYNC_OPTS "${MAC_PATH}" "${PI_USER}@${PI_HOST}:${PI_PATH}" 2>/dev/null)
  elif [ "$direction" = "pull" ]; then
    log "Dry-run (Pi → Mac): listing changes..."
    out=$(rsync -n --itemize-changes $RSYNC_OPTS "${PI_USER}@${PI_HOST}:${PI_PATH}" "${MAC_PATH}" 2>/dev/null)
  else
    log "Dry-run (both directions): listing changes..."
    out="$(rsync -n --itemize-changes $RSYNC_OPTS "${PI_USER}@${PI_HOST}:${PI_PATH}" "${MAC_PATH}" 2>/dev/null)"
    out="${out}"$'\n'
    out+=$(rsync -n --itemize-changes $RSYNC_OPTS "${MAC_PATH}" "${PI_USER}@${PI_HOST}:${PI_PATH}" 2>/dev/null)
  fi

  if [ -z "$out" ]; then
    echo ""
    echo "  (no changes detected)"
    return 0
  fi

  echo ""
  echo "=== Changes (itemized) ==="
  echo "$out"
  echo "=========================="
  # count non-empty lines
  local count
  count=$(printf "%s\n" "$out" | sed '/^\s*$/d' | wc -l)
  echo "Files/entries that would be changed: $count"
  return $count
}

# === Core functions ===
compare() {
  log "Comparing Pi → Mac ..."
  rsync -n $RSYNC_OPTS ${PI_USER}@${PI_HOST}:${PI_PATH} ${MAC_PATH} | tee -a "$LOG_FILE"
  log "Comparing Mac → Pi ..."
  rsync -n $RSYNC_OPTS ${MAC_PATH} ${PI_USER}@${PI_HOST}:${PI_PATH} | tee -a "$LOG_FILE"
  log "Compare complete."
}

pull() {
  log "Preparing to pull from Pi → Mac ..."
  # show diffs and ask confirm
  show_diffs pull
  if ! confirm_proceed "Confirm pull (Pi → Mac)? This will modify local files. [y/N]: "; then
    log "Pull cancelled by user."
    echo "Pull cancelled."
    return 1
  fi

  # create a backup on the Pi before pulling (so source is saved)
  if remote_backup; then
    log "Remote backup created; proceeding with pull."
  else
    log "Abort pull: remote backup failed."
    echo "Abort pull: remote backup failed."
    return 1
  fi

  log "Pulling from Pi → Mac ..."
  rsync $RSYNC_OPTS ${PI_USER}@${PI_HOST}:${PI_PATH} ${MAC_PATH} | tee -a "$LOG_FILE"
  log "✅ Sync complete (Pi → Mac)."
  echo "Remote backup was saved under the Pi path shown above."
}

# --- Auto-backup on Pi before push ---
remote_backup() {
  # create timestamped backup directory on the Pi and copy Server contents into it
  TS="$(date '+%Y%m%d_%H%M%S')"
  BACKUP_DIR="${PI_PATH%/}_Backup_${TS}"
  log "Creating remote backup: ${BACKUP_DIR}"
  # Use ssh to run mkdir + cp -a on the Pi (cp -a preserves attributes)
  if ssh "${PI_USER}@${PI_HOST}" "mkdir -p '${BACKUP_DIR}' && cp -a '${PI_PATH%/}/' '${BACKUP_DIR}/'"; then
    log "Remote backup created: ${BACKUP_DIR}"
    # also print to stdout so user sees it immediately
    echo ""
    echo "Remote backup folder created on Pi:"
    echo "  ${BACKUP_DIR}"
    echo ""
    return 0
  else
    log "ERROR: remote backup failed"
    return 1
  fi
}

push() {
  log "Preparing to push from Mac → Pi ..."
  # show diffs and ask confirm
  show_diffs push
  if ! confirm_proceed "Confirm push (Mac → Pi)? This will modify remote files. [y/N]: "; then
    log "Push cancelled by user."
    echo "Push cancelled."
    return 1
  fi

  # create a backup on the Pi before actually pushing files
  if remote_backup; then
    log "Proceeding with push (remote backup OK)."
  else
    log "Abort push: remote backup failed."
    echo "Abort push: remote backup failed."
    return 1
  fi

  rsync $RSYNC_OPTS ${MAC_PATH} ${PI_USER}@${PI_HOST}:${PI_PATH} | tee -a "$LOG_FILE"
  log "✅ Sync complete (Mac → Pi)."
  echo "Remote backup was saved under the Pi path shown above."
}

menu() {
  echo "=============================================="
  echo "   Freenove Robot Dog Sync Utility"
  echo "=============================================="
  echo "  Created:  2025-10-29"
  echo "  Host:     ${PI_HOST}"
  echo "  Pi Path:  ${PI_PATH}"
  echo "  Mac Path: ${MAC_PATH}"
  echo "  Log File: ${LOG_FILE}"
  echo "----------------------------------------------"
  echo "1) Compare only"
  echo "2) Pull from Pi → Mac"
  echo "3) Push from Mac → Pi"
  echo "q) Quit"
  echo "----------------------------------------------"
  read -p "Select an option: " opt
  case $opt in
    1) compare ;;
    2) pull ;;
    3) push ;;
    q|Q) log "Exited syncPi.sh."; echo "Bye"; exit 0 ;;
    *) echo "Invalid option" ;;
  esac
}

# === Main ===
log "----------------------------------------------"
log "syncPi.sh started by ${USER}"
case "$1" in
  compare) compare ;;
  pull) pull ;;
  push) push ;;
  *) menu ;;
esac
log "syncPi.sh finished."
log "----------------------------------------------"
