#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/p1_calibration_update.py
Version: v1.1 (2026-02-28 12:33)
Revision History:
- 2026-02-28 12:33 v1.1 - Relocated to `Code/DigitalTwin/scripts/`; removed `Test/` from path builder.
- 2026-02-26 10:50 v1.0 - Added P1 calibration updater to sync neutral offsets and IMU mount/bias across JSON+CSV with optional Phase C/D live verification.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update P1 calibration values (neutral offsets + IMU) in DigitalTwin specs and log, then optionally verify."
    )
    parser.add_argument("--code-root", default="/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code")
    parser.add_argument("--date", default="2026-02-26")
    parser.add_argument("--owner", default="user")

    parser.add_argument("--neutral-s11", type=float, required=True)
    parser.add_argument("--neutral-s12", type=float, required=True)
    parser.add_argument("--neutral-s13", type=float, required=True)
    parser.add_argument("--neutral-source", choices=["MEASURED", "ASSUMED"], default="MEASURED")
    parser.add_argument("--neutral-confidence", type=int, default=80)
    parser.add_argument("--neutral-notes", default="neutral offsets from measured assembly alignment")

    parser.add_argument("--imu-mount-roll", type=float, required=True)
    parser.add_argument("--imu-mount-pitch", type=float, required=True)
    parser.add_argument("--imu-mount-yaw", type=float, required=True)
    parser.add_argument("--imu-bias-roll", type=float, required=True)
    parser.add_argument("--imu-bias-pitch", type=float, required=True)
    parser.add_argument("--imu-bias-yaw", type=float, required=True)
    parser.add_argument("--imu-source", choices=["MEASURED", "ASSUMED"], default="MEASURED")
    parser.add_argument("--imu-confidence", type=int, default=80)
    parser.add_argument("--imu-notes", default="IMU mount+bias from flat table calibration session")

    parser.add_argument("--apply", action="store_true", help="Write changes to JSON/CSV. Without this flag, performs dry-run only.")
    parser.add_argument("--verify", action="store_true", help="Run phase C and D verification after apply.")
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


def _repo_paths(code_root: Path) -> tuple[Path, Path, Path]:
    base = code_root / "DigitalTwin"
    return (
        base / "resources" / "specs" / "robot_specs_template.json",
        base / "resources" / "specs" / "measurement_log_template.csv",
        base / "scripts" / "run_phase_verification.py",
    )


def _update_csv_row(rows: list[dict[str, str]], phase: str, parameter: str, value: Any, unit: str, source: str, confidence: int, date_str: str, owner: str, notes: str) -> None:
    value_str = f"{value:.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    for row in rows:
        if row.get("phase") == phase and row.get("parameter") == parameter:
            row.update(
                {
                    "value": value_str,
                    "unit": unit,
                    "source": source,
                    "confidence": str(confidence),
                    "date": date_str,
                    "owner": owner,
                    "notes": notes,
                }
            )
            return
    rows.append(
        {
            "phase": phase,
            "parameter": parameter,
            "value": value_str,
            "unit": unit,
            "source": source,
            "confidence": str(confidence),
            "date": date_str,
            "owner": owner,
            "notes": notes,
        }
    )


def run_verify(code_root: Path, runner: Path, headless: bool) -> int:
    head = ["--headless"] if headless else []
    cmds = [
        [sys.executable, str(runner), *head, "--only-phase", "C"],
        [sys.executable, str(runner), *head, "--only-phase", "D"],
    ]
    for cmd in cmds:
        print("VERIFY:", " ".join(cmd))
        rc = subprocess.call(cmd, cwd=str(code_root))
        if rc != 0:
            return rc
    return 0


