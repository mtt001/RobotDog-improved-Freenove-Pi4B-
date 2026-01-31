---
Document: System Restructure Proposal (mtDogMain.py Decomposition)
Background: Freenove Robot Dog Client refactor for modularity and AI/skills extensibility
Author: Codex (draft for project owner review)
Date: 2026-01-17
---

# System Restructure Proposal (mtDogMain.py Decomposition)

## Goals
- Reduce `mtDogMain.py` to a thin UI shell and app orchestrator.
- Enforce reasonable module size (target 200-400 LOC per file).
- Establish clean boundaries for video, vision, behavior, actuators, telemetry, and skills.
- Make room for new skills and AI extensions (roaming, dog interaction, audio I/O, human interaction, API key mgmt).

## Target Architecture

```
Client/
  app/
    app.py                 # App bootstrap, wiring, lifecycle
    config.py              # App + runtime config (loads mtDogConfig)
    state.py               # Global state container (lightweight dataclass)
  ui/
    main_window.py         # Qt window class (thin)
    widgets/
      status_bar.py
      controls_panel.py
      overlay_renderer.py
  video/
    source.py              # Unified camera source interface
    source_mac.py          # OpenCV Mac camera
    source_dogpi.py         # JPEG stream from Pi (Client)
    frame_buffer.py         # Last frame, timestamps, FPS
  vision/
    ball_tracker.py         # mtDogBallTrack (refactor)
    ai_detector.py          # mtBallDetectAI wrapper, prompt config
    post_filter.py          # HSV/score filtering
    overlays.py             # draw circles, text, HSV
  behavior/
    tracking_controller.py  # body/head tracking decisions
    lost_search.py          # search state machine
    close_enough.py         # completion/latched behavior
  actuators/
    dog_client.py           # wrapper around Client.py (control/video)
    head.py                 # head angle commands
    led.py                  # LED flash control
    audio.py                # beeps/bark sequences
  telemetry/
    telemetry.py            # dog telemetry polling
    diagnostics.py          # video stall + status checks
  skills/
    registry.py             # plugin manager
    base.py                 # Skill base class + context
    roaming.py              # room roaming/search ball
    interaction_dog.py      # dog-dog interaction behavior
    interaction_human.py    # human interaction behavior
    audio_io.py             # mic input / audio output
    ai_keys.py              # API key config & validation
  infra/
    threading.py            # shared timers, workers
    logging.py              # logging utils
    events.py               # event bus (simple pub/sub)
```

## Module Boundaries and Size Limits
- `ui/*`: Qt widgets, layout, and signals only (<300 LOC each).
- `video/*`: frame acquisition, buffering, FPS, metadata (<300 LOC each).
- `vision/*`: detection, filtering, overlays (<400 LOC each).
- `behavior/*`: state machines and decisions; no UI rendering (<400 LOC each).
- `actuators/*`: hardware commands only (<250 LOC each).
- `skills/*`: optional behavior sets loaded by registry (<300 LOC each).
- `app/*`: wiring and lifecycle (<200 LOC each).
- `infra/*`: utilities without domain dependencies.

## Key Decomposition of mtDogMain.py

Move these responsibilities into dedicated modules:

- UI construction and styling -> `ui/widgets/*`
- Frame capture and source switching -> `video/source_*`
- AI Vision request, filter, and overlay -> `vision/*`
- Ball tracking and search states -> `behavior/*` and `vision/ball_tracker.py`
- Head/body tracking decisions -> `behavior/tracking_controller.py`
- Barking, beeps, LED feedback -> `actuators/audio.py`, `actuators/led.py`
- Telemetry polling and server checks -> `telemetry/*`
- Global state and config -> `app/state.py`, `app/config.py`

## Video Source and Resolution
- Provide a unified `VideoSource` interface that exposes `get_frame()`, `fps()`, `source_name()`, and `resolution()`.
- Mac camera: `source_mac.py` wraps `cv2.VideoCapture` with optional fixed resolution.
- Dog Pi: `source_dogpi.py` reads frames from `Client.py` image buffer.
- Allow optional `resize_to` in `app/config.py` to normalize AI Vision inputs.

## Extensibility for Skills and AI
- `infra/events.py`: publish events such as `frame`, `ball_detected`, `telemetry_update`.
- `skills/registry.py`: discover and enable skills based on config.
- Each skill implements a `Skill` base class with `on_event(...)` hooks.
- Skills can call actuators via a shared context object:
  - Roaming: obstacle-aware navigation, room search pattern.
  - Dog interaction: social behaviors based on detections.
  - Human interaction: face detection, commands via audio input.
  - AI API key management: load/validate/store key securely.

## Proposed File Mapping (Examples)
- `mtDogMain.py:update_frame()` -> `video/source.py` + `vision/overlays.py` + `behavior/*` + `telemetry/*`
- `_draw_ai_detections()` -> `vision/overlays.py`
- AI detection + filtering -> `vision/ai_detector.py`, `vision/post_filter.py`
- `handle_ai_vision_button()` -> UI layer emits event; app toggles vision state.
- `send_head_angle()` -> `actuators/head.py`

## Module Skeletons (Draft)

### app/app.py
```python
from app.config import AppConfig
from app.state import AppState
from infra.events import EventBus
from video.source import VideoSource

class App:
    def __init__(self, config: AppConfig):
        self.config = config
        self.state = AppState()
        self.events = EventBus()
        self.video_source: VideoSource | None = None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
```

### app/state.py
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AppState:
    use_dog_video: bool = False
    ai_vision_enabled: bool = False
    last_frame: Any = None
```

### video/source.py
```python
from typing import Protocol, Tuple, Any

