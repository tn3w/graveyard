# Browser Signals

Anti-replay browser signal verification with polymorphic nonce hiding.

## The Problem

Browser integrity checks collect signals from the client to detect bots. But a headless browser can:

1. Execute the JS, collect real signals
2. Capture the resulting payload
3. **Replay** that same payload later without a browser

The signals themselves are valid — the attack works because the payload is not bound to a specific server-issued challenge.

## The Solution

```
                         ┌─────────────┐
                         │   Server    │
                         │             │
    ┌───── POST /init ──>│ Generate    │
    │                    │  nonce N    │
    │  <── {id, url} ─── │  store N    │
    │                    │             │
    │  GET /payload/id ─>│ Generate    │
    │                    │ unique JS   │
    │  <── JS file ───── │ with N      │
    │       (N hidden)   │ scattered   │
    │                    │             │
    │                    │             │
    │  Browser executes: │             │
    │  1. Collect signals│             │
    │  2. Find N in code │             │
    │  3. HMAC(N, data)  │             │
    │                    │             │
    │  POST /verify ────>│ Look up N   │
    │  {signals, sig}    │ Verify HMAC │
    │                    │ Score sigs  │
    │  <── clearance ─── │ Burn nonce  │
    │       token        │ (single-use)│
    └────────────────────┴─────────────┘
```

### Why This Defeats Replay

| Attack                | Defense                                                         |
| --------------------- | --------------------------------------------------------------- |
| Replay same payload   | Nonce is single-use — burned after first verification           |
| Extract nonce from JS | Polymorphic code — structure changes every time, expires in 30s |
| Pre-compute signals   | Nonce unknown until JS is fetched; JS is unique per challenge   |
| MITM/intercept nonce  | Nonce never sent in plaintext — hidden in obfuscated JS         |
| Brute-force signature | 256-bit HMAC with 256-bit nonce — computationally infeasible    |

## Architecture

```
browser-signals/
├── server.js              # Express: /init, /payload/:id.js, /verify, /protected
├── lib/
│   ├── challenges.js      # Nonce generation, single-use enforcement, clearance tokens
│   ├── payload.js         # Polymorphic JS generator (nonce hiding + signal collectors)
│   └── scorer.js          # Signal scoring engine (0.0–1.0)
├── public/
│   └── index.html         # Test UI
└── package.json
```

## Protocol Flow

```
 Client                              Server
   │                                    │
   │──── POST /signals/init ───────────>│
   │                                    │── Generate challenge ID
   │                                    │── Generate random nonce (32 bytes)
   │                                    │── Store {id, nonce, expires_at, used: false}
   │                                    │── Generate polymorphic JS with nonce hidden
   │<─── {challengeId, scriptUrl} ──────│
   │                                    │
   │──── GET /signals/payload/:id.js ──>│
   │                                    │── Validate challenge exists & not expired
   │<─── application/javascript ────────│── Return polymorphic JS (no-cache headers)
   │                                    │
   │  ┌─ Execute JS in browser ─┐       │
   │  │ 1. Collect ALL signals  │       │
   │  │ 2. Reconstruct nonce    │       │
   │  │    from 8 fragments     │       │
   │  │    (scattered, encoded) │       │
   │  │ 3. message = id:ts:JSON │       │
   │  │ 4. sig = HMAC(nonce,msg)│       │
   │  └─────────────────────────┘       │
   │                                    │
   │──── POST /signals/verify ─────────>│
   │     {cid, s, ts, sig}              │── Validate challenge (exists, not expired, not used)
   │                                    │── Verify timestamp freshness
   │                                    │── Recompute HMAC with stored nonce
   │                                    │── Compare signatures (timing-safe)
   │                                    │── Burn nonce (mark used, delete)
   │                                    │── Score signals → 0.0–1.0
   │<─── {cleared, score, token} ───────│── Issue clearance token if score ≥ threshold
   │                                    │
   │──── GET /protected ───────────────>│
   │     Authorization: Bearer <token>  │── Verify clearance token
   │<─── {message: "Access granted"} ───│
```

## Nonce Hiding: Polymorphic Obfuscation

The nonce (64 hex chars) is split into **8 fragments** of 8 chars each. Each fragment is encoded with a **randomly selected method**:

```
Nonce: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2

Fragment 1: a1b2c3d4  →  XOR pair encoding
Fragment 2: e5f6a7b8  →  Char code array
Fragment 3: c9d0e1f2  →  Base64 encoding
Fragment 4: a3b4c5d6  →  Math derivation (XOR pairs)
Fragment 5: e7f8a9b0  →  String slice from decoy
Fragment 6: c1d2e3f4  →  Split interleave
Fragment 7: a5b6c7d8  →  Reverse string
Fragment 8: e9f0a1b2  →  Char shift
```