def main() -> int:
    args = parse_args()
    code_root = Path(args.code_root).resolve()
    json_path, csv_path, phase_runner = _repo_paths(code_root)

    if not json_path.exists() or not csv_path.exists() or not phase_runner.exists():
        print("ERROR: required DigitalTwin files not found.")
        print(f"- json: {json_path}")
        print(f"- csv:  {csv_path}")
        print(f"- run:  {phase_runner}")
        return 2

    data = json.loads(json_path.read_text(encoding="utf-8"))
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or ["phase", "parameter", "value", "unit", "source", "confidence", "date", "owner", "notes"])

    # JSON updates
    neutral = data.setdefault("neutral_offsets_assumed", {})
    neutral["S11_offset_from_90_deg"] = float(args.neutral_s11)
    neutral["S12_offset_from_90_deg"] = float(args.neutral_s12)
    neutral["S13_offset_from_90_deg"] = float(args.neutral_s13)
    neutral["source"] = f"{args.owner}_{args.neutral_source.lower()}_{args.date}"
    neutral["confidence"] = int(args.neutral_confidence)
    neutral["notes"] = str(args.neutral_notes)

    imu = data.setdefault("imu_mount_assumed", {})
    imu["frame"] = "FLU"
    imu["roll_offset_deg"] = float(args.imu_mount_roll)
    imu["pitch_offset_deg"] = float(args.imu_mount_pitch)
    imu["yaw_offset_deg"] = float(args.imu_mount_yaw)

    imu_conf = data.setdefault("imu_assumption_confidence", {})
    imu_conf["mount_orientation_confidence"] = int(args.imu_confidence)
    imu_conf["static_bias_confidence"] = int(args.imu_confidence)
    imu_conf["notes"] = str(args.imu_notes)

    prov = data.setdefault("provenance", {})
    prov["last_updated"] = "2026-02-26 10:50 CST"

    # CSV updates
    _update_csv_row(rows, "C", "S11_neutral_offset_from_90", args.neutral_s11, "deg", args.neutral_source, args.neutral_confidence, args.date, args.owner, args.neutral_notes)
    _update_csv_row(rows, "C", "S12_neutral_offset_from_90", args.neutral_s12, "deg", args.neutral_source, args.neutral_confidence, args.date, args.owner, args.neutral_notes)
    _update_csv_row(rows, "C", "S13_neutral_offset_from_90", args.neutral_s13, "deg", args.neutral_source, args.neutral_confidence, args.date, args.owner, args.neutral_notes)

    _update_csv_row(rows, "D", "imu_mount_roll", args.imu_mount_roll, "deg", args.imu_source, args.imu_confidence, args.date, args.owner, args.imu_notes)
    _update_csv_row(rows, "D", "imu_mount_pitch", args.imu_mount_pitch, "deg", args.imu_source, args.imu_confidence, args.date, args.owner, args.imu_notes)
    _update_csv_row(rows, "D", "imu_mount_yaw", args.imu_mount_yaw, "deg", args.imu_source, args.imu_confidence, args.date, args.owner, args.imu_notes)
    _update_csv_row(rows, "D", "imu_bias_roll", args.imu_bias_roll, "deg", args.imu_source, args.imu_confidence, args.date, args.owner, args.imu_notes)
    _update_csv_row(rows, "D", "imu_bias_pitch", args.imu_bias_pitch, "deg", args.imu_source, args.imu_confidence, args.date, args.owner, args.imu_notes)
    _update_csv_row(rows, "D", "imu_bias_yaw", args.imu_bias_yaw, "deg", args.imu_source, args.imu_confidence, args.date, args.owner, args.imu_notes)

    print("P1 Calibration Update Preview")
    print(f"- JSON: {json_path}")
    print(f"- CSV:  {csv_path}")
    print(f"- neutral: S11={args.neutral_s11}, S12={args.neutral_s12}, S13={args.neutral_s13} ({args.neutral_source}, conf={args.neutral_confidence})")
    print(f"- imu_mount: roll={args.imu_mount_roll}, pitch={args.imu_mount_pitch}, yaw={args.imu_mount_yaw} ({args.imu_source}, conf={args.imu_confidence})")
    print(f"- imu_bias:  roll={args.imu_bias_roll}, pitch={args.imu_bias_pitch}, yaw={args.imu_bias_yaw} ({args.imu_source}, conf={args.imu_confidence})")

    if not args.apply:
        print("DRY-RUN: no files written")
        return 0

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("APPLY: JSON/CSV updated")

    if args.verify:
        rc = run_verify(code_root, phase_runner, args.headless)
        print("VERIFY RESULT:", "PASS" if rc == 0 else f"FAIL (rc={rc})")
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
