#!/usr/bin/env bash
#===============================================================================
# Project : Freenove Robot Dog - Remote Access Precheck
# File   : phaseE_remote_precheck.sh
# Author : Codex
#
# Version
# v1.0 (2026-02-10 07:40)
#
# Revision History
# v1.0 (2026-02-10 07:40) : Initial precheck for Safari remote-access readiness.
#===============================================================================

set -euo pipefail

MODE="${1:-tailscale}"  # tailscale | wan
CFG="${CFG_PATH:-/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/realtime_webrtc/sfu/mediamtx.yml}"

ok() { echo "[OK] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; }

if [[ ! -f "$CFG" ]]; then
  fail "Config not found: $CFG"
  exit 1
fi

echo "[INFO] mode=$MODE"
echo "[INFO] config=$CFG"

for s in robot-sfu.service robot-viewer.service robot-telemetry.service; do
  if systemctl is-active --quiet "$s"; then
    ok "$s active"
  else
    fail "$s not active"
  fi
done

if ss -lntup | grep -q ':8080'; then ok 'port 8080 listening'; else fail 'port 8080 not listening'; fi
if ss -lntup | grep -q ':8090'; then ok 'port 8090 listening'; else fail 'port 8090 not listening'; fi
if ss -lntup | grep -q ':8889'; then ok 'port 8889 listening'; else fail 'port 8889 not listening'; fi

if grep -q '^webrtc:' "$CFG"; then ok 'webrtc enabled in config'; else fail 'webrtc not configured'; fi

if [[ "$MODE" == "tailscale" ]]; then
  if command -v tailscale >/dev/null 2>&1; then
    TSIP="$(tailscale ip -4 2>/dev/null | head -n1 || true)"
    if [[ -n "$TSIP" ]]; then
      ok "tailscale ip detected: $TSIP"
      if grep -q "$TSIP" "$CFG"; then
        ok "tailscale ip is present in webrtcAdditionalHosts"
      else
        warn "tailscale ip not present in webrtcAdditionalHosts (recommended to add)"
      fi
    else
      warn "tailscale installed but no IPv4 assigned"
    fi
  else
    warn "tailscale binary not found"
  fi

  if grep -q '^webrtcEncryption: no' "$CFG"; then
    warn "webrtcEncryption=no (acceptable in private tailnet, but TLS still recommended)"
  fi
fi

if [[ "$MODE" == "wan" ]]; then
  if grep -q '^webrtcEncryption: yes' "$CFG"; then
    ok "webrtcEncryption=yes"
  else
    warn "webrtcEncryption is not enabled"
  fi

  if grep -q '^webrtcICEServers2:' "$CFG"; then
    ok "webrtcICEServers2 configured"
  else
    warn "webrtcICEServers2 missing (TURN/STUN likely not configured)"
  fi

  if grep -q '^api:' "$CFG"; then
    ok "api enabled"
  fi
fi

echo "[INFO] precheck complete"