### Encoding Methods

| #   | Method               | Example Code                                                    |
| --- | -------------------- | --------------------------------------------------------------- |
| 0   | **XOR pair**         | `const _k="f3a1"; const _e="52b3"; → xor(_e, _k)`               |
| 1   | **Char codes**       | `[97, 49, 98, 50, ...].map(c=>String.fromCharCode(c)).join("")` |
| 2   | **Base64**           | `atob("YTFiMmMzZDQ=")`                                          |
| 3   | **Reverse**          | `"4d3c2b1a".split("").reverse().join("")`                       |
| 4   | **Math derivation**  | `[[142,227],[51,102],...].map(p=>(p[0]^p[1]).toString(16)...)`  |
| 5   | **String slice**     | `"ff3ca1b2c3d4e89a".slice(4, 12)`                               |
| 6   | **Split interleave** | Even/odd chars in two vars, recombined                          |
| 7   | **Char shift**       | Characters shifted by N, restored at runtime                    |

### Polymorphism Per Request

Every payload generation produces structurally different code:

- **Variable names**: All randomized (`_kT4mQ`, `_xR2bP`, ...)
- **Section order**: Signal collector sections shuffled
- **Fragment placement**: Fragments scattered between different code sections
- **Encoding selection**: Random method per fragment
- **Decoys**: 12–20 fake nonce-like declarations inserted throughout
- **Assembly function**: Uses randomized variable name

### Why Static Analysis Fails

```
Request 1:                          Request 2:
const _aB3="f3a1";                  const _qW7=[99,57,100,48,...];
const _cD5="52b3";                  ...
... (signal collector A) ...        ... (signal collector D) ...
const _eF7=atob("YTFi...");        const _mN2="4d3c2b1a";
... (signal collector D) ...        ... (signal collector A) ...
const _gH9=[97,49,...];             const _pQ4="ff3c"+"e89a";
... (signal collector B) ...        ... (signal collector C) ...
```

No two payloads share the same structure, variable names, or encoding methods.
Combined with the 30-second TTL, automated extraction is impractical.

## Signal Categories (Complete)

### Detection Signals (flag bots)

| ID     | Category               | Bits  | Description                                                                                                                                                                                                                                          |
| ------ | ---------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `a0`   | Automation Globals     | 24    | `window.callPhantom`, `_phantom`, `__nightmare`, `domAutomation`, `_selenium`, `webdriver`, `__playwright*`, `Cypress`, `Buffer`, `emit`, `spawn`, `HeadlessChrome`, etc.                                                                            |
| `a1`   | Enhanced Automation    | 16    | `navigator.webdriver` descriptor analysis, CDC properties, CDP injection, prototype tampering, DOM attributes, `Function.prototype.toString` nativity                                                                                                |
| `a2`   | Browser Feature Probes | 8     | `chrome` in navigator, `permissions`, `languages`, `connection`, `getBattery`, `bluetooth`, `usb`, `serial`                                                                                                                                          |
| `x`    | Tampering Bitmap       | 12    | Native code checks: `Function.prototype.toString`, `setTimeout`, `setInterval`, `Date.now`, `Math.random`, `Array.prototype.push`, `JSON.stringify`, `Object.keys`, `Promise.resolve`, `Array.from`, `Reflect.get`, `console.log`                    |
| `p0`   | Property Integrity     | 16    | `Object.defineProperty`/`getOwnPropertyDescriptor`/`Reflect.get` nativity, `chrome.csi`/`loadTimes`, `navigator.toString()`, `Symbol.toStringTag`, prototype getter nativity                                                                         |
| `p_ov` | Property Overrides     | count | Direct overrides on `navigator` instance (webdriver, plugins, languages, platform, userAgent)                                                                                                                                                        |
| `p_pi` | Proto Inconsistency    | count | `Object.getPrototypeOf(navigator).constructor.name !== 'Navigator'`                                                                                                                                                                                  |
| `b0`   | SB0: Chromium/Selenium | 15    | CDC keys, `__selenium_*`, PluginArray/MimeTypeArray toString, permissions.query nativity, chrome.runtime analysis, Notification+hidden, speechSynthesis, SwiftShader, Bluetooth API                                                                  |
| `b1`   | SB1: Stealth/Advanced  | 16    | Iframe srcdoc injection, webdriver on instance, error stack frameworks, perf.now identical diffs, Proxy on window, mediaDevices missing, connection.rtt=0, chrome.app missing, document CDC keys, webdriver getter analysis, deviceMemory validation |
| `b2`   | SB2: Undetected-CD     | 15    | Webdriver getter returns undefined, Reflect.get returns undefined, pointer+touch mismatch, Notification nativity, navigation timing zeros, console helpers ($,$0-$4), CDC on window/proto, SharedWorker/BroadcastChannel, USB/Serial/HID API         |
| `cdp`  | CDP Detection          | 1     | Console serialization side-effect (detects Chrome DevTools Protocol)                                                                                                                                                                                 |

