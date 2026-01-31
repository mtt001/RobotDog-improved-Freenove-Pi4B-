---
**Document:** AI Vision Detection System  
**Source:** `mtDogMain.py`, `mtBallDetectAI.py`  
**Last reviewed:** 2026-01-17  
**Model (vision):** `gpt-4o-mini`  
---

# AI Vision Detection System

## Overview
The Freenove Robot Dog uses **OpenAI's gpt-4o-mini vision model** to detect orange/red balls in the camera feed. The system combines cloud-based AI detection with local Mac post-processing for filtering, logging, and overlay rendering. AI Vision is **single-shot** per button toggle: it sends one frame, caches detections, and only re-requests when you toggle it again.

---

## Architecture

```
┌──────────────────────────────┐
│  Video Source                │  Resolution/FPS varies
│  - Mac camera (OpenCV)       │  (no fixed size set)
│  - Dog Pi stream (JPEG)      │
└───────────────┬──────────────┘
         │
         ▼
┌─────────────────┐
│  Frame Capture  │  Single-shot when AI Vision is toggled on
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  JPEG Encoding  │  Quality: 80%, Base64 encoding
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  OpenAI API Call (gpt-4o-mini)                          │
│  - Sends: base64 JPEG + prompt                          │
│  - Receives: JSON with circle candidates                │
│  - Latency: ~0.5-2s depending on network               │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  JSON Parsing   │  Extract circles array (robust { ... } scan)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Local Post-Processing (Mac)                            │
│  1. Coordinate normalization (0-1 → pixels)            │
│  2. Score filtering (≥0.50 confidence)                  │
│  3. HSV color validation (orange/red check)            │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Visual Overlay │  Yellow circles + HSV text on color window
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LED Feedback   │  Yellow flash (rate-limited to 1/sec)
└─────────────────┘
```

## Runtime Behavior (Current Code)

- **Toggle gating:** `ai_vision_enabled` is flipped by the AI Vision button; enabling it resets `_ai_request_sent` so one request is allowed.
- **Frame source:** The request uses `last_display_frame_bgr` if available; otherwise it uses the current `frame` from `update_frame()`.
- **Single-shot:** After the first request, `_ai_request_sent` is set True and no more API calls occur until toggled again.
- **Telemetry:** Raw model output is stored in `last_raw_text` and printed if present; errors are recorded in `last_error`.

---

## AI Request Details

### Model
- **Name**: `gpt-4o-mini`
- **Provider**: OpenAI
- **Type**: Multi-modal (vision + text)
- **Cost**: Depends on your OpenAI account plan
- **Latency**: Network/inference dependent (variable)

### Prompt
```
You are a vision module that finds ball-like circles. 
Return ONLY JSON: {"circles":[{"x":int,"y":int,"r":int,"score":float}]}. 
Coordinates are pixel positions in the image. If none, return {"circles":[]}.
```

**Prompt Strategy:**
- **Concise**: Minimal tokens to reduce cost
- **Format-strict**: Demands JSON-only output to avoid parsing issues
- **Explicit schema**: Specifies exact field types (int, float)
- **Fallback-aware**: Instructs empty array when no detections

### Request Format
```python
# OpenAI SDK Responses API call
client.responses.create(
    model="gpt-4o-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": "data:image/jpeg;base64,..."}
            ]
        }
    ]
)
```

### Image Encoding
- **Format**: JPEG (converted from OpenCV BGR)
- **Quality**: 80% (balance between quality and payload size)
- **Encoding**: Base64 string in data URL format
- **Typical size**: Depends on content/resolution (JPEG-compressed)

### Expected JSON Response Format

**Single candidate:**
```json
{
  "circles": [
    {
      "x": 320,
      "y": 240,
      "r": 25,
      "score": 0.95
    }
  ]
}
```

**Multiple candidates:**
```json
{
  "circles": [
    {
      "x": 150,
      "y": 200,
      "r": 20,
      "score": 0.85
    },
    {
      "x": 480,
      "y": 180,
      "r": 18,
      "score": 0.72
    }
  ]
}
```

**No detections:**
```json
{
  "circles": []
}
```

### Field Definitions
| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `x` | int/float | 0 - frame_width OR 0.0 - 1.0 | Center X coordinate (absolute pixels or normalized) |
| `y` | int/float | 0 - frame_height OR 0.0 - 1.0 | Center Y coordinate (absolute pixels or normalized) |
| `r` | int/float | 1 - max(width,height)/2 OR 0.0 - 1.0 | Circle radius (absolute pixels or normalized) |
| `score` | float | 0.0 - 1.0 | Confidence level (1.0 = highest confidence) |

**Multiple Candidates:** Yes, the model can return multiple ball candidates in a single response. Each candidate is independently filtered and rendered.

---

