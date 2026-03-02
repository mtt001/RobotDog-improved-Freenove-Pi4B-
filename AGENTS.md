# AGENTS.md

## Version
v3.5 (2026-03-01 22:30 CST)

## Revision History
- 2026-03-01 22:30 v3.5 - Finalized HIL Demo simulation (v2.92). Restored simulator integrity and synchronized procedural 'Action.py' routines [FL:0, RL:1, RR:2, FR:3].
- 2026-03-01 22:15 v3.4 - Implementing HIL 'Action.py' Demo simulation (v2.90). Synchronized leg indexing with server-side source of truth.
- 2026-03-01 21:42 v3.3 - Hardened Servo Test (v2.88). Synchronized sweep runner to simTime. Fixed toggle logic.
- 2026-03-01 21:38 v3.2  Expanded Servo Gait View header (18px -> 30px) to provide dual vertical lanes for title/legend and leg labels, eliminating overlap.
- 2026-03-01 21:20 v2.8  Moved HFE tag-pill down by 10px to ensure clearance from HAA label.
- 2026-03-01 21:18 v2.7  Moved X-Z coordinate symbol to main header under 960x480 resolution text.
- 2026-03-01 21:05 v2.6  Added proactive Safari refresh rule for Mac UI tasks: agents must use AppleScript to reload pages immediately.
- 2026-03-01 20:56 v2.5  Updated contact information (corrected phone) and added Section 4 reporting requirement for clickable absolute file links.
- 2026-03-01 10:19 v2.4  Added Sections 11 and 12 regarding iMessage status updates and UI development first-pass quality standards.

---

# CORE PHILOSOPHY

Workspace operates in CONTROLLED_AUTONOMOUS mode:

- Maximum AI throughput
- Deterministic governance
- Premium visibility
- Oscillation detection
- No destructive automation
- No silent loops

Autonomy is allowed.
Blind recursion is forbidden.

---

# 1. HEADER & VERSION ENFORCEMENT

Mandatory for any modified file:

*.py, *.js, *.html, *.css, *.sh, *.md

Requirements:

- Update header/version block in same change.
- Use format: YYYY-MM-DD HH:MM (24h).
- Capture timestamp using:

  date '+%Y-%m-%d %H:%M %Z'

No silent exceptions.

---

# 2. PI SERVER SOURCE OF TRUTH

For any Server/ task:

Pi path:

/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/

Rules:

1. Edit locally.
2. Sync to Pi.
3. Verify header/version on Pi.
4. Verify runtime.
5. Only then mark task complete.

Never finalize Server work without Pi verification.

---

# 3. README IMPACT POLICY

If change affects:

- Client behavior → update Client/README.md
- Server behavior → update Server/README.md

Server README must be synced and verified on Pi before completion.

---

# 4. WEB/UI LIVE VERIFICATION

For any web/UI change:

- Verify no console errors.
- **Reporting**: Always include the absolute file link or URL in the task report for the user to click/hard-refresh.
- If no browser page exists, open one in Safari.
- **Proactive Refresh**: On Mac, the agent MUST proactively refresh Safari using `osascript` to target the builds' URL.
- Do not mark complete until confirmed.

---

# 5. AUTONOMOUS EXECUTION RULES

Agent may:

- Execute sequential todos
- Refactor across files
- Run regression sweeps

Agent must:

- Log phase transitions
- Avoid infinite retries
- Abort if validation exceeds limits

Validation timeout:

- 60 seconds per verification
- Max 2 retries

If exceeded:

- Log FAILURE
- Do not retry indefinitely

---

# 6. OSCILLATION PROTECTION

Within one logical task:

If:

- Same file modified >5 times
OR
- Same verification fails >3 times

Then:

- Log OSCILLATION DETECTED
- Snapshot state
- Stop retry loop
- Require new strategy

---

# 7. PREMIUM ESTIMATION ENGINE

Maintain internal estimate counters.

Multipliers:

0x
0.33x
1x
3x

Monthly quota baseline: 300 units

For each task:

- Record premium_start
- Record premium_end
- Calculate delta

Thresholds:

>50 → REMINDER
>100 → STRONG WARNING
>150 → CRITICAL

If STRONG or higher:

- Re-evaluate strategy
- Check oscillation

---

# 8. PREMIUM DASHBOARD (MANDATORY IN REPORT)

Every major checkpoint must generate:

Major-task threshold policy:

- Generate checkpoint reports only when task_delta > 1x.
- Do not generate checkpoint reports for task_delta <= 1x.
- If multiple minor steps belong to one objective, use aggregated delta.
- When aggregated delta > 1x, generate checkpoint report at objective completion.


iCloud/AI_Reports/YYYYMMDD_HHMM.md
iCloud/AI_Reports/YYYYMMDD_HHMM.json

Include:

================ PREMIUM DASHBOARD =================
Task: <task>
Model: <model>
Session Units: <x>
Task Delta: <x>
Monthly Estimate: <x>/300
[██████████░░░░░░░░░░░░░░░░░░░░░░░░]
Usage: <percent>%
Risk Level: LOW | MODERATE | HIGH | CRITICAL
Oscillation: YES/NO
====================================================

Bar width = 40 chars.

Risk Levels:

<60% LOW
60–80% MODERATE
80–95% HIGH
>95% CRITICAL

---

# 9. LIVE STATUS TELEMETRY (ANXIETY RELIEF)

Maintain rolling file:


iCloud/AI_Reports/latest_status.md

Task/stage completion reporting policy:

- At each finished task or major stage completion, update latest_status.md.
- Keep the update concise and iPhone-readable.
- In chat, explicitly notify whether AI_Reports was updated and list updated path(s).

Update when:

- Todo completes
- Phase changes
- Every 10 minutes
- Every +10 premium units

Include:

- Current Task
- Current Phase
- Timestamp
- Elapsed Time
- Session Units
- Task Delta
- Monthly Estimate
- Burn Velocity (units/hour)
- Oscillation Detected
- Warning Level

Burn velocity thresholds:

>40/hr → HIGH BURN WARNING
>60/hr → CRITICAL BURN WARNING

This file may be overwritten each update.

---

# 10. GIT SAFETY RULE

Never force push main automatically.

If divergence:

- Fetch
- Inspect
- Report
- Require explicit instruction before:

  git push --force-with-lease

---

# 11. STATUS MESSAGE CONTACT (USER-PROVIDED)

For completion/status iMessage trial updates, use:

- Phone: 0937991869
- Apple ID email: mengta941108@gmail.com

Notes:

- Attempt send to both when explicitly requested.
- If Messages automation fails (for example AppleEvent timeout), report failure clearly in chat and continue with iCloud/AI_Reports updates as fallback.

---

# 12. PRO-LEVEL UI FIRST-PASS STANDARD

For any UI/UX task, default execution quality must be professional-first, not rush-first.

Mandatory behavior:

- Before editing, define a concise acceptance checklist (readability, spacing, hierarchy, overlap, stability).
- Implement a complete first pass that targets production-level clarity instead of incremental quick fixes.
- Avoid “back-and-forth micro-patching” unless new requirements are introduced.
- If quality bar is not met after one pass, switch strategy immediately instead of repeating the same patch pattern.
- Treat repeated visual regressions as process failure and trigger OSCILLATION safeguards.

Completion rule:

- Do not mark UI tasks complete until visual output is stable, readable, and review-ready in one continuous verification pass.

---

END OF FILE