### Fingerprint Signals (identify environment)

| ID    | Category           | Fields        | Description                                                                                                                                                                                                 |
| ----- | ------------------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `c0`  | Canvas/WebGL/Audio | bitmap + data | Canvas 2D availability, zero-pixel detection, WebGL renderer, AudioContext sample rate                                                                                                                      |
| `f`   | Features           | 16 bits       | localStorage, sessionStorage, WebSocket, WebGL1/2, WebAssembly, indexedDB, Notification, fetch, Promise, Intl, SharedArrayBuffer, SharedWorker, BroadcastChannel, PerformanceObserver, IntersectionObserver |
| `nav` | Navigator          | struct        | UA, platform, plugins, languages, cookies, DNT, hardwareConcurrency, deviceMemory, connection (rtt, downlink, effectiveType), maxTouchPoints, pdfViewerEnabled, userAgentData, vendor, productSub           |
| `scr` | Screen             | struct        | width, height, availWidth, availHeight, colorDepth, pixelDepth, devicePixelRatio, orientation, isExtended                                                                                                   |
| `eng` | Engine             | struct        | `eval.toString().length` (33=Chrome, 37=Firefox), error stack format (v8/spidermonkey/jsc), `Math.tan(-1e308)`, `Function.prototype.bind` nativity                                                          |
| `mq`  | Media Queries      | struct        | hover, pointer (fine/coarse), any-hover, color-gamut (srgb/p3), prefers-color-scheme, prefers-reduced-motion, prefers-contrast, forced-colors, touch support                                                |
| `vm`  | Voices/Media       | struct        | speechSynthesis voice count, mediaDevices count (audio in/out, video in), WebRTC support                                                                                                                    |
| `gl`  | WebGL Deep         | struct        | Unmasked vendor/renderer, MAX_TEXTURE_SIZE, MAX_VERTEX_ATTRIBS, MAX_VARYING_VECTORS, MAX_RENDERBUFFER_SIZE, extensions count                                                                                |
| `dr`  | DOMRect            | struct        | Emoji rendering dimensions (getBoundingClientRect), TextMetrics (measureText width, ascent, descent)                                                                                                        |
| `ch`  | Client Hints       | struct        | userAgentData presence, mobile flag consistency, platform consistency                                                                                                                                       |

### Behavioral & Environmental Signals

| ID     | Category           | Fields | Description                                                                                                                      |
| ------ | ------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `dt`   | DevTools           | struct | Width/height diff detection, Firebug, console timing, open count, was-open                                                       |
| `env`  | Environment        | struct | Timezone offset + name, touch bitmap, document visibility state, visibility changes, battery (level, charging), online status    |
| `tm`   | Timing             | struct | requestAnimationFrame interval, performance.now() identical-diff detection                                                       |
| `wk`   | Worker Consistency | struct | Compare navigator.userAgent, hardwareConcurrency, platform, languages between main thread and Web Worker — mismatches = spoofing |
| `bhv`  | Behavioral         | struct | Mouse movement count, key presses, scroll events, elapsed time                                                                   |
| `perm` | Permissions        | struct | Notification.permission vs permissions.query({name:'notifications'}) consistency                                                 |
| `perf` | Performance        | struct | JS heap size limit, total/used heap, storage quota/usage                                                                         |

### Server-Side Signals (from request headers)

| Signal                   | Suspicious When |
| ------------------------ | --------------- |
| `Accept` header          | Missing         |
| `Accept-Language` header | Missing         |
| `Accept-Encoding` header | Missing         |

## Scoring

The scorer applies **weighted penalties** to a starting score of 1.0:

