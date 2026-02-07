# Mac Calendar Agent Bridge

This tool lets Codex run Calendar actions on your Mac through AppleScript.

## Permission setup (one time)
1. Open `System Settings -> Privacy & Security -> Calendars`.
2. Enable Calendar access for the terminal app you use to run Codex.
3. Run the test command below. macOS may show an additional permission popup.

Shortcut to open the Calendar privacy page:
```bash
./open_calendar_privacy.sh
```

## Commands
Fixed target calendar:
```bash
行事曆 iCloud
```

Confirm fixed calendar exists:
```bash
python3 calendar_agent.py confirm-default-calendar
```

List calendars:
```bash
python3 calendar_agent.py list-calendars
```

List events in a time window:
```bash
python3 calendar_agent.py list-events --start "2026-02-08 00:00" --end "2026-02-09 00:00"
```

Create event:
```bash
python3 calendar_agent.py add-event --title "Codex follow-up" --start "2026-02-08 09:00" --end "2026-02-08 09:30" --notes "IMU viewer debug"
```

## Notes
- Datetime format: `YYYY-MM-DD HH:MM` (24-hour).
- If you get `Not authorized to send Apple events to Calendar`, grant permission in Privacy settings and rerun.
