# AGENTS.md

## Version
v1.4 (2026-02-28 22:39 local time)

## Revision History
- 2026-02-28 22:39 v1.4  Added mandatory post-change web UI live visual check and focused-page refresh/open rule (create/open a page when none is focused).
- 2026-02-09 15:02 v1.3  Added mandatory README update rule for impacted Client/Server changes, including Pi-side sync/verification for `Server/README.md`.
- 2026-02-09 14:03 v1.2  Added explicit Pi `Server/` source-of-truth policy and mandatory sync/verification rule before finalizing `Server/` tasks.
- 2026-02-08 15:01 v1.1  Added explicit local-time capture + timestamp sync/hook enforcement steps.
- 2026-02-08 11:24 v1.0  Initial persistent working rules.

## Persistent Working Rules

1. Header update is mandatory on every code or Markdown change.
- Scope: any edited `*.py`, `*.sh`, `*.js`, `*.html`, `*.css`, `*.md` file.
- Requirement: update that file's header/version history in the same change.

2. Version entries must include date and time.
- Required format: `YYYY-MM-DD HH:MM` (24-hour).
- Example: `v2.18 (2026-02-08 11:19)`.

3. No silent exceptions.
- If a file has no existing header block, add one when editing.
- If any conflict or ambiguity exists, ask the user for confirmation before proceeding.

4. Compliance check before finish.
- Before marking work done, verify changed files include header/version updates with timestamp.

5. Timestamp source of truth (local clock).
- Before editing any version/header timestamp, run:
  - `date '+%Y-%m-%d %H:%M %Z'`
- Use that exact local minute in file version lines.
- If multiple files are updated in one change set, use the same captured timestamp unless edits happen across different minutes.

6. Enforced tooling before commit/finalization.
- Run timestamp sync when touching README versions:
  - `bash tools/version_time_sync.sh Client/README.md Server/README.md`
- Ensure pre-commit guard is installed:
  - `bash tools/install_time_guard_hook.sh`

7. Pi `Server/` source of truth policy.
- For any work under local `Server/` (code or docs), treat Pi-side `Server/` as source of truth.
- Local `Code/Server/` is a synchronized mirror/backup for convenient review.
- Before finalizing any `Server/` task:
  - sync changed `Server/` content to Pi,
  - verify on Pi that updated header/version lines are present.
- Do not report `Server/` task complete until Pi-side verification is done.

8. README impact update policy.
- If a change impacts client behavior/workflow/configuration, update `Client/README.md` in the same task.
- If a change impacts server behavior/workflow/configuration, update `Server/README.md` in the same task.
- For server-impacting changes, do not finalize until Pi-side `Server/README.md` is synced and verified.

9. Web/UI live verification and focused-page refresh policy.
- For any web/UI change (`*.html`, UI JS/CSS affecting browser output), perform a live visual check after edits.
- Refresh the currently focused web page in the editor after each UI change set.
- If no focused/available web page exists, open a new page for verification (Simple Browser or equivalent) and verify there.
- Do not mark UI tasks complete until the refreshed/opened page is visually verified.