```
Score = 1.0 - Σ(penalties)

Penalty weights:
  Automation globals (a0):     0.15 per bit  (max 0.50)
  Enhanced automation (a1):    0.12 per bit  (max 0.50)
  Tampered natives (x):        0.08 per bit  (max 0.40)
  Property integrity (p0):     0.10–0.15 per check
  Bot detection (b0/b1/b2):    0.08 per bit  (max 0.50)
  Navigator anomalies:         0.08–0.15 per check
  Screen anomalies:            0.10–0.15 per check
  Engine mismatch:             0.10–0.15 per check
  Worker mismatch:             0.10–0.20 per field
  Feature inconsistency:       0.15–0.20
  Software renderer:           0.20
```

**Threshold**: Clearance granted if `score ≥ 0.3` (configurable via `SCORE_THRESHOLD` env).

## Quick Start

```bash
cd browser-signals
npm install
npm start
# Open http://localhost:3001
```

## Integration

```javascript
// Client-side: load and execute
const res = await fetch('/signals/init', { method: 'POST' });
const { scriptUrl } = await res.json();

const script = document.createElement('script');
script.src = scriptUrl;
document.head.appendChild(script);

// The script auto-submits. Listen for result:
window.__signals_cb = (result) => {
    if (result.cleared) {
        // Use result.token for authenticated requests
        fetch('/api/data', {
            headers: { Authorization: `Bearer ${result.token}` },
        });
    }
};
```

```javascript
// Server-side: protect endpoints
import { requireClearance } from './server.js';

app.get('/api/data', requireClearance, (req, res) => {
    // req.clearance contains { sub, score, iat, ip }
    res.json({ data: 'protected content' });
});
```

## Security Properties

| Property                   | Mechanism                                                            |
| -------------------------- | -------------------------------------------------------------------- |
| **Anti-replay**            | Single-use nonce, burned after verification                          |
| **Anti-extraction**        | Polymorphic JS, 8 encoding methods, randomized structure, 30s TTL    |
| **Anti-forgery**           | HMAC-SHA256 signature with 256-bit nonce as key                      |
| **Anti-pre-computation**   | Nonce unknown until JS payload fetched; payload unique per challenge |
| **Timing-safe comparison** | `crypto.timingSafeEqual` for all signature checks                    |
| **No-cache enforcement**   | `Cache-Control: no-store` on payload responses                       |
| **Clearance binding**      | Token includes challenge ID, score, timestamp, client IP             |

## Threat Model

| Attacker                                | Capability                   | Outcome                                                                    |
| --------------------------------------- | ---------------------------- | -------------------------------------------------------------------------- |
| **HTTP client** (curl, requests)        | Cannot execute JS            | No signals, no signature → rejected                                        |
| **JSDOM / Node.js**                     | Partial JS, no rendering     | Missing canvas/WebGL/audio, wrong engine fingerprint → low score           |
| **Headless Chrome**                     | Full browser, but detectable | Automation signals (a0/a1/b0/b1/b2) trigger penalties                      |
| **Stealth browser** (puppeteer-stealth) | Hides some signals           | Worker consistency, CDP detection, timing anomalies, deep integrity checks |
| **Replay attacker**                     | Captured valid payload       | Nonce already burned → rejected                                            |
| **Static analysis**                     | Reads JS source              | Polymorphic code + 30s TTL → must reverse-engineer each unique payload     |
| **Real browser via proxy**              | Genuine signals              | High score → cleared (this is the intended use case)                       |

## Configuration

| Env Variable      | Default | Description                               |
| ----------------- | ------- | ----------------------------------------- |
| `PORT`            | 3001    | Server port                               |
| `SIGNALS_SECRET`  | random  | Server secret for clearance token signing |
| `SCORE_THRESHOLD` | 0.3     | Minimum score for clearance               |

## Comparison with `browser-integrity`

| Aspect                 | `browser-integrity`          | `browser-signals`                                                                                                  |
| ---------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Purpose**            | Prove browser can render     | Comprehensive bot detection + anti-replay                                                                          |
| **Protocol**           | Multi-round HMAC chain       | Single-round with nonce-signed signals                                                                             |
| **Anti-replay**        | HMAC chain (sequential)      | Polymorphic nonce hiding (parallel)                                                                                |
| **Signal depth**       | 4 rendering stages           | 22+ signal categories, 150+ individual checks                                                                      |
| **Headless detection** | Canvas/Audio/Pixel rendering | Automation globals, prototype integrity, worker consistency, CDP detection, timing analysis, engine fingerprinting |
| **Time to complete**   | ~200ms (4 rounds)            | ~150ms (1 round)                                                                                                   |
| **Server state**       | Per-stage state              | Single nonce (lighter)                                                                                             |