## Local Post-Processing (MacBook Pro)

All post-processing runs locally on the Mac using OpenCV and NumPy.

## Video Source and Resolution

AI Vision runs on whatever frame source is active in `update_frame()`:

### Source Selection
- **Dog Pi video:** When `self.use_dog_video` is True, frames are pulled from `Client.image` (decoded JPEGs from the Pi stream).
- **Client Mac camera:** Otherwise, frames come from `cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)` on macOS.

### Resolution Handling
- **Dog Pi video:** No resizing in `mtDogMain.py`. The frame resolution is whatever the Pi server sends over the JPEG stream.
- **Mac camera:** No explicit `CAP_PROP_FRAME_WIDTH/HEIGHT` is set in `mtDogMain.py`, so resolution is whatever the camera driver returns by default.
- **Fallback frames:** When no video is available, the code creates a `480x640` placeholder image for the UI.

### Practical Implications
- AI detections and HSV sampling always use the **actual frame shape** at runtime.
- If you need a fixed resolution for AI consistency, add explicit resize or `cap.set(...)` for the Mac camera, and confirm the Pi stream resolution in the server-side video sender.

### Step 1: Coordinate Normalization

**Problem:** AI may return coordinates in normalized format (0.0-1.0) or absolute pixels.

**Detection Logic:**
```python
if 0 < x <= 1.0 and 0 < y <= 1.0 and frame_width > 1 and frame_height > 1:
    x_pixels = x * frame_width
    y_pixels = y * frame_height
```

**Radius Normalization:**
```python
if 0 < r <= 1.0 and min(frame_width, frame_height) > 1:
    r_pixels = r * min(frame_width, frame_height)
```

**Output:** All coordinates converted to absolute pixel positions (e.g., x=320, y=240, r=25).

### Step 2: Score Filtering

**Threshold:** `ai_score_min = 0.50`

**Logic:**
```python
if detection_score < 0.50:
    reject_detection()  # Skip low-confidence detections
```

**Purpose:** Eliminates weak candidates that the model itself is uncertain about, reducing false positives.

### Step 3: HSV Color Validation

**Hardware:** Mac (CPU-based)  
**Library:** OpenCV (local install)

#### Color Space Conversion
```python
hsv_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2HSV)
# OpenCV HSV ranges: H: 0-179, S: 0-255, V: 0-255
```

#### Pixel Sampling
At each detected center (x, y):
```python
H, S, V = hsv_frame[y, x]  # Sample single pixel at ball center
```

#### Filter Parameters
```python
ai_hue_ranges = [(0, 40), (150, 179)]  # Orange/red hues
ai_min_s = 25   # Minimum saturation (color richness)
ai_min_v = 25   # Minimum value (brightness)
```

#### Validation Rules
1. **Saturation Check:**
   ```python
   if S < 25:
       reject("Too gray/washed out")
   ```

2. **Value Check:**
   ```python
   if V < 25:
       reject("Too dark")
   ```

3. **Hue Range Check:**
   ```python
   hue_valid = False
   if (0 <= H <= 40) or (150 <= H <= 179):
       hue_valid = True
   if not hue_valid:
       reject("Wrong color (not orange/red)")
   ```

#### Rejection Logging
```
[AI] Reject #0@(320,240): HSV(85,180,200) - Hue not in [(0,40),(150,179)]
[AI] Reject #1@(150,100): HSV(15,12,220) - S<25 or V<25
```

**Purpose:** Eliminates detections that pass AI confidence but fail color validation (e.g., detecting white/blue objects).

### Step 4: Visual Overlay Rendering

**Hardware Acceleration:** Metal-accelerated rendering via PyQt5 on macOS

**Overlay Elements:**
1. **Yellow Circle:** `cv2.circle(frame, (x,y), radius, (0,255,255), 2)`
2. **Center Dot:** `cv2.circle(frame, (x,y), 2, (0,255,255), -1)`
3. **Text Line 1:** `D40px, (320,240)` (diameter in pixels, center coordinates)
4. **Text Line 2:** `HSV(15,180,200)` (sampled color at center)

**Text Rendering:**
- Font: `cv2.FONT_HERSHEY_SIMPLEX`, size 0.45
- Color: Yellow (0,255,255) with black outline for contrast
- Position: 10px right, 10px above circle center

### Step 5: LED Feedback

**Rate Limiting:** Maximum 1 flash per second to prevent strobe effect

```python
if (current_time - last_flash_time) >= 1.0:
    flash_yellow_led(duration=0.18s)
    last_flash_time = current_time
```

**Purpose:** Provides immediate visual feedback when ball detected, without overwhelming the user.

---

## Performance Characteristics

