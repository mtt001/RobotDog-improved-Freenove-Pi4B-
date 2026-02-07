#!/usr/bin/env python3
"""Mac Calendar bridge for Codex agent.

Commands:
- list-calendars
- list-events
- add-event
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from typing import List

DEFAULT_CALENDAR = "行事曆 iCloud"


def _run_osascript(script: str, args: List[str], timeout_sec: int = 8) -> subprocess.CompletedProcess:
    cmd = ["osascript", "-e", script, "--", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)


def _to_applescript_date(text: str) -> str:
    """Convert ISO-ish text to AppleScript date text.

    Accepted input examples:
    - 2026-02-08 09:00
    - 2026-02-08 09:00:00
    - 2026-02-08T09:00
    """
    normalized = text.replace("T", " ").strip()
    fmts = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]
    parsed = None
    for fmt in fmts:
        try:
            parsed = dt.datetime.strptime(normalized, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        raise ValueError(f"Unsupported datetime format: {text}")
    # Use ISO-like format to avoid locale parsing failures in AppleScript date().
    return parsed.strftime("%Y-%m-%d %H:%M:%S")

def _normalize_calendar_name(name: str) -> str:
    return (
        name.casefold()
        .replace("…", "")
        .replace("...", "")
        .replace(" ", "")
    )

def _fetch_calendars(timeout_sec: int = 8) -> List[str]:
    script = r'''
on run argv
  set outLines to {}
  tell application "Calendar"
    repeat with c in calendars
      set end of outLines to (name of c)
    end repeat
  end tell
  if (count of outLines) is 0 then return ""
  set AppleScript's text item delimiters to linefeed
  set outText to outLines as text
  set AppleScript's text item delimiters to ""
  return outText
end run
'''
    p = _run_osascript(script, [], timeout_sec=timeout_sec)
    if p.returncode != 0:
        return []
    out = p.stdout.strip()
    return [x.strip() for x in out.splitlines() if x.strip()]

def _resolve_calendar(requested: str | None) -> str:
    if requested and requested != DEFAULT_CALENDAR:
        print(
            f"Ignoring requested calendar '{requested}'. "
            f"Using fixed calendar alias '{DEFAULT_CALENDAR}'."
        )

    alias = DEFAULT_CALENDAR
    calendars = _fetch_calendars()
    if not calendars:
        return alias

    if alias in calendars:
        return alias

    n_alias = _normalize_calendar_name(alias)
    for cal in calendars:
        if _normalize_calendar_name(cal) == n_alias:
            return cal

    # Fallback for localized iCloud suffixes (e.g., trailing ellipsis)
    for cal in calendars:
        n_cal = _normalize_calendar_name(cal)
        if "行事曆" in cal and "icloud" in n_cal:
            return cal

    return alias


def list_calendars() -> int:
    script = r'''
on run argv
  set outLines to {}
  tell application "Calendar"
    repeat with c in calendars
      set end of outLines to (name of c)
    end repeat
  end tell
  if (count of outLines) is 0 then return ""
  set AppleScript's text item delimiters to linefeed
  set outText to outLines as text
  set AppleScript's text item delimiters to ""
  return outText
end run
'''
    try:
        p = _run_osascript(script, [])
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "Calendar permission prompt likely pending or blocked. "
            "Open System Settings > Privacy & Security > Calendars and allow access, then retry.\n"
        )
        return 124
    if p.returncode != 0:
        sys.stderr.write(p.stderr.strip() + "\n")
        return p.returncode
    out = p.stdout.strip()
    if not out:
        print("No calendars found.")
        return 0
    print(out)
    return 0

def confirm_default_calendar() -> int:
    try:
        calendars = _fetch_calendars()
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "Calendar permission prompt likely pending or blocked. "
            "Open System Settings > Privacy & Security > Calendars and allow access, then retry.\n"
        )
        return 124
    resolved = _resolve_calendar(DEFAULT_CALENDAR)
    if resolved in calendars:
        print(f"Confirmed default calendar alias '{DEFAULT_CALENDAR}' -> '{resolved}'")
        return 0
    print(f"Default calendar not found: {DEFAULT_CALENDAR}")
    return 3


def list_events(calendar: str, start: str, end: str) -> int:
    script = r'''
on run argv
  set startText to item 1 of argv
  set endText to item 2 of argv
  set calFilter to item 3 of argv
  set outLines to {}
  set sDate to date startText
  set eDate to date endText

  tell application "Calendar"
    repeat with c in calendars
      set cName to name of c
      if calFilter is "" or cName is calFilter then
        set evs to (every event of c whose start date ≥ sDate and start date < eDate)
        repeat with ev in evs
          set line to cName & "||" & (summary of ev) & "||" & ((start date of ev) as string) & "||" & ((end date of ev) as string)
          set end of outLines to line
        end repeat
      end if
    end repeat
  end tell

  if (count of outLines) is 0 then return ""
  set AppleScript's text item delimiters to linefeed
  set outText to outLines as text
  set AppleScript's text item delimiters to ""
  return outText
end run
'''
    try:
        p = _run_osascript(script, [start, end, calendar])
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "Calendar permission prompt likely pending or blocked. "
            "Open System Settings > Privacy & Security > Calendars and allow access, then retry.\n"
        )
        return 124
    if p.returncode != 0:
        sys.stderr.write(p.stderr.strip() + "\n")
        return p.returncode
    out = p.stdout.strip()
    if not out:
        print("No events found in range.")
        return 0
    for line in out.splitlines():
        parts = line.split("||")
        if len(parts) != 4:
            continue
        print(f"[{parts[0]}] {parts[1]} | {parts[2]} -> {parts[3]}")
    return 0


def add_event(calendar: str, title: str, start: str, end: str, notes: str) -> int:
    script = r'''
on run argv
  set calName to item 1 of argv
  set titleText to item 2 of argv
  set startText to item 3 of argv
  set endText to item 4 of argv
  set notesText to item 5 of argv
  set sDate to date startText
  set eDate to date endText

  tell application "Calendar"
    if not (exists calendar calName) then error "Calendar not found: " & calName

    set targetCal to calendar calName

    set newEvent to make new event at end of events of targetCal with properties {summary:titleText, start date:sDate, end date:eDate, description:notesText}
    make new display alarm at end of display alarms of newEvent with properties {trigger interval:0}
    return id of newEvent
  end tell
end run
'''
    start_text = _to_applescript_date(start)
    end_text = _to_applescript_date(end)

    try:
        p = _run_osascript(script, [calendar, title, start_text, end_text, notes])
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "Calendar permission prompt likely pending or blocked. "
            "Open System Settings > Privacy & Security > Calendars and allow access, then retry.\n"
        )
        return 124
    if p.returncode != 0:
        sys.stderr.write(p.stderr.strip() + "\n")
        return p.returncode

    print("Event created.")
    event_id = p.stdout.strip()
    if event_id:
        print(f"Event id: {event_id}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mac Calendar bridge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-calendars", help="List all calendar names")
    sub.add_parser(
        "confirm-default-calendar",
        help=f"Confirm fixed target calendar exists ({DEFAULT_CALENDAR})",
    )

    ev = sub.add_parser("list-events", help="List events in a time window")
    ev.add_argument("--calendar", default="", help=f"Ignored. Always uses '{DEFAULT_CALENDAR}'")
    ev.add_argument("--start", required=True, help="Start datetime: YYYY-MM-DD HH:MM")
    ev.add_argument("--end", required=True, help="End datetime: YYYY-MM-DD HH:MM")

    add = sub.add_parser("add-event", help="Create an event")
    add.add_argument("--calendar", default="", help=f"Ignored. Always uses '{DEFAULT_CALENDAR}'")
    add.add_argument("--title", required=True, help="Event title")
    add.add_argument("--start", required=True, help="Start datetime: YYYY-MM-DD HH:MM")
    add.add_argument("--end", required=True, help="End datetime: YYYY-MM-DD HH:MM")
    add.add_argument("--notes", default="", help="Event notes")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.cmd == "list-calendars":
        return list_calendars()
    if args.cmd == "confirm-default-calendar":
        return confirm_default_calendar()
    if args.cmd == "list-events":
        return list_events(_resolve_calendar(args.calendar), _to_applescript_date(args.start), _to_applescript_date(args.end))
    if args.cmd == "add-event":
        return add_event(_resolve_calendar(args.calendar), args.title, args.start, args.end, args.notes)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
