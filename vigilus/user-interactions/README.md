# User Interactions

**Behavioral biometrics verification** — the third layer in the Vigilus defense stack.

While `browser-integrity` proves a real browser exists and `browser-signals` detects automation artifacts, **user-interactions** proves a _human_ is operating the device by analyzing the biomechanics of their input.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Defense Stack                               │
│                                                                 │
│  Layer 1: browser-integrity   → Is this a real browser?         │
│  Layer 2: browser-signals     → Is it running automation?       │
│  Layer 3: user-interactions   → Is a human controlling it?  ◄── │
└─────────────────────────────────────────────────────────────────┘
```

Sophisticated bots with undetected-chromedriver can pass signal checks. They cannot replicate the involuntary biomechanical patterns of a human hand.

---

## Protocol

```
Client                                    Server
  │                                          │
  │─── POST /interactions/init ─────────────►│  Create challenge + nonce
  │◄── { challengeId, scriptUrl, ttl } ──────│
  │                                          │
  │─── GET /interactions/probe/:id.js ──────►│  Serve collector with embedded nonce
  │◄── (JavaScript collector) ───────────────│
  │                                          │
  │    ┌──────────────────────┐              │
  │    │ Collect for 3-15s:   │              │
  │    │ • Mouse movement     │              │
  │    │ • Click positions    │              │
  │    │ • Keystroke timing   │              │
  │    │ • Scroll patterns    │              │
  │    │ • Touch + pressure   │              │
  │    │ • Gyro/Accel sensors │              │
  │    │ • Event ordering     │              │
  │    └──────────────────────┘              │
  │                                          │
  │─── POST /interactions/verify ───────────►│  HMAC-verify, then analyze
  │    { cid, d, ts }  +  X-Signature        │
  │◄── { cleared, score, token, flags } ─────│
  │                                          │
  │─── GET /protected ──────────────────────►│  Bearer token validation
  │    Authorization: Bearer <token>         │
  │◄── { message, score } ───────────────────│