### Latency Breakdown
| Stage | Time | Location |
|-------|------|----------|
| Frame capture | ~33ms | Local (Mac camera) |
| JPEG encoding | ~5-10ms | Local (OpenCV) |
| API network + inference | ~500-2000ms | Cloud (OpenAI) |
| JSON parsing | <1ms | Local (Python) |
| HSV filtering | ~1-2ms | Local (OpenCV) |
| Overlay rendering | ~2-5ms | Local (PyQt5/Metal) |
| **Total** | **~550-2050ms** | **Cloud-dominated** |

### Detection Frequency
- **Current behavior:** Single-shot per toggle (one request after enabling AI Vision)
- **Config placeholder:** `ai_detect_interval_s` exists but is not currently used
- **Parallel processing:** No (single request at a time)

### Resource Usage
- **CPU:** Minimal (<5% on M-series during post-processing)
- **Memory:** ~50MB for OpenCV buffers + model responses
- **Network:** ~15-30KB upload per request, ~1KB download
- **Cost:** Depends on account billing and usage

---

## Configuration Parameters

### AI Model Settings
```python
self.ai_detector = AIVisionBallDetector(model="gpt-4o-mini")
self.ai_detect_interval_s = 1.0  # Defined but not used in current loop
```

### Score Filtering
```python
self.ai_score_min = 0.50  # Minimum confidence threshold
```

### HSV Color Filtering
```python
self.ai_hsv_filter_enabled = True
self.ai_hue_ranges = [(0, 40), (150, 179)]  # Orange/red hues
self.ai_min_s = 25  # Minimum saturation
self.ai_min_v = 25  # Minimum brightness
```

### LED Feedback
```python
self._ai_led_last_ts = 0.0  # Track last flash time
led_rate_limit = 1.0  # Minimum 1 second between flashes
```

---

## Code Modules

### mtBallDetectAI.py
**Purpose:** AI API wrapper and response parsing

**Key Classes:**
- `AICircle`: Data class for circle detections (x, y, r, score)
- `AIVisionBallDetector`: OpenAI API client wrapper
  - `analyze(frame_bgr)`: Send frame to API, return list of AICircle
  - `last_error`: Stores error messages
  - `last_latency_s`: Records API call duration
  - `last_raw_text`: Raw JSON response from model
  - `last_parsed`: Parsed Python dict

**Key Functions:**
- `_safe_json(text)`: Robust JSON extraction (handles markdown code blocks, extra text)
  - Note: It simply tries full JSON parse, then first "{" to last "}" substring.

### mtDogMain.py
**Purpose:** Main application with AI integration

**AI-Related Sections:**
- **Lines 241-253:** AI initialization and filter parameters
- **Lines 1133-1210:** AI detection loop in `update_frame()`
  - Sends frame to API every 1 second
  - Filters results by score + HSV
  - Logs candidate info
- **Lines 348-420:** `_draw_ai_detections()` method
  - Renders yellow circles and text overlays
  - Triggers LED feedback

---

## Debugging

### Log Output Format

**Successful detection with filtering:**
```
[AI] Response: 2 candidates (latency 1.23s)
[AI] Raw response:
{"circles":[{"x":320,"y":240,"r":25,"score":0.95},{"x":150,"y":100,"r":18,"score":0.65}]}
[AI] Reject #1@(150,100): HSV(15,12,220) - S<25 or V<25
[AI] Filtered: 1/2 kept
[AI] #0 D50px HSV(18,180,210) center:(320,240) score:0.95
```

**No detections:**
```
[AI] Response: 0 candidates (latency 0.87s)
```

**HSV rejection:**
```
[AI] Response: 1 candidates
[AI] Reject #0@(200,150): HSV(120,200,180) - Hue not in [(0,40),(150,179)]
[AI] Filtered: 0 kept
```

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| No API response | Missing `OPENAI_API_KEY` | Set environment variable |
| All detections filtered | HSV thresholds too strict | Lower `ai_min_s`, `ai_min_v` |
| False positives | Score threshold too low | Increase `ai_score_min` |
| Wrong position overlay | Coordinate normalization bug | Check 0-1 range detection logic |
| LED flashing excessively | Rate limiter disabled | Verify 1-second rate limit |

---

## Future Enhancements

### Potential Improvements
1. **Multi-frame tracking:** Kalman filter for temporal consistency
2. **Adaptive HSV:** Learn color ranges from user-confirmed detections
3. **Model fine-tuning:** Train custom vision model on dog's camera data
4. **Edge inference:** Run lightweight model locally (CoreML/ONNX) to reduce latency
5. **Confidence calibration:** Map model scores to actual detection accuracy

### Performance Optimization
- **Reduce resolution:** Downscale to 320×240 before encoding (4× smaller payload)
- **Frame skipping:** Only send frames when motion detected
- **Batch processing:** Queue frames and send multiple in parallel (if API supports)
- **Local caching:** Skip API call if frame identical to previous detection
