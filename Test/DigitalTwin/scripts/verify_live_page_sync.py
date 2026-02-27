#!/usr/bin/env python3
"""
File: Test/DigitalTwin/scripts/verify_live_page_sync.py
Version: v1.0 (2026-02-27 08:32)
Revision History:
- 2026-02-27 08:32 v1.0 - Added live-page sync verifier to prevent mismatch between local viewed page and reported verification state (conflict/hash/runtime checks + optional focused Safari refresh).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    root_default = Path(__file__).resolve().parents[3]
    page_default = root_default / "Test" / "DigitalTwin" / "pages" / "freenove_robotdog_3d_render.html"
    out_default = root_default / "Test" / "DigitalTwin" / "logs" / "live_page_state.json"
    p = argparse.ArgumentParser(description="Verify local live-page sync and runtime state")
    p.add_argument("--repo-root", default=str(root_default))
    p.add_argument("--page-path", default=str(page_default))
    p.add_argument("--output-json", default=str(out_default))
    p.add_argument("--refresh-focused-safari", action="store_true")
    p.add_argument("--headless", action="store_true")
    return p.parse_args()


def refresh_focused_safari() -> dict:
    script = (
        'tell application "Safari" to activate\n'
        'tell application "System Events" to keystroke "r" using {command down}\n'
    )
    cp = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    return {
        "ok": cp.returncode == 0,
        "returncode": cp.returncode,
        "stderr": cp.stderr.strip(),
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    page_path = Path(args.page_path).resolve()
    out_path = Path(args.output_json).resolve()
    rel_page = str(page_path.relative_to(repo_root))

    result: dict = {
        "protocol": "live_page_sync_v1",
        "repo_root": str(repo_root),
        "page_path": str(page_path),
        "page_url": f"file://{page_path}",
        "checks": {},
        "runtime": {},
    }

    if not page_path.exists():
        result["checks"]["page_exists"] = False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1
    result["checks"]["page_exists"] = True

    if args.refresh_focused_safari:
        result["checks"]["safari_refresh"] = refresh_focused_safari()

    fetch_cp = run_cmd(["git", "fetch", "origin", "--prune"], repo_root)
    result["checks"]["git_fetch_ok"] = fetch_cp.returncode == 0

    local_text = page_path.read_text(encoding="utf-8")
    has_conflict = ("<<<<<<<" in local_text) or (">>>>>>>" in local_text) or ("=======" in local_text)
    result["checks"]["no_conflict_markers"] = not has_conflict
    result["checks"]["local_sha256"] = sha256_text(local_text)

    show_cp = run_cmd(["git", "show", f"origin/main:{rel_page}"], repo_root)
    if show_cp.returncode == 0:
        origin_text = show_cp.stdout
        result["checks"]["origin_main_sha256"] = sha256_text(origin_text)
        result["checks"]["matches_origin_main"] = (origin_text == local_text)
    else:
        result["checks"]["matches_origin_main"] = False
        result["checks"]["origin_main_sha256"] = None
        result["checks"]["git_show_error"] = show_cp.stderr.strip()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"file://{page_path}", wait_until="domcontentloaded")
        page.wait_for_timeout(1600)
        state = page.evaluate(
            """() => {
                const panel = document.getElementById('gaitDebugPanel');
                const ghostBtn = document.getElementById('ghostLegBtn');
                const dialValue = document.getElementById('gaitStepDialValue');
                const hasCanvas = !!document.querySelector('#app > canvas');
                const tick = (window.__robotDogDebug && window.__robotDogDebug.getHilReport)
                  ? window.__robotDogDebug.getHilReport().tick
                  : null;
                return {
                  hasWebGLCanvas: hasCanvas,
                  hasOverlayPanel: !!panel,
                  overlayVisible: panel ? !panel.classList.contains('hidden') : false,
                  ghostButtonText: ghostBtn ? ghostBtn.textContent : null,
                  stepDialValue: dialValue ? dialValue.textContent : null,
                  tick,
                };
            }"""
        )
        browser.close()
    result["runtime"]["state"] = state
    result["runtime"]["page_errors"] = errors
    result["runtime"]["ok"] = (
        state.get("hasWebGLCanvas") is True
        and state.get("hasOverlayPanel") is True
        and state.get("overlayVisible") is True
        and state.get("tick") is not None
        and len(errors) == 0
    )

    result["ok"] = (
        result["checks"].get("page_exists", False)
        and result["checks"].get("no_conflict_markers", False)
        and result["checks"].get("matches_origin_main", False)
        and result["runtime"].get("ok", False)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
