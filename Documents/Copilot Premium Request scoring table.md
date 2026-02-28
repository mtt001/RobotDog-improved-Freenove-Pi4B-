# Copilot Premium Request Scoring Table

## Version
v1.0 (2026-02-28 23:33 CST)

---

## Purpose
Use this table to score **project-side Copilot task effort** consistently.
This is an internal planning metric, not OpenAI billing.

---

## Scoring Multipliers

| Score | When to Use | Typical Example |
|---|---|---|
| 0x | Discussion only, no code or verification action | Q&A, idea check, wording clarification |
| 0.33x | Minor, localized change with minimal validation | Move one label by 10px, change one UI text |
| 1x | Standard implementation with normal validation | Add a small feature, update logic in 1–3 files |
| 3x | Complex or high-effort task | Multi-module refactor, repeated debugging, risky integration |

---

## Quick Decision Rules

1. If there is **no file change**, start at **0x**.
2. If there is **one small file edit** and **one refresh/visual check**, use **0.33x**.
3. If task touches **multiple files**, needs **tests/diagnostics**, or includes moderate debugging, use **1x**.
4. If task has **broad impact**, heavy debugging loops, or complex integration, use **3x**.

---

## Escalation Triggers
Escalate one level when any of these occur:

- Scope grows beyond original ask.
- More than one meaningful implementation pass is required.
- Validation fails and requires additional fix cycles.
- Cross-component changes are introduced.

---

## UI-Specific Defaults

- Pixel nudges (e.g., FR label +10px): **0.33x**
- Single text/label replacement: **0.33x**
- Small layout reorder in one panel: **0.33x** to **1x** (based on validation effort)
- UI change with regression fix: **1x**
- UI + runtime bug hunt across modules: **3x**

---

## Logging Template

```text
Task:
Start Score:
End Score:
Delta:
Reason:
Validation Performed:
Notes:
```

---

## Examples

1. "Move FR label right by 10px" + refresh Safari + one screenshot check → **0.33x**.
2. "Rename GAIT panel title" + no code (discussion only) → **0x**.
3. "Remove button + update CSS + fix broken listener + verify" → **1x**.
4. "Refactor gait projection and resolve repeated runtime regressions" → **3x**.
