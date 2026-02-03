# Environment Setup

## Recommended Python Version
- Python 3.9 (arm64 on Apple Silicon).

## Virtual Environment (venv)
1. Create venv:
   - `python3 -m venv .venv`
2. Activate venv:
   - `source .venv/bin/activate`
3. Install dependencies:
   - `pip install -r requirements.txt`

## Apple Silicon (arm64) Notes
- Use an arm64 Python interpreter to avoid binary wheel mismatches.
- Avoid mixing x86_64 Python with arm64 wheels (or vice versa).

## Known Issues
- **PyQt5 x86_64 vs arm64 mismatch**
  - If PyQt5 is installed for the wrong architecture, import may fail with an incompatible binary error.
- **OpenCV + NumPy dependency sensitivity**
  - Import errors can occur if NumPy is missing or if the installed wheel is for the wrong architecture.

## Important
- Import errors are environment-related, not code defects.