class VideoSource(Protocol):
    def get_frame(self) -> Any: ...
    def fps(self) -> float: ...
    def source_name(self) -> str: ...
    def resolution(self) -> Tuple[int, int]: ...
```

### video/source_mac.py
```python
import cv2

class MacCameraSource:
    def __init__(self, index: int = 0):
        self.cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)

    def get_frame(self):
        ret, frame = self.cap.read()
        return frame if ret else None
```

### video/source_dogpi.py
```python
import numpy as np

class DogPiSource:
    def __init__(self, dog_client):
        self.dog_client = dog_client

    def get_frame(self) -> np.ndarray | None:
        with self.dog_client.image_lock:
            return self.dog_client.image.copy() if isinstance(self.dog_client.image, np.ndarray) else None
```

### vision/ai_detector.py
```python
from mtBallDetectAI import AIVisionBallDetector

class AIVisionService:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.detector = AIVisionBallDetector(model=model)

    def analyze(self, frame_bgr):
        return self.detector.analyze(frame_bgr)
```

### vision/post_filter.py
```python
class AIPostFilter:
    def __init__(self, score_min=0.50, hsv_ranges=None, min_s=25, min_v=25):
        self.score_min = score_min
        self.hsv_ranges = hsv_ranges or [(0, 40), (150, 179)]
        self.min_s = min_s
        self.min_v = min_v

    def filter(self, frame_bgr, detections):
        return detections
```

### behavior/tracking_controller.py
```python
class TrackingController:
    def update_full_body_tracking(self, ball_center, frame_shape):
        pass

    def handle_tracking_mode_transition(self, mode):
        pass
```

### actuators/audio.py
```python
class AudioActuator:
    def beep_pattern(self, beeps: int, on_s: float, off_s: float):
        pass

    def start_barking(self):
        pass

    def stop_barking(self):
        pass
```

### skills/base.py
```python
class Skill:
    name: str = "base"

    def on_event(self, event_name: str, payload):
        pass
```

## Migration Checklist (Mapped to mtDogMain.py)

### UI and Window
- `CameraWindow.__init__` -> `ui/main_window.py`
- `build_ui`, `update_status_ui` -> `ui/widgets/*`
- `mousePressEvent`, `mouseMoveEvent`, `keyPressEvent`, `closeEvent` -> `ui/main_window.py`

### Frame and Video Handling
- `update_frame` (frame acquisition) -> `video/source.py`, `video/source_mac.py`, `video/source_dogpi.py`
- `last_display_frame_bgr` handling -> `video/frame_buffer.py`
- `try_reconnect`, `_startup_initial_probe`, server checks -> `telemetry/diagnostics.py`

### AI Vision
- `ai_vision_enabled`, `_ai_request_sent`, `_ai_detections` -> `vision/ai_detector.py`, `vision/post_filter.py`
- `_draw_ai_detections` -> `vision/overlays.py`
- `handle_ai_vision_button` -> `ui/widgets/controls_panel.py` (emit event)

### Ball Tracking and Behavior
- `ball_mode_enabled`, `ball_tracker` -> `vision/ball_tracker.py`
- `_update_full_body_tracking`, `_handle_tracking_mode_transition` -> `behavior/tracking_controller.py`
- `_update_lost_ball_search` -> `behavior/lost_search.py`
- `_trigger_close_enough_sequence`, `_bark_should_run` -> `behavior/close_enough.py`

### Actuators and Feedback
- `_start_barking`, `_stop_barking`, `_bark_tick` -> `actuators/audio.py`
- LED flash timing in `_draw_ai_detections` -> `actuators/led.py`
- `send_head_angle` -> `actuators/head.py`
- `_send_relax_only`, `_send_stop_pwm_only` -> `actuators/dog_client.py`

### Misc
- `_cmd_key_to_human` -> `app/state.py` or `ui/main_window.py` as a local helper

## Safe Migration Plan (with Backup and Restoration)

1. **Snapshot backup before each extraction**
   - Copy `mtDogMain.py` to `Backup/mtDogMain.pre_refactor.YYYYMMDD.py`.
   - If using git, create a branch or tag before each extraction step.

2. **Extract one subsystem at a time**
   - Start with video sources, then AI vision, then behavior, then actuators, then UI.
   - After each step, run a quick manual smoke test (open app, confirm video, toggle AI Vision).

3. **Keep compatibility shims**
   - Temporarily import new modules into `mtDogMain.py` and forward-call existing method names.
   - Avoid breaking key bindings or UI signal wiring during transitions.

4. **Restore procedure if a step fails**
   - Replace current file with the latest `Backup/mtDogMain.pre_refactor.YYYYMMDD.py`.
   - Revert module changes tied to that step only; leave earlier completed steps intact.

5. **Finalize and delete shims**
   - Once a subsystem is stable, remove duplicate old methods in `mtDogMain.py`.
   - Update documentation to reflect final module ownership.

## Migration Plan (Incremental)
1. Extract video sources (Mac + Dog Pi) behind a unified interface.
2. Extract AI Vision (request, parsing, filtering, overlays).
3. Extract behavior state machines (tracking, lost search, close-enough).
4. Extract actuators (head, LED, audio).
5. Introduce event bus and skill registry with one pilot skill.
6. Reduce `mtDogMain.py` to UI wiring and high-level orchestration.

## Risks and Mitigations
- Behavior regressions: keep function signatures stable during moves; add frame-based tests.
- Threading issues: centralize mutable state in `app/state.py`.
- UI coupling: enforce "UI-only" rule in `ui/*`.

## Testing Strategy
- Replay recorded frames for tracking regressions.
- Snapshot test overlays with known inputs.
- Integration test for both video sources and AI Vision on/off.
