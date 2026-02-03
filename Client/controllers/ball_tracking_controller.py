#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : ball_tracking_controller.py
 Author : MT & GitHub Copilot

 Description:
     Ball tracking helpers extracted from mtDogMain.py (CameraWindow).
     Handles tracking transitions, full/body control, lost-ball search,
     and close-enough completion/barking logic.

 v1.00  (2026-01-31 22:25)    : Initial ball tracking controller extraction
     • Move tracking helpers + close-enough/bark logic into controller.
===============================================================================
"""

from __future__ import annotations

import threading
import time

from PyQt5.QtCore import QTimer

from mtDogBallTrack import TRACKING_MODE_FULL, TRACKING_MODE_BODY


class BallTrackingController:
    def __init__(self, host):
        self._host = host

        # Track tracking-mode transitions (e.g., to center head when switching modes)
        host._last_tracking_mode = getattr(host.ball_tracker, "tracking_mode", None)

        host.last_dog_frame_height = 0      # updated when Dog frame arrives
        host.body_tracking_interval = 0.6   # seconds between body tracking commands
        host.last_body_cmd_time = 0.0

        # Body tracking policy: by default, do not command backward motion.
        # (Backward can be surprising when the ball jitters above center while turning.)
        host.body_allow_backward = False

        # Body tracking hysteresis state (reduces left/right oscillation near center)
        host._body_hyst_axis = None  # 'x' | 'y' | None
        host._body_hyst_dir = 0      # -1 or +1

        # Lost-ball search + obstacle avoidance state
        host._lost_search_state = "idle"   # 'idle' | 'forward' | 'scan' | 'escape'
        host._lost_search_last_cmd_ts = 0.0
        host._lost_search_sent_stop = False
        host._lost_search_phase = "scan"   # 'scan' | 'forward'
        host._lost_search_phase_start_ts = 0.0

        # FULL mode head lock (stabilize SONIC ranging): keep head at neutral and skip head tracking.
        host.full_lock_head_in_full = True
        host._full_head_last_sent_ts = 0.0
        host._full_head_sent_once = False

        # FULL-mode close-enough completion sequence
        host._close_enough_latched = False
        host._close_enough_seq_state = "idle"  # 'idle' | 'triggered' | 'relax' | 'off'
        host._close_enough_seq_ts = 0.0
        host._close_enough_off_timer = None

        # FULL close-enough latch reset + STOP spam guard
        host._close_enough_last_stop_ts = 0.0
        host._close_enough_stop_min_interval_s = 0.8
        host._close_enough_clear_below_ratio = 0.6  # hysteresis: clear latch when diam < (w/4)*ratio
        host._close_enough_clear_hold_s = 0.6
        host._close_enough_clear_start_ts = 0.0

        # Ball tracking status (for Color window overlay)
        host._ball_close_enough = False
        host._ball_locked = False
        host._ball_lock_source = ""
        host._body_cmd_name = ""

        # Post-completion "barking" (beep + yellow flash) + Mask cheer message
        host._bark_timer = QTimer()
        host._bark_timer.timeout.connect(self.bark_tick)
        host._bark_active = False
        host._bark_pending_start = False
        host._bark_interval_ms = 2000
        host._cheer_text = ""
        host._cheer_visible = False
        host._cheer_pending_apply = False

    def start_barking(self):
        host = self._host
        if host._bark_active:
            return
        host._bark_active = True
        try:
            host._bark_timer.start(int(host._bark_interval_ms))
        except Exception:
            host._bark_active = False

    def stop_barking(self):
        host = self._host
        host._bark_active = False
        try:
            if host._bark_timer.isActive():
                host._bark_timer.stop()
        except Exception:
            pass

    def bark_tick(self):
        host = self._host
        # Auto-stop barking if the completion conditions are no longer true.
        if not self.bark_should_run():
            self.stop_barking()
            # Hide the cheer banner as well to avoid confusing state.
            host._set_mask_cheer("", visible=False)
            return

        # Only bark when in Dog mode with a control link.
        if (
            not host.use_dog_video
            or host.dog_client is None
            or not getattr(host.dog_client, "tcp_flag", False)
            or not getattr(host, "server_control_ok", False)
        ):
            return
        # Single beep + yellow flash
        try:
            host._beep_pattern(beeps=1, on_s=0.10, off_s=0.00)
        except Exception:
            pass

    def bark_should_run(self) -> bool:
        host = self._host
        """Barking should only run after FULL completion reaches OFF and we still have a ball lock."""
        try:
            mode = getattr(host.ball_tracker, "tracking_mode", None)
        except Exception:
            mode = None
        try:
            missed = int(getattr(host.ball_tracker, "missed_frames", 0) or 0)
        except Exception:
            missed = 0

        return bool(
            host.ball_mode_enabled
            and host.use_dog_video
            and host.dog_client is not None
            and getattr(host.dog_client, "tcp_flag", False)
            and getattr(host, "server_control_ok", False)
            and mode == TRACKING_MODE_FULL
            and bool(getattr(host, "_close_enough_latched", False))
            and str(getattr(host, "_close_enough_seq_state", "")) == "off"
            and missed == 0
        )

    def trigger_close_enough_sequence(self, *, ball_diameter: float | None, frame_w: float):
        host = self._host
        """One-shot completion: double beep + double green flash, then STOP+RELAX, then OFF after 5s."""
        if host._close_enough_latched:
            return
        if (
            not host.use_dog_video
            or host.dog_client is None
            or not getattr(host.dog_client, "tcp_flag", False)
            or not getattr(host, "server_control_ok", False)
        ):
            return

        host._close_enough_latched = True
        host._close_enough_seq_state = "triggered"
        host._close_enough_seq_ts = time.time()

        # Audible + visible cue
        try:
            host._beep_pattern(beeps=2, on_s=0.12, off_s=0.12)
            host._led_flash(flashes=2, on_s=0.18, off_s=0.18, color=(0, 255, 0))
        except Exception:
            pass

        # Immediately stop and relax
        try:
            host.send_stop_motion()
        except Exception:
            pass
        try:
            host._send_relax_only()
            host._close_enough_seq_state = "relax"
        except Exception:
            pass

        # Cancel any previous pending OFF to avoid stacking timers.
        prev = getattr(host, "_close_enough_off_timer", None)
        try:
            if prev is not None and prev.is_alive():
                prev.cancel()
        except Exception:
            pass

        def _do_off():
            host._send_stop_pwm_only()
            host._close_enough_seq_state = "off"
            host._close_enough_seq_ts = time.time()
            # After OFF, start barking and show a cheer message in Mask window.
            if host.ball_mode_enabled:
                host._bark_pending_start = True
                host._set_mask_cheer(
                    "Ball located! FULL complete → STOP, RELAX, OFF.\n"
                    "Barking: 1 beep + yellow flash every 2s. Click Clear to stop.",
                    visible=True,
                )

        host._close_enough_off_timer = threading.Timer(5.0, _do_off)
        host._close_enough_off_timer.daemon = True
        host._close_enough_off_timer.start()
        try:
            print(
                f"[FULL] Close enough -> cue+STOP+RELAX then OFF in 5s "
                f"(diam={ball_diameter if ball_diameter is not None else 'NA'} thr={frame_w/4.0:.1f})"
            )
        except Exception:
            pass

    def handle_tracking_mode_transition(self, mode):
        host = self._host
        if mode == host._last_tracking_mode:
            return

        host._last_tracking_mode = mode

        # Reset FULL head-lock one-shot when leaving/entering FULL mode.
        try:
            if mode != TRACKING_MODE_FULL:
                host._full_head_sent_once = False
        except Exception:
            pass

        # When switching into BODY tracking, keep the head neutral (90 deg).
        if mode == TRACKING_MODE_BODY:
            try:
                host.head_tracker.reset()
                neutral = int(round(getattr(host.head_tracker.cfg, "neutral_deg", 90)))
            except Exception:
                neutral = 90

            if (
                host.use_dog_video
                and host.dog_client is not None
                and getattr(host.dog_client, "tcp_flag", False)
            ):
                host.send_head_angle(neutral)

        if mode == TRACKING_MODE_FULL:
            try:
                host._full_head_sent_once = False
            except Exception:
                pass

    def update_full_body_tracking(self, ball_center, frame_shape):
        host = self._host
        if host.ball_tracker.tracking_mode not in (TRACKING_MODE_FULL, TRACKING_MODE_BODY):
            return
        if ball_center is None or frame_shape is None:
            return
        # Pull tuning from BallTracker (updated by mask window sliders)
        try:
            host.body_tracking_interval = float(
                getattr(host.ball_tracker, "body_tracking_interval", host.body_tracking_interval)
            )
        except Exception:
            pass
        interval = max(0.05, min(5.0, float(host.body_tracking_interval)))

        try:
            deadzone_ratio = float(getattr(host.ball_tracker, "body_deadzone_ratio", 0.18))
        except Exception:
            deadzone_ratio = 0.18
        deadzone_ratio = max(0.05, min(0.50, deadzone_ratio))

        h = frame_shape[0]
        w = frame_shape[1] if len(frame_shape) > 1 else 0
        if h == 0 or w == 0:
            return

        now = time.time()

        center_x = w / 2.0
        center_y = h / 2.0
        x_off = ball_center[0] - center_x   # positive = ball is RIGHT of center
        y_off = ball_center[1] - center_y   # positive = ball is BELOW center

        # FULL tracking: forward-approach policy based on apparent ball size.
        # Keep moving toward the ball until its diameter exceeds 1/4 of screen width.
        # (When close enough, stop forward motion even if Y offset still suggests moving.)
        full_mode = host.ball_tracker.tracking_mode == TRACKING_MODE_FULL
        ball_radius = getattr(host.ball_tracker, "last_radius", None)
        try:
            ball_diameter = float(ball_radius) * 2.0 if ball_radius is not None else None
        except Exception:
            ball_diameter = None
        thr_hi = (w / 4.0) if w > 0 else 0.0
        try:
            clear_ratio = float(getattr(host.ball_tracker, "full_close_enough_clear_below_ratio", host._close_enough_clear_below_ratio))
        except Exception:
            clear_ratio = float(getattr(host, "_close_enough_clear_below_ratio", 0.85))
        clear_ratio = max(0.20, min(0.99, clear_ratio))
        thr_lo = thr_hi * clear_ratio

        # Extra "close enough" confirmation:
        # If the ball's bottom edge reaches the bottom of the frame, consider it close enough.
        # This covers cases where the ball is still small but physically very near.
        bottom_margin_px = 2.0
        try:
            bottom_edge_reached = bool(
                full_mode
                and ball_radius is not None
                and float(ball_center[1]) + float(ball_radius) >= (float(h) - bottom_margin_px)
            )
        except Exception:
            bottom_edge_reached = False

        close_enough_by_size = bool(full_mode and ball_diameter is not None and thr_hi > 0 and ball_diameter >= thr_hi)
        close_enough_hi = bool(close_enough_by_size or bottom_edge_reached)

        # Latch auto-clear uses hysteresis on size, but also requires the ball is no longer
        # touching the bottom edge.
        close_enough_lo = bool(
            full_mode
            and ball_diameter is not None
            and thr_lo > 0
            and ball_diameter < thr_lo
            and (not bottom_edge_reached)
        )
        close_enough = close_enough_hi

        # Publish for status overlay
        try:
            latched = bool(getattr(host, "_close_enough_latched", False)) if full_mode else False
            host._ball_close_enough = bool(close_enough_hi or latched)
        except Exception:
            pass

        # FULL-mode completion sequence when close enough.
        if full_mode and close_enough_hi:
            self.trigger_close_enough_sequence(ball_diameter=ball_diameter, frame_w=float(w))

        # If we've already completed/started the close-enough sequence, do not send further motion.
        # However, auto-clear the latch (with hysteresis + hold time) once the ball is no longer close.
        if full_mode and host._close_enough_latched:
            seq = str(getattr(host, "_close_enough_seq_state", "idle"))
            can_auto_clear = seq in ("off", "idle")

            # Hysteresis-based auto-reset to resolve the "unexpected Stop" latch.
            # Only allow clearing after the completion sequence reaches OFF/IDLE.
            if can_auto_clear and close_enough_lo:
                if float(getattr(host, "_close_enough_clear_start_ts", 0.0) or 0.0) <= 0.0:
                    host._close_enough_clear_start_ts = now
                hold_s = float(getattr(host, "_close_enough_clear_hold_s", 0.6) or 0.6)
                hold_s = max(0.0, min(5.0, hold_s))
                if (now - float(host._close_enough_clear_start_ts)) >= hold_s:
                    host._close_enough_latched = False
                    host._close_enough_clear_start_ts = 0.0
                    # Resume normal tracking immediately.
                    # (Do not send STOP here; the controller below will decide.)
                else:
                    pass
            else:
                host._close_enough_clear_start_ts = 0.0

            if host._close_enough_latched:
                # While the completion sequence is still in progress, keep the robot safe by
                # occasionally re-sending STOP (rate-limited). Once OFF (stop_pwm) is reached,
                # do not send STOP anymore and show cmd:Off in the HUD.
                show_cmd = "Stop"
                if seq == "off":
                    show_cmd = "Off"
                elif seq == "relax":
                    show_cmd = "Relax"

                if seq in ("triggered", "relax"):
                    try:
                        min_dt = float(getattr(host, "_close_enough_stop_min_interval_s", 0.8) or 0.8)
                    except Exception:
                        min_dt = 0.8
                    min_dt = max(0.2, min(5.0, min_dt))
                    if (now - float(getattr(host, "_close_enough_last_stop_ts", 0.0))) >= min_dt:
                        try:
                            host.send_stop_motion()
                        except Exception:
                            pass
                        host._close_enough_last_stop_ts = now

                try:
                    t0 = float(getattr(host, "_close_enough_seq_ts", 0.0) or 0.0)
                    dt = max(0.0, time.time() - t0) if t0 > 0 else 0.0
                    lines = [
                        f"TRACK:full axis:- cmd:{show_cmd}",
                        "GOAL:close_enough → completion (latched)",
                        f"SEQ:{seq} +{dt:.1f}s  reset:diam<thr_lo for {float(getattr(host, '_close_enough_clear_hold_s', 0.6) or 0.6):.1f}s",
                    ]
                    if seq == "off":
                        lines.insert(2, "POWER:off (stop_pwm)")
                    elif seq == "relax":
                        lines.insert(2, "SERVOS:relax (waiting for off)")
                    if ball_diameter is not None:
                        lines.append(
                            f"diam:{ball_diameter:.0f} thr_hi:{thr_hi:.0f} thr_lo:{thr_lo:.0f} bottom:{int(bool(bottom_edge_reached))} close:{int(bool(close_enough_hi))}"
                        )
                    host.ball_tracker.body_debug_lines = lines
                except Exception:
                    pass
                return
            try:
                host.send_stop_motion()
            except Exception:
                pass
            try:
                seq = str(getattr(host, "_close_enough_seq_state", "idle"))
                t0 = float(getattr(host, "_close_enough_seq_ts", 0.0) or 0.0)
                dt = max(0.0, time.time() - t0) if t0 > 0 else 0.0
                lines = [
                    "TRACK:full axis:- cmd:Stop",
                    f"GOAL:close_enough → Stop, Relax, Off (5s)",
                    f"SEQ:{seq} +{dt:.1f}s",
                ]
                if ball_diameter is not None:
                    lines.append(f"diam:{ball_diameter:.0f} thr:{(w/4.0):.0f} close:1")
                host.ball_tracker.body_debug_lines = lines
            except Exception:
                pass
            return

        try:
            body_kp = float(getattr(host.ball_tracker, "body_kp", 0.0))
        except Exception:
            body_kp = 0.0
        body_kp = max(0.0, min(5.0, body_kp))

        x_ctl = x_off
        y_ctl = y_off

        def _kp_speed(error_ctl: float, dead: float, span: float) -> int | None:
            """Map error magnitude to a motion speed (2..10) using Body-Kp.

            If body_kp==0, return None to keep the existing fixed-speed behavior.
            """
            if body_kp <= 0.0:
                return None
            mag = max(0.0, abs(float(error_ctl)) - float(dead))
            if mag <= 0.0:
                return None
            frac = mag / max(1.0, float(span))
            frac = max(0.0, min(1.0, frac))
            eff = max(0.0, min(1.0, body_kp * frac))
            min_speed = 2
            max_speed = 10
            return int(round(min_speed + (max_speed - min_speed) * eff))

        # Deadzone (tunable)
        x_dead = max(20.0, w * deadzone_ratio)
        y_dead = max(20.0, h * deadzone_ratio)

        # Hysteresis: enter further out, exit further in
        x_margin = max(8.0, x_dead * 0.25)
        y_margin = max(8.0, y_dead * 0.25)
        x_enter = x_dead + x_margin
        x_exit = max(0.0, x_dead - x_margin)
        y_enter = y_dead + y_margin
        y_exit = max(0.0, y_dead - y_margin)

        # Policy: do not move forward/back unless X is centered within tolerance.
        # Use the X deadzone as the centering tolerance.
        x_centered = abs(x_off) <= x_dead

        # Policy: in body tracking, optionally disallow backward motion.
        # Prefer the BallTracker setting (tunable/persisted via mask window).
        allow_backward = bool(
            getattr(
                host.ball_tracker,
                "body_allow_backward",
                getattr(host, "body_allow_backward", False),
            )
        )

        def sign_dir(v: float) -> int:
            return -1 if v < 0 else 1

        axis = host._body_hyst_axis
        direction = int(host._body_hyst_dir)
        command = None
        speed_override = None
        send_stop = False

        axis_before = axis

        if axis == "x":
            if abs(x_ctl) < x_exit:
                axis = None
                direction = 0
                send_stop = True
            else:
                new_dir = sign_dir(x_ctl)
                if new_dir != direction and abs(x_ctl) > x_enter:
                    direction = new_dir
                command = "w" if direction < 0 else "r"
                speed_override = _kp_speed(x_ctl, x_dead, (w / 2.0) - x_dead)
        elif axis == "y":
            # If X drifts out of tolerance, immediately switch to turn-to-center.
            if not x_centered:
                axis = "x"
                direction = sign_dir(x_ctl)
                command = "w" if direction < 0 else "r"

            if full_mode:
                # FULL mode: ignore Y-offset for approach; use ball size to decide forward/stop.
                if close_enough:
                    axis = None
                    direction = 0
                    send_stop = True
                else:
                    direction = 1
                    if x_centered:
                        command = "e"  # forward toward ball
                        # Speed based on how far we are from the size threshold.
                        if ball_diameter is not None:
                            approach_err = max(0.0, (w / 4.0) - ball_diameter)
                            speed_override = _kp_speed(approach_err, 0.0, (w / 4.0))
                    else:
                        command = None
            else:
                # BODY mode: original Y-offset based forward/back behavior.
                # Forward-only Y control when backward is disabled.
                if (not allow_backward) and (y_ctl < -y_enter):
                    axis = None
                    direction = 0
                    send_stop = True
                elif abs(y_ctl) < y_exit:
                    axis = None
                    direction = 0
                    send_stop = True
                else:
                    new_dir = sign_dir(y_ctl)
                    if new_dir != direction and abs(y_ctl) > y_enter:
                        direction = new_dir
                    # Only allow forward/back when X is centered.
                    if x_centered:
                        if allow_backward:
                            command = "c" if direction < 0 else "e"
                        else:
                            command = "e" if direction > 0 else None
                    else:
                        command = None
                    if command is not None:
                        speed_override = _kp_speed(y_ctl, y_dead, (h / 2.0) - y_dead)
        else:
            # Prefer X corrections (turn) over Y (forward/back)
            # Turn whenever X is outside the deadzone tolerance.
            if not x_centered:
                axis = "x"
                direction = sign_dir(x_ctl)
                command = "w" if direction < 0 else "r"
                speed_override = _kp_speed(x_ctl, x_dead, (w / 2.0) - x_dead)
            elif full_mode:
                # FULL mode: if centered and not close enough, keep approaching.
                if x_centered and not close_enough:
                    axis = "y"
                    direction = 1
                    command = "e"
                    if ball_diameter is not None:
                        approach_err = max(0.0, (w / 4.0) - ball_diameter)
                        speed_override = _kp_speed(approach_err, 0.0, (w / 4.0))
                else:
                    axis = None
                    direction = 0
                    send_stop = True
            elif (abs(y_ctl) > y_enter) if allow_backward else (y_ctl > y_enter):
                axis = "y"
                direction = sign_dir(y_ctl)
                # Only enter Y axis if X is centered.
                if x_centered:
                    if allow_backward:
                        command = "c" if direction < 0 else "e"
                    else:
                        command = "e" if direction > 0 else None
                else:
                    axis = "x"
                    direction = sign_dir(x_ctl)
                    command = "w" if direction < 0 else "r"
                if command is not None:
                    speed_override = _kp_speed(y_ctl, y_dead, (h / 2.0) - y_dead)

        host._body_hyst_axis = axis
        host._body_hyst_dir = direction

        # ---- Debug lines for Mask window ----
        # Stored on BallTracker (shared with BallMaskWindow) so you can see live
        # body decisions without reading the terminal.
        try:
            cmd_dbg = host._cmd_key_to_human(command, send_stop=bool(send_stop))
            mode_dbg = "full" if full_mode else "body"
            lines = [
                f"TRACK:{mode_dbg} axis:{axis or '-'} cmd:{cmd_dbg}",
                f"off=({x_off:+.0f},{y_off:+.0f}) dead=({x_dead:.0f},{y_dead:.0f})",
            ]
            if full_mode:
                if ball_diameter is not None:
                    lines.append(
                        f"diam:{ball_diameter:.0f} thr_hi:{thr_hi:.0f} thr_lo:{thr_lo:.0f} close:{int(bool(close_enough_hi))}"
                    )
                else:
                    lines.append(
                        f"diam:-- thr_hi:{thr_hi:.0f} thr_lo:{thr_lo:.0f} close:{int(bool(close_enough_hi))}"
                    )
            else:
                spd_dbg = speed_override if speed_override is not None else int(getattr(host, "move_speed", 8))
                lines.append(f"kp:{body_kp:.2f} spd:{int(spd_dbg)} x_ok:{int(bool(x_centered))}")
            host.ball_tracker.body_debug_lines = lines
        except Exception:
            pass

        axis_changed = axis_before != axis

        if send_stop:
            # Stop immediately once we re-enter the inner band.
            host.send_stop_motion()
            host.last_body_cmd_time = now
            try:
                host._body_cmd_name = ""
            except Exception:
                pass
            return

        # If we just switched axes (e.g., from Y to X), allow an immediate corrective command.
        can_send = axis_changed or ((now - host.last_body_cmd_time) >= interval)

        if command and can_send:
            print(
                f"[BODY] mode={host.ball_tracker.tracking_mode} axis={axis} cmd={command} "
                f"x_off={x_off:+.0f} y_off={y_off:+.0f} "
                f"kp={body_kp:.2f} "
                f"dead=({x_dead:.0f},{y_dead:.0f})"
            )
            host.send_motion_command(command, speed_override=speed_override)
            host.last_body_cmd_time = now
            try:
                host._body_cmd_name = host._cmd_key_to_human(command)
            except Exception:
                pass
        elif can_send and not command:
            try:
                host._body_cmd_name = ""
            except Exception:
                pass

    def update_lost_ball_search(self, frame_shape):
        """When ball is lost, search by moving forward; avoid obstacles via SONIC.

        Policy:
          - If range <= near_cm: turn-left until range > clear_cm.
          - Otherwise: move forward slowly to search.
          - If telemetry (sonic) is stale: stop for safety.
        """
        host = self._host
        t = host.ball_tracker
        if not (getattr(t, "search_forward_enabled", True) or getattr(t, "obstacle_avoid_enabled", True)):
            return

        # If FULL-mode completion sequence is active, do not keep searching.
        if bool(getattr(host, "_close_enough_latched", False)):
            return

        now = time.time()
        interval = float(getattr(t, "body_tracking_interval", 0.6))
        interval = max(0.20, min(2.00, interval))
        if (now - float(getattr(host, "_lost_search_last_cmd_ts", 0.0))) < interval:
            return

        # Require recent telemetry for obstacle logic; otherwise stop.
        telemetry_ok = bool(getattr(host, "telemetry_valid", False)) and (
            (now - float(getattr(host, "last_telemetry_ok_time", 0.0))) <= 2.0
        )
        if not telemetry_ok:
            if host._lost_search_state != "idle" or not host._lost_search_sent_stop:
                host.send_stop_motion()
                host._lost_search_sent_stop = True
            host._lost_search_state = "idle"
            try:
                host.ball_tracker.body_debug_lines = [
                    "SEARCH:idle (telemetry stale)",
                    f"missed:{int(getattr(t, 'missed_frames', 0))}",
                ]
            except Exception:
                pass
            host._lost_search_last_cmd_ts = now
            return

        dist = float(getattr(host, "distance_cm", 9999.0) or 9999.0)
        near_cm = float(getattr(t, "obstacle_near_cm", 10.0) or 10.0)
        clear_cm = float(getattr(t, "obstacle_clear_cm", 30.0) or 30.0)
        if clear_cm < near_cm:
            clear_cm = near_cm

        search_forward_enabled = bool(getattr(t, "search_forward_enabled", True))
        obstacle_avoid_enabled = bool(getattr(t, "obstacle_avoid_enabled", True))

        # If both toggles are off, treat as feature disabled.
        if (not search_forward_enabled) and (not obstacle_avoid_enabled):
            if not host._lost_search_sent_stop:
                host.send_stop_motion()
                host._lost_search_sent_stop = True
            host._lost_search_state = "idle"
            host._lost_search_phase = "scan"
            host._lost_search_phase_start_ts = 0.0
            try:
                host.ball_tracker.body_debug_lines = [
                    "SEARCH:off",
                    f"dist:{dist:.1f}cm near:{near_cm:.0f} clear:{clear_cm:.0f}",
                    f"missed:{int(getattr(t, 'missed_frames', 0))}",
                ]
            except Exception:
                pass
            host._lost_search_last_cmd_ts = now
            return

        want_escape = obstacle_avoid_enabled and (dist <= near_cm)

        # Search policy:
        # - If forward enabled: run a simple repeating pattern: scan-left 2s, forward 1s.
        # - If forward disabled: keep scanning (turn-left) only.
        preferred_state = "pattern" if search_forward_enabled else "scan"
        state = str(getattr(host, "_lost_search_state", "idle"))
        if state == "escape":
            if dist > clear_cm:
                state = preferred_state
                host.send_stop_motion()
                host._lost_search_sent_stop = True
                # After escaping, restart the search pattern from scan.
                host._lost_search_phase = "scan"
                host._lost_search_phase_start_ts = now
        else:
            state = "escape" if want_escape else preferred_state
            if state == "escape":
                host.send_stop_motion()
                host._lost_search_sent_stop = True
                # Pause/restart pattern timing while escaping.
                host._lost_search_phase = "scan"
                host._lost_search_phase_start_ts = now

        host._lost_search_state = state

        cmd = None
        speed_override = None
        if state == "escape":
            cmd = "w"  # always turn-left for escape
            speed_override = int(getattr(t, "obstacle_turn_speed", 4) or 4)
        elif state == "pattern":
            scan_s = 2.0
            forward_s = 1.0
            if float(getattr(host, "_lost_search_phase_start_ts", 0.0)) <= 0.0:
                host._lost_search_phase_start_ts = now
                host._lost_search_phase = "scan"

            phase = str(getattr(host, "_lost_search_phase", "scan"))
            phase_elapsed = max(0.0, now - float(getattr(host, "_lost_search_phase_start_ts", now)))
            phase_dur = scan_s if phase == "scan" else forward_s
            phase_switched = False
            if phase_elapsed >= phase_dur:
                phase = "forward" if phase == "scan" else "scan"
                host._lost_search_phase = phase
                host._lost_search_phase_start_ts = now
                phase_elapsed = 0.0
                phase_dur = scan_s if phase == "scan" else forward_s
                phase_switched = True

            if phase == "forward":
                cmd = "e"
                speed_override = int(getattr(t, "search_forward_speed", 4) or 4)
            else:
                cmd = "w"
                speed_override = int(getattr(t, "obstacle_turn_speed", 4) or 4)

            # If we just switched phase, send immediately (don’t wait for the interval gate).
            if phase_switched:
                host._lost_search_last_cmd_ts = 0.0

            # Export pattern info for UI
            pattern_line = f"PATTERN:{phase} {phase_elapsed:.1f}/{phase_dur:.1f}s (scan=2.0 fwd=1.0)"
        elif state == "scan":
            cmd = "w"  # turn-left to scan for the ball
            speed_override = int(getattr(t, "obstacle_turn_speed", 4) or 4)
            pattern_line = "PATTERN:scan-only"
        else:
            cmd = None
            pattern_line = ""

        if cmd is None:
            if not host._lost_search_sent_stop:
                host.send_stop_motion()
                host._lost_search_sent_stop = True
            try:
                host.ball_tracker.body_debug_lines = [
                    f"SEARCH:{state} (disabled)",
                    f"dist:{dist:.1f}cm near:{near_cm:.0f} clear:{clear_cm:.0f}",
                    f"missed:{int(getattr(t, 'missed_frames', 0))}",
                ]
            except Exception:
                pass
            host._lost_search_last_cmd_ts = now
            return

        # Send search motion
        host._lost_search_sent_stop = False
        host.send_motion_command(cmd, speed_override=speed_override)
        host._lost_search_last_cmd_ts = now

        try:
            cmd_name = host._cmd_key_to_human(cmd)
            lines = [
                f"SEARCH:{state} cmd:{cmd_name} spd:{int(speed_override) if speed_override is not None else int(getattr(host, 'move_speed', 8))}",
                f"dist:{dist:.1f}cm near:{near_cm:.0f} clear:{clear_cm:.0f}",
                f"missed:{int(getattr(t, 'missed_frames', 0))}",
            ]
            if pattern_line:
                lines.insert(1, pattern_line)
            host.ball_tracker.body_debug_lines = lines
        except Exception:
            pass
