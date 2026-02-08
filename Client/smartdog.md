# smartdog Command Guide

## What is `smartdog`?

`smartdog` is a shell function that activates the Freenove Robot Dog client Python virtual environment and navigates to the Client directory in one command.

It is also available as an executable launcher script at:
- `/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/smartdog`
- symlinked to `/opt/homebrew/bin/smartdog`

---

## Usage

From **any directory**, simply type:

```bash
smartdog
```

Run a one-shot command inside the same venv/context:

```bash
smartdog python3 -V
smartdog python3 mtDogMain.py
```

### What You'll See

```
╔════════════════════════════════════════════════════════════╗
║         Freenove Robot Dog - Client Environment            ║
╚════════════════════════════════════════════════════════════╝

✓ Virtual environment activated: freenove-client
✓ Working directory: /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client

Available commands:
  • python mtDogMain.py          Launch robot dog client GUI
  • python mtDogBallTrack.py     Ball tracking calibration
  • python testHeadMoving.py     Test head servo movement

To exit the virtual environment, use:
  • deactivate                   Exit venv and return to system Python

((freenove-client) ) mengtatsai@MacBook-Pro Client %
```

Notice:
- ✅ **Directory changed** to `Client/`
- ✅ **Venv active** (shown by `((freenove-client))` in the prompt)
- ✅ **Quick reference** for common commands

---

## How It Works

The `smartdog` function is defined in your `~/.zshrc` file:

```bash
smartdog() {
    cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client
    source ~/.venvs/freenove-client/bin/activate
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         Freenove Robot Dog - Client Environment            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✓ Virtual environment activated: freenove-client"
    echo "✓ Working directory: $(pwd)"
    echo ""
    echo "Available commands:"
    echo "  • python mtDogMain.py          Launch robot dog client GUI"
    echo "  • python mtDogBallTrack.py     Ball tracking calibration"
    echo "  • python testHeadMoving.py     Test head servo movement"
    echo ""
    echo "To exit the virtual environment, use:"
    echo "  • deactivate                   Exit venv and return to system Python"
    echo ""
}
```

### What It Does (Step by Step)

1. **Changes Directory**: `cd` to the Client folder
2. **Activates Virtual Environment**: `source` activates the Python venv  
3. **Displays Welcome Banner**: Shows status and available commands
4. **Runs in Current Shell**: All changes persist in your current shell

---

## Running Your Scripts

Once activated, you can run Python scripts:

```bash
python mtDogMain.py           # Launch robot dog client GUI
python mtDogBallTrack.py      # Ball tracking calibration
python testHeadMoving.py      # Test head servo movement
```

---

## Deactivation

When done, use the `deactivate` command:

```bash
deactivate
```

Your prompt returns to normal (without venv indicator).

---

## Why It's a Shell Function (Not a Script)

**Why this approach works:**

| Approach | How it Works | Problem |
|----------|-------------|---------|
| Shell Script | Spawns new shell process | Directory changes don't persist |
| Shell Function | Runs in current shell | ✅ Changes persist naturally |

Since `smartdog` is a **shell function**, not a script file:
- It runs **in your current shell** without spawning subshells
- Directory and venv changes persist automatically
- Simpler and more reliable

---

## Troubleshooting

### Issue: `smartdog` command not found

**Solution**: Reload your shell configuration:
```bash
source ~/.zshrc
```

Or restart your terminal.

### Issue: Venv not activating (no `((freenove-client))` in prompt)

**Check**: Is the venv installed?
```bash
ls -la ~/.venvs/freenove-client/
```

If missing, create it:
```bash
python3 -m venv ~/.venvs/freenove-client
```

### Issue: Welcome banner not showing

Try reloading .zshrc:
```bash
source ~/.zshrc
```

Then run `smartdog` again.

---

## Quick Reference

| Task | Command |
|------|---------|
| Activate venv | `smartdog` |
| Deactivate venv | `deactivate` |
| Check current venv | `which python` |
| Check venv path | `echo $VIRTUAL_ENV` |
| List installed packages | `pip list` |
| Install new package | `pip install package_name` |

---

## Related Files

- **Shell config**: `~/.zshrc` (defines smartdog function)
- **Virtual environment**: `~/.venvs/freenove-client/` (venv directory)
- **Client code**: `mtDogMain.py` (main application)
- **Ball tracking**: `mtDogBallTrack.py` (calibration + tracking)
- **Head servo test**: `testHeadMoving.py` (servo movement test)

---

## Author Notes

- Created: 2025-12-30
- Updated: 2025-12-30 (Added professional welcome banner)
- Version: 1.1
- Maintainer: MT (User) with GitHub Copilot assistance
- Status: Production ready


