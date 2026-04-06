# Browser Integrity Challenge

Browser integrity verification using a multi-round rendering chain protocol. The server controls stage progression via HMAC-chained secrets, preventing signal replay and offline pre-computation.

## Quick Start

```bash
npm install
npm start
# Open http://localhost:3000
```

Set `VIGILUS_SECRET` for persistent token signing (random secret generated at startup otherwise):

```bash
VIGILUS_SECRET=your-secret-here npm start
```

## How It Works

### Protocol Flow

```
Browser                           Server
  │                                 │
  │  POST /challenge                │
  │────────────────────────────────►│ Generate challengeId, baseSeed
  │                                 │ Shuffle stage order via HMAC
  │  { challengeId, totalStages,    │ Compute stage 0 seed:
  │    stage: { index:0, type,      │   HMAC(secret, id:baseSeed:0)
  │             seed, params } }    │
  │◄────────────────────────────────│
  │                                 │
  │  Execute stage 0 (e.g. canvas)  │
  │  Hash rendering output          │
  │                                 │
  │  POST /challenge/:id/solve      │
  │  { stageIndex: 0, hash: H0 }    │
  │────────────────────────────────►│ Validate timing, format, triviality
  │                                 │ If pixel_verify: check hash matches
  │                                 │ Compute stage 1 seed:
  │  { stage: { index:1, ... } }    │   HMAC(secret, id:baseSeed:1:H0)
  │◄────────────────────────────────│
  │                                 │
  │  Execute stage 1 (e.g. audio)   │
  │  Hash rendering output          │
  │                                 │
  │  POST /challenge/:id/solve      │
  │  { stageIndex: 1, hash: H1 }    │
  │────────────────────────────────►│ Validate, compute next seed
  │  { stage: { index:2, ... } }    │   HMAC(secret, id:baseSeed:2:H0:H1)
  │◄────────────────────────────────│
  │                                 │
  │   ... repeat for N stages ...   │
  │                                 │
  │  POST /challenge/:id/solve      │
  │  { stageIndex: N-1, hash: HN }  │
  │────────────────────────────────►│ All stages complete
  │                                 │ Chain proof = HMAC(secret, id:H0|H1|...|HN)
  │  { complete: true,              │ Sign token with chain proof
  │    token, expiresAt }           │
  │◄────────────────────────────────│
  │                                 │
  │  Authorization: Bearer <token>  │
  │────────────────────────────────►│ Verify token signature + expiry
  │  Protected resource             │
  │◄────────────────────────────────│
```

### HMAC Chain Dependency

Each stage's parameters depend on ALL previous stages' results mixed with the server secret:

```
              ┌───────────────┐
              │ Server Secret │
              └──────┬────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │ seed₀ = HMAC(secret, id:base:0)     │
  └──────────────────┬──────────────────┘
                     │
         ┌───────────▼───────────┐
         │  Stage 0: canvas_text │──► H₀ (browser-specific)
         └───────────┬───────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │ seed₁ = HMAC(secret, id:base:1:H₀)  │
  └──────────────────┬──────────────────┘
                     │
         ┌───────────▼───────────┐
         │  Stage 1: audio       │──► H₁ (browser-specific)
         └───────────┬───────────┘
                     │
  ┌──────────────────▼──────────────────────┐
  │ seed₂ = HMAC(secret, id:base:2:H₀:H₁)   │
  └──────────────────┬──────────────────────┘
                     │
         ┌───────────▼────────────────┐
         │  Stage 2: canvas_geometry  │──► H₂ (browser-specific)
         └───────────┬────────────────┘
                     │
  ┌──────────────────▼─────────────────────────┐
  │ seed₃ = HMAC(secret, id:base:3:H₀:H₁:H₂)   │
  └──────────────────┬─────────────────────────┘
                     │
         ┌───────────▼───────────────┐
         │  Stage 3: pixel_verify    │──► H₃ (deterministic, server-verifiable)
         └───────────┬───────────────┘
                     │
  ┌──────────────────▼────────────────────────┐
  │ chainProof = HMAC(secret, id:H₀|H₁|H₂|H₃) │
  └──────────────────┬────────────────────────┘
                     │
              ┌──────▼──────┐
              │    Token    │
              └─────────────┘
```

> Stage order is **shuffled per challenge** via `HMAC(secret, "shuffle:" + challengeId)`, so attackers cannot hardcode the sequence.

## Stages

| Stage             | What it computes                                     | Why it needs a browser                                                    | Server can verify? |
| ----------------- | ---------------------------------------------------- | ------------------------------------------------------------------------- | ------------------ |
| `canvas_text`     | Text + gradients + arcs + bezier curves on Canvas 2D | Font rasterization, anti-aliasing, subpixel rendering are GPU/OS-specific | Format only        |
| `audio`           | Oscillator → compressor via OfflineAudioContext      | DSP pipeline produces browser-specific floating-point samples             | Format only        |
| `canvas_geometry` | Arcs, fills, strokes with seed-derived parameters    | Anti-aliased shape rendering is engine-specific                           | Format only        |
| `pixel_verify`    | Deterministic integer math → SHA-256 (no rendering)  | Pure computation, identical on all platforms                              | **Exact hash**     |

### The pixel_verify Stage

This is the only stage the server can verify exactly. It computes a pixel buffer using pure integer math over the seed bytes:

```
For each pixel (x, y):
  R = seedBytes[x % 32] XOR seedBytes[y % 32]
  G = (seedBytes[(x+y) % 32] * 3) & 0xFF
  B = (seedBytes[|x-y| % 32] * 7) & 0xFF
  A = 255

hash = SHA-256(pixel_buffer)
```

