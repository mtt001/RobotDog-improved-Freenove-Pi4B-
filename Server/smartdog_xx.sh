#!/usr/bin/env bash
set -euo pipefail
S=smartdog.service
case "${1:-status}" in
  start)   exec sudo /bin/systemctl start "$S" ;;
  stop)    exec sudo /bin/systemctl stop "$S" ;;
  restart) exec sudo /bin/systemctl restart "$S" ;;
  enable)  exec sudo /bin/systemctl enable "$S" ;;
  status|*)
    echo "== Service =="; /bin/systemctl is-active "$S" || true
    /bin/systemctl status "$S" --no-pager -l | sed -n '1,10p'
    echo; echo "== Python PIDs ==";
    ps -eo pid,ppid,cmd --sort=pid | egrep 'python3 .*(Server\.py|main\.py)' | grep -v egrep || echo "no smartdog python"
    echo; echo "== Ports (5001 control, 8001 video) ==";
    ss -lntp | egrep ':5001|:8001' || echo "ports closed"
  ;;
esac
