# PoW Challenge

Memory-hard Balloon Hashing Proof of Work. Each PoW attempt requires allocating and filling a memory buffer, making GPU/ASIC parallelization impractical. Browsers solve via multi-worker mining.

## Quick Start

```bash
npm install
npm start
# Open http://localhost:3000
```

```bash
VIGILUS_SECRET=your-secret POW_SPACE_COST=512 POW_DIFFICULTY=8 npm start
```

## How It Works

### Protocol Flow

```
Client (N workers)                          Server
  │                                           │
  │  POST /challenge                          │
  │──────────────────────────────────────────►│ prefix = HMAC(secret, id:salt)
  │  { challengeId, prefix, difficulty,       │
  │    spaceCost, timeCost, delta }           │
  │◄──────────────────────────────────────────│
  │                                           │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
  │  │ Worker 0 │ │ Worker 1 │ │ Worker N │   │
  │  │ nonce: 0 │ │ nonce: 1 │ │ nonce: N │   │
  │  │ step: +N │ │ step: +N │ │ step: +N │   │
  │  └────┬─────┘ └────┬─────┘ └────┬─────┘   │
  │       │            │            │         │
  │       │ Balloon(prefix + nonce,           │
  │       │   spaceCost, timeCost, delta)     │
  │       │ until leading_zeros >= difficulty │
  │       │            │            │         │
  │      ◄── first solution found ──►         │
  │                                           │
  │  POST /challenge/:id/solve                │
  │  { nonce }                                │
  │──────────────────────────────────────────►│ Recompute Balloon hash
  │                                           │ Verify leading_zeros >= diff
  │  { token, expiresAt }                     │
  │◄──────────────────────────────────────────│
```

### Balloon Hashing

Each PoW attempt runs the Balloon hash function (Boneh, Corrigan-Gibbs, Schechter 2016) using SHA-256 as the building block:

1. **Expand**: Fill `spaceCost` blocks with chained SHA-256 hashes
2. **Mix**: For `timeCost` rounds, mix each block with its predecessor and `delta` pseudorandom other blocks
3. **Check**: Test if the final block has enough leading zero bits

Memory per attempt: `spaceCost × 32` bytes. With `spaceCost=512`: 16KB per hash attempt, per worker.

### Why Balloon over SHA-256

SHA-256 is fast and cheap — an attacker with GPUs or ASICs can solve many challenges in parallel with minimal memory overhead. Balloon hashing requires a configurable amount of RAM per hash, making mass-parallelization on specialized hardware impractical.

### Configuration

| Env Var          | Default | Effect                                |
| ---------------- | ------- | ------------------------------------- |
| `POW_SPACE_COST` | 512     | Blocks per hash (memory = N×32 bytes) |
| `POW_TIME_COST`  | 1       | Mixing rounds                         |
| `POW_DIFFICULTY` | 9       | Leading zero bits required            |

Each additional difficulty bit doubles expected attempts. Higher `spaceCost` increases memory requirement per attempt.

### Security Properties

- **Memory-hard**: Each hash attempt allocates `spaceCost × 32` bytes — resists GPU/ASIC parallelization
- **HMAC-bound prefixes**: Cannot be predicted without server secret
- **Single-use challenges**: Deleted after solve or expiry
- **Minimum solve time**: Rejects solutions under 50ms
- **Timing-safe token verification**: Constant-time comparison
- **Challenge TTL**: 120s expiry prevents stockpiling
