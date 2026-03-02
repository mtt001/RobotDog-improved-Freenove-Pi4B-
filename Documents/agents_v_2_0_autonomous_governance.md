# AGENTS.md

## Version
v2.4 (2026-03-01 00:46 CST)

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

- Refresh focused page.
- If none exists, open one.
- Verify visually.
- Verify no console errors.
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

Reference table:

- [Copilot Premium Request scoring table](Copilot Premium Request scoring table.md)

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

END OF FILE