```

---

## Signals Collected

| Category           | Data                                        | Desktop | Mobile |
| ------------------ | ------------------------------------------- | :-----: | :----: |
| Mouse position     | Sub-pixel x,y with timestamps               |    ●    |        |
| Click landing      | Offset from target center + dwell time      |    ●    |        |
| Keystroke timing   | Hold duration + inter-key gaps              |    ●    |   ●    |
| Scroll behavior    | Position, delta, timestamps                 |    ●    |   ●    |
| Touch events       | Position, pressure, contact radius          |         |   ●    |
| Accelerometer      | 3-axis acceleration readings                |         |   ●    |
| Gyroscope          | 3-axis rotation rate                        |         |   ●    |
| Device orientation | Alpha, beta, gamma angles                   |         |   ●    |
| Event ordering     | Timestamped sequence of all event types     |    ●    |   ●    |
| Engagement         | Time-to-first-interaction, session duration |    ●    |   ●    |

---

## Analysis Algorithms

### Mouse Movement — _weight: 0.30_

The core signal. Human motor control follows biomechanical constraints that are extremely hard to fake.

| Check                                                                             | Human                                                   | Bot                                                         | Penalty   |
| --------------------------------------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------- | --------- |
| **Curvature entropy** — Menger curvature distribution across path                 | Variable curvature, high entropy (>2.0)                 | Near-zero curvature (straight lines), low entropy           | 0.05–0.12 |
| **Micro-tremor** — RMS of residuals from 5-point smoothed path                    | 0.3–8px wobble from physiological hand tremor (8-12 Hz) | <0.05px (algorithmically smooth) or >20px (noise injection) | 0.06–0.10 |
| **Velocity variance** — Coefficient of variation of instantaneous velocity        | CV >0.4 (accelerate/cruise/decelerate per Fitts' Law)   | CV <0.15 (constant speed)                                   | 0.05–0.12 |
| **Jerk analysis** — Third derivative of position (rate of acceleration change)    | High variance (irregular corrections)                   | Low variance (smooth function)                              | 0.06      |
| **Straightness index** — Path length ÷ direct distance over 15-point windows      | 1.02–1.5 (natural curves)                               | ~1.000 (ruler-straight)                                     | 0.04–0.10 |
| **Direction entropy** — Shannon entropy of angle changes between segments         | >2.5 (normally distributed angles)                      | <1.2 (discrete angles: 0°, 45°, 90°)                        | 0.08      |
| **Timing regularity** — Interval CV + mode analysis for machine-precise intervals | Variable intervals, no dominant mode                    | >70% of intervals identical, avg >80ms                      | 0.08–0.10 |
| **Teleportation** — >300px displacement in <10ms                                  | Never                                                   | Common (element-to-element jumps)                           | 0.08–0.15 |
| **Origin clustering** — Points at (0,0)                                           | Never                                                   | Common initialization artifact                              | 0.08      |
| **Bezier detection** — Consistency of second derivative (acceleration)            | Irregular acceleration (>15% variation)                 | >85% constant acceleration (synthetic curves)               | 0.10      |

### Click Landing — _weight: 0.15_

Humans almost never click the exact geometric center of an element.

| Check                                                                       | Human                              | Bot                                      | Penalty   |
| --------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------- | --------- |
| **Center offset ratio** — Distance from click to element center, normalized | >5% offset, variable across clicks | >70% within 5% of center (pixel-perfect) | 0.06–0.12 |
| **Offset variance** — Standard deviation of offsets across multiple clicks  | std >0.02                          | std <0.02 (identical positions)          | 0.08      |
| **Click dwell time** — mousedown→mouseup duration                           | 60–250ms, variable (CV >0.15)      | <10ms or perfectly uniform               | 0.06–0.08 |
| **Zero-duration clicks** — Dwell = 0ms                                      | Never                              | Event dispatch without mousedown/up      | 0.08      |

### Pre-click Deceleration — _weight: 0.10_

Fitts' Law: humans decelerate as they approach a click target.

| Check                               | Human                       | Bot                                            |
| ----------------------------------- | --------------------------- | ---------------------------------------------- |
| Velocity in last 500ms before click | Decreasing (approach phase) | Constant or increasing (no targeting behavior) |

### Keystroke Dynamics — _weight: 0.15_

Every human has a unique typing rhythm that is impossible to perfectly replicate.

| Check                                                            | Human                            | Bot                                     | Penalty   |
| ---------------------------------------------------------------- | -------------------------------- | --------------------------------------- | --------- |
| **Dwell time** — Key hold duration                               | 50–200ms, variable by finger/key | <5ms or identical across all keys       | 0.08–0.10 |
| **Flight time** — Gap between key release and next press         | 30–500ms, variable               | <15ms (impossible) or perfectly uniform | 0.08–0.10 |
| **Rhythm entropy** — Shannon entropy of combined timing sequence | >2.0 (natural variation)         | <1.5 (mechanical precision)             | 0.06      |
| **Uniform detection** — CV of dwell and flight times             | CV >0.15                         | CV <0.08 (robotic uniformity)           | 0.08      |

### Scroll Behavior — _weight: 0.10_

| Check                   | Human                    | Bot                          |
| ----------------------- | ------------------------ | ---------------------------- |
| **Velocity variance**   | Variable bursts + pauses | Constant velocity (CV <0.15) |
| **Direction reversals** | Frequent (re-reading)    | None (one-directional)       |
| **Pauses**              | >300ms gaps (reading)    | Continuous scrolling         |
| **Delta uniformity**    | Variable scroll amounts  | Fixed increments (CV <0.05)  |

### Touch Biometrics — _weight: 0.10_

Real fingers produce a pressure distribution and blob-shaped contact area.

| Check                  | Human                                   | Bot                                |
| ---------------------- | --------------------------------------- | ---------------------------------- |
| **Pressure variation** | CV >0.01 (changing during gesture)      | CV ~0 (constant or absent)         |
| **Contact area**       | radiusX/Y vary as finger rolls          | Constant or zero                   |
| **Trajectory wobble**  | Sub-pixel deviations from straight line | RMS <0.3px (geometrically perfect) |
| **End deceleration**   | Natural slowdown at swipe end           | Constant velocity or abrupt stop   |

### Sensor Data — _weight: 0.10_

A human holding a device introduces involuntary micro-movement.

| Check                      | Human                                       | Bot                      |
| -------------------------- | ------------------------------------------- | ------------------------ |
| **Accelerometer noise**    | stddev 0.01–0.5 per axis (micro-vibrations) | Zero or perfectly static |
| **Gyroscope tremor**       | Detectable 8-12 Hz oscillation              | Zero rotation rate       |
| **Orientation drift**      | Slow natural drift over time                | Perfectly fixed angles   |
| **Cross-axis correlation** | Correlated noise between axes               | Independent or zero      |

### Event Ordering — _weight: 0.05_

Browser events fire in specific sequences. Violations indicate synthetic dispatch.

```
Expected:  mousemove → mousedown → mouseup → click
           keydown → keyup
           touchstart → touchmove → touchend
