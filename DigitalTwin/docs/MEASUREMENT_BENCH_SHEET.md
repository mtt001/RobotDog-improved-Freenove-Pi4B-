<!--
File: DigitalTwin/docs/MEASUREMENT_BENCH_SHEET.md
Version: v1.0 (2026-02-26 09:32)
Revision History:
- 2026-02-26 09:32 v1.0 - Added printable one-page bench sheet for first physical measurement session (Top-5 priority items #1 and #2 focus) with capture fields and sign-off checklist.
-->

# Digital Twin Measurement Bench Sheet (Printable)

Session goal:
- Capture highest-impact physical values first for model fidelity:
  - Geometry: `L1`, `L2`, hip offsets
  - Joint limits: `S11`, `S12`, `S13` hard-stop min/max

Date: __________  Time: __________  Operator: __________  Robot ID: __________

Tools checklist:
- [ ] Caliper / ruler
- [ ] Marker tape
- [ ] Phone camera (photo evidence)
- [ ] Flat hard table
- [ ] Power + neutral servo mode ready

## A) Geometry Capture (repeat 3x, average)

| Parameter | Trial 1 | Trial 2 | Trial 3 | Average | Unit | Confidence (0-100) | Notes |
|---|---:|---:|---:|---:|---|---:|---|
| `L1` (hip-pitch axis -> knee axis) |  |  |  |  | mm |  |  |
| `L2` (knee axis -> foot ref point) |  |  |  |  | mm |  |  |
| Hip offset `x` (body ref -> S11 pivot) |  |  |  |  | mm |  |  |
| Hip offset `y` (body ref -> S11 pivot) |  |  |  |  | mm |  |  |
| Hip offset `z` (body ref -> S11 pivot) |  |  |  |  | mm |  |  |

Photo refs:
- Geometry photo #1: __________
- Geometry photo #2: __________

## B) Joint Hard-Stop Limits (safe margin before contact)

| Joint | Min safe angle | Max safe angle | Unit | Confidence (0-100) | Notes |
|---|---:|---:|---|---:|---|
| `S11` hip roll |  |  | deg |  |  |
| `S12` hip pitch |  |  | deg |  |  |
| `S13` knee pitch |  |  | deg |  |  |

Photo refs:
- Limit photo #1: __________
- Limit photo #2: __________

## C) Immediate Sync + Verification

Sync checklist:
- [ ] Updated `DigitalTwin/resources/specs/robot_specs_template.json`
- [ ] Updated README measurement table row values and source to `MEASURED`
- [ ] Added notes for any remaining `ASSUMED` values

Quick verification commands:

```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase B
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase C
```

Verification result:
- Phase B: [ ] PASS  [ ] FAIL
- Phase C: [ ] PASS  [ ] FAIL

If FAIL:
- [ ] Re-check measurements with largest trial variance
- [ ] Re-test with prior baseline values to isolate culprit
- [ ] Record suspected parameter(s): ______________________

## D) Session Sign-off

- Completed by: __________
- Reviewed by: __________
- Next action: __________________________________________
