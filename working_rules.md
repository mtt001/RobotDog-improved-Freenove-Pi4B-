# Working Rules

## Version
v1.5 (2026-02-09 15:02 local time)

## Revision History
- 2026-02-09 15:02 v1.5  Added mandatory README impact update rule for Client/Server, with Pi-side sync/verification gate for `Server/README.md`.
- 2026-02-09 14:16 v1.4  Added mandatory build-time verification rule (run maximum feasible tests) and explicit intervention escalation requirement.
- 2026-02-09 12:01 v1.3  Expanded Pi source-of-truth rule to all `Server/` code/docs with mandatory sync + verification.
- 2026-02-08 16:34 v1.2  Added Pi Server source-of-truth rule for `Server/smartdog.sh` edits.
- 2026-02-08 15:01 v1.1  Added local-time capture rule and timestamp-guard tooling workflow.
- 2026-02-08 11:24 v1.0  Initial rules snapshot.

## Rule: Header + Timestamp Required

When changing any code file or Markdown file, always update that file's header/version section.

- Applies to: `*.py`, `*.sh`, `*.js`, `*.html`, `*.css`, `*.md`
- Version must include date and time in this format: `YYYY-MM-DD HH:MM`
- Example: `v3.36 (2026-02-08 11:19)`

## Operating Behavior

- Do not finalize a task until header/version updates are done for all changed files.
- If a file has no header/version block, add one as part of the same edit.
- If user instruction conflicts with this rule, ask user to confirm override explicitly.

## Time Accuracy Enforcement

- Before writing a timestamp into any file header/version section, run:
  - `date '+%Y-%m-%d %H:%M %Z'`
- Use that exact local minute as the timestamp source of truth.
- For README version lines, run:
  - `bash tools/version_time_sync.sh Client/README.md Server/README.md`
- Keep hook installed to catch drift before commit:
  - `bash tools/install_time_guard_hook.sh`

## Pi Server Source of Truth

- For any change under local `Server/` (code or docs), Pi side is source of truth:
  - Local: `/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/`
  - Pi: `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/`
- Required before finalizing any `Server/` task:
  - Sync changed files (or whole folder) to Pi.
  - Verify on Pi that updated version/header lines exist.
- Recommended sync command:
  - `rsync -av --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.log' Server/ pi@192.168.0.32:/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/`
- Do not report `Server/` updates complete until Pi-side verification is done.

## README Impact Rule

- If task changes impact client behavior, configuration, startup, URLs, workflows, or diagnostics, update `Client/README.md` in the same task.
- If task changes impact server behavior, configuration, startup, APIs, workflows, or diagnostics, update `Server/README.md` in the same task.
- For server-impacting tasks, finalization requires Pi-side `Server/README.md` sync and verification with the rest of `Server/` source-of-truth checks.

## Build Verification And Escalation

- For every build/task completion, run the strongest verification an agent can execute in current environment:
  - relevant unit/integration tests
  - lint/static checks where applicable
  - targeted runtime/health checks for changed services
- If full verification cannot be completed (missing hardware, remote dependency, permissions, credentials, external service state), report:
  - exactly what was run
  - exactly what could not be run
  - the concrete intervention needed from user
- Escalate to user immediately when intervention/authorization/manual action is required; do not silently skip critical verification.
