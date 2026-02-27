<!--
File: Documents md/Live_Page_Verification_Protocol.md
Version: v1.0 (2026-02-27 08:32)
Revision History:
- 2026-02-27 08:32 v1.0 - Added beginner-safe live page verification protocol to prevent mismatch between user-visible page and agent verification.
-->

# Live Page Verification Protocol

## Goal
Ensure the page you are currently viewing is exactly the same page that was verified.

## Step 1: Run verification command
Use this exact command:

```bash
python3 /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Test/DigitalTwin/scripts/verify_live_page_sync.py --refresh-focused-safari --headless
```

## Step 2: Check expected result
The command should print JSON with:
- `"ok": true`
- `"checks.no_conflict_markers": true`
- `"checks.matches_origin_main": true`
- `"runtime.state.hasWebGLCanvas": true`
- `"runtime.state.hasOverlayPanel": true`

## Step 3: Open/confirm page path
The verified page path is:

```bash
open -a Safari "/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Test/DigitalTwin/pages/freenove_robotdog_3d_render.html"
```

## Step 4: Verification artifact
Verification JSON is saved at:

```text
/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Test/DigitalTwin/logs/live_page_state.json
```

## Minimal Troubleshooting
If `"ok": false`:
1. If `no_conflict_markers` is false, resolve merge markers in the page file first.
2. If `matches_origin_main` is false, sync the page from `origin/main` and rerun.
3. If WebGL/overlay checks are false, rerun with internet enabled (Three.js CDN import is required).