```

| Anomaly                                   | Penalty   |
| ----------------------------------------- | --------- |
| Click without preceding mousedown→mouseup | 0.02 each |
| mousedown→mouseup at identical timestamp  | 0.03      |
| touchmove without preceding touchstart    | 0.02      |
| keyup without preceding keydown           | 0.02      |

### Engagement — _weight: 0.05_

| Check                         | Human                           | Bot                  |
| ----------------------------- | ------------------------------- | -------------------- |
| **Time to first interaction** | >200ms (visual processing)      | <50ms (pre-scripted) |
| **Event density**             | Reasonable for session duration | >50 events in <500ms |

---

## Scoring

```
Final Score = 1.0 - Σ(category penalties)

Each category has a maximum penalty cap:
  Mouse:       0.30    Click:        0.15
  Pre-click:   0.10    Keystrokes:   0.15
  Scroll:      0.10    Touch:        0.10
  Sensors:     0.10    Event order:  0.05
  Engagement:  0.05
                       ─────────────────
  Maximum total:       1.00

Score ≥ 0.5 → CLEARED (human)     Token issued
Score < 0.5 → BLOCKED (bot)       No token
```

The threshold is configurable via `SCORE_THRESHOLD` environment variable.

---

## Quick Start

```bash
cd user-interactions
npm install
npm start
# → http://localhost:3002
```

Open the test page and interact naturally — move your mouse around, click the buttons, type in the input field, and scroll. The system will auto-submit after collecting enough data (3–15 seconds) and display the analysis.

## Configuration

| Variable              | Default         | Description                                           |
| --------------------- | --------------- | ----------------------------------------------------- |
| `PORT`                | `3002`          | Server port                                           |
| `INTERACTIONS_SECRET` | Random 32 bytes | Token signing secret                                  |
| `SCORE_THRESHOLD`     | `0.5`           | Minimum score to clear (0.0–1.0)                      |
| `DEBUG_ANALYSIS`      | —               | Set to any value to include full analysis in response |

## Integration

```javascript
// 1. Init challenge
const { scriptUrl } = await fetch('/interactions/init', {
    method: 'POST',
}).then((r) => r.json());

// 2. Load collector
const script = document.createElement('script');
script.src = scriptUrl;
document.head.appendChild(script);

// 3. Handle result (auto-submits when ready, or call manually)
window.__interactionResult = (result) => {
    if (result.cleared) {
        // Use result.token for authenticated requests
        fetch('/api/data', {
            headers: { Authorization: `Bearer ${result.token}` },
        });
    }
};

// OR trigger manually:
const result = await window.__interactionProbe.verify();
```

## Why This Works

| Attack                        | Defense                                                                  |
| ----------------------------- | ------------------------------------------------------------------------ |
| Selenium/Puppeteer `moveTo()` | Produces straight lines with uniform velocity and zero curvature entropy |
| Bezier curve mouse libraries  | Detectable by constant second derivative (too-smooth acceleration)       |
| Recorded human replay         | HMAC nonce prevents replay; timestamps won't match                       |
| Synthetic `dispatchEvent()`   | Missing mousedown→mouseup sequence; zero click dwell                     |
| Headless touch simulation     | Zero pressure, zero contact radius, no wobble                            |
| Emulated sensors              | Zero noise floor, no cross-axis correlation                              |
| Fast `sendKeys()`             | Flight times <15ms (physically impossible), zero dwell variance          |

The fundamental insight: **human motor control is governed by biomechanical constraints** (Fitts' Law, physiological tremor, speed-accuracy tradeoff) that produce characteristic statistical signatures in movement data. These signatures are involuntary and extremely difficult to replicate at the distribution level, even when individual data points can be faked.