Both server (Node.js `Buffer`) and browser (`Uint8Array`) execute identical math, producing the same hash. Its seed is HMAC-chained to all previous rendering stages, binding the verification to the entire chain.

## Design Rationale

### Problem with v1 (Signal-Based)

The previous system collected browser signals (canvas hash, audio hash, WebGL params, API fingerprint) in a single round-trip. The fundamental flaw:

```
  Attacker captures solver.js once
           │
           ▼
  ┌─────────────────────────────┐
  │ Extract rendering functions │
  │ Run with any new nonce      │
  │ Generate valid proof        │
  └─────────────────────────────┘
           │
           ▼
  Unlimited valid tokens without a browser
```

Signals are just deterministic functions of the nonce. Once you have the function, you don't need the browser.

### Why Multi-Round Fixes This

```
  Attacker has solver.js code
           │
           ▼
  ┌─────────────────────────────────────┐
  │ Can see stage computation logic     │
  │ BUT cannot compute stage N+1 seed   │
  │ without server response to stage N  │
  │                                     │
  │ Server response requires:           │
  │   HMAC(SERVER_SECRET, prev_hashes)  │
  │                                     │
  │ SERVER_SECRET is never exposed      │
  └─────────────────────────────────────┘
           │
           ▼
  Must interact with server sequentially
  Must compute each stage in real-time
  Cannot pre-compute or batch
```

### Approaches Considered and Rejected

| Approach                                               | Why rejected                                                                                                                |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| **Proof of Work** (hash puzzle)                        | User requirement: not a PoW system. Also penalizes legitimate users on slow devices                                         |
| **Server-side rendering** (node-canvas)                | Different rendering engine (Cairo vs Skia/Gecko) produces different hashes. Can't match browser output for verification     |
| **Zero-knowledge proofs**                              | Impractical complexity. Would need a ZK circuit for canvas rendering — doesn't exist                                        |
| **Steganography** (server embeds secrets in images)    | Attacker can decode PNG data URLs without rendering. Browser color management is too inconsistent for reliable verification |
| **DOM measurement challenges** (getBoundingClientRect) | Values vary with viewport, zoom, DPI. Too fragile for verification                                                          |
| **WebGL shader computation**                           | Strong in theory but requires GPU; many privacy browsers disable WebGL                                                      |
| **Single-round with better signals**                   | Fundamentally broken — any deterministic function of a nonce can be replayed without the original execution environment     |

### The Fundamental Impossibility

**A server without a rendering engine cannot verify exact rendering output.** This is why:

- `canvas_text`, `audio`, and `canvas_geometry` stages are validated for format/timing only
- `pixel_verify` is the only exactly-verifiable stage (because it's pure math, not rendering)
- The chain binding (`HMAC(secret, all_hashes)`) is what ties everything together

The security doesn't come from verifying individual rendering outputs. It comes from **forcing sequential server interaction with secret mixing** — making offline solving impossible.

## Threat Model

| Attacker                            | Blocked?        | Mechanism                                                            |
| ----------------------------------- | --------------- | -------------------------------------------------------------------- |
| HTTP client (curl, Python requests) | **Blocked**     | No JavaScript — can't compute any stage                              |
| Node.js / Deno                      | **Blocked**     | No Canvas 2D, OfflineAudioContext APIs                               |
| JSDOM / happy-dom                   | **Blocked**     | Stubbed canvas returns zero pixels → trivial hash rejected           |
| Signal replay                       | **Blocked**     | Each stage seed depends on HMAC(server_secret, ...) — can't reuse    |
| Pre-computation                     | **Blocked**     | Stage N+1 params unknown until stage N hash submitted to server      |
| Source code exposure                | **Blocked**     | Security from server secret + protocol structure, not obscurity      |
| Headless Chrome (Puppeteer)         | **Cost raised** | Requires full browser instance per challenge, sequential round-trips |

### Headless Chrome Note

Puppeteer/Playwright with real Chromium can still solve the challenge — they run complete browser engines. This is a **fundamental limitation** of any browser-based challenge system. The defense is economic:

- Each challenge requires 4+ sequential HTTP round-trips (can't batch)
- Each round-trip requires real rendering computation (can't skip)
- Per-challenge cost: full browser instance + ~500ms wall time
- Combine with rate limiting and behavioral analysis for defense in depth

## Integration

### Protect a Server Endpoint

```javascript
import { verifyToken } from './server.js';

app.get('/api/data', verifyToken, (req, res) => {
    res.json({ sensitive: 'data' });
});
```

### Solve from a Client Page

```html
<script type="module">
    import { solveChallenge } from '/solver.js';

    const { token } = await solveChallenge();

    const response = await fetch('/api/data', {
        headers: { Authorization: `Bearer ${token}` },
    });
</script>
```

### With Progress Tracking

```javascript
const result = await solveChallenge({
    onProgress(stage, total) {
        console.log(`Solving stage ${stage}/${total}...`);
    },
});
```

## Production Considerations

- **HTTPS required** — `crypto.subtle` is only available in secure contexts
- **Rate limiting** — add to `POST /challenge` to prevent nonce flooding
- **Persistent storage** — replace the in-memory `Map` with Redis for multi-instance deployments
- **Token TTL** — default 1 hour, configurable via `TOKEN_TTL_MS`
- **Challenge TTL** — default 2 minutes for the full multi-stage challenge
- **Stage min time** — default 5ms floor; adjust `STAGE_MIN_MS` based on expected network latency
