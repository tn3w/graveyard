import express from 'express';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import {
    createChallenge,
    validateChallenge,
    consumeChallenge,
    verifySignature,
    signClearance,
    verifyClearance,
    CHALLENGE_TTL_MS,
} from './lib/challenges.js';
import { generatePayload } from './lib/payload.js';
import { scoreSignals } from './lib/scorer.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json({ limit: '64kb' }));
app.use(express.static(join(__dirname, 'public')));

// ── Phase 1: Initialize Challenge ──
// Returns a challenge ID and the URL to fetch the polymorphic JS payload.
// The nonce is generated server-side and never sent directly to the client.

app.post('/signals/init', (req, res) => {
    const { id, nonce, createdAt } = createChallenge();

    // Pre-generate the payload so it's ready when requested
    const payload = generatePayload(id, nonce, '');
    payloadCache.set(id, { payload, expiresAt: createdAt + CHALLENGE_TTL_MS });

    res.json({
        challengeId: id,
        scriptUrl: `/signals/payload/${id}.js`,
        ttl: CHALLENGE_TTL_MS,
    });
});

// Payload cache (challenge ID → generated JS)
const payloadCache = new Map();
setInterval(() => {
    const now = Date.now();
    for (const [id, p] of payloadCache) {
        if (now > p.expiresAt) payloadCache.delete(id);
    }
}, 15_000);

// ── Phase 2: Serve Polymorphic JS Payload ──
// Each challenge ID gets a unique, one-time JS file with the nonce hidden inside.
// Content-Type is application/javascript; served with no-cache headers.

app.get('/signals/payload/:id.js', (req, res) => {
    const cached = payloadCache.get(req.params.id);
    if (!cached) return res.status(404).send('// expired or unknown');

    const { valid, error } = validateChallenge(req.params.id);
    if (!valid) {
        payloadCache.delete(req.params.id);
        return res.status(410).send(`// ${error}`);
    }

    res.set({
        'Content-Type': 'application/javascript; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'X-Content-Type-Options': 'nosniff',
    });
    res.send(cached.payload);
});

// ── Phase 3: Verify Signed Signals ──
// Client submits: { cid, s (signals), ts (timestamp), sig (HMAC signature) }
// Server verifies: challenge exists, not expired, not reused, signature matches, scores signals.

app.post('/signals/verify', (req, res) => {
    const { cid, s, ts, sig } = req.body;

    if (!cid || !s || !ts || !sig) {
        return res.status(400).json({ error: 'Missing fields' });
    }

    // Validate challenge
    const { valid, error, challenge } = validateChallenge(cid);
    if (!valid) return res.status(400).json({ error });

    // Timestamp freshness: must be within challenge window
    const now = Date.now();
    if (Math.abs(now - ts) > CHALLENGE_TTL_MS) {
        return res.status(400).json({ error: 'Timestamp out of range' });
    }

    // Reconstruct the signed message and verify
    const payload = JSON.stringify(s);
    const message = `${cid}:${ts}:${payload}`;

    if (!verifySignature(challenge.nonce, message, sig)) {
        consumeChallenge(cid); // Burn the challenge on failed attempt
        payloadCache.delete(cid);
        return res.status(403).json({ error: 'Invalid signature' });
    }

    // Consume the challenge (single-use)
    consumeChallenge(cid);
    payloadCache.delete(cid);

    // Score the signals
    const { score, flags } = scoreSignals(s, req.headers);

    // Issue clearance token if score is acceptable
    const SCORE_THRESHOLD = parseFloat(process.env.SCORE_THRESHOLD || '0.3');

    if (score >= SCORE_THRESHOLD) {
        const token = signClearance({
            sub: cid,
            score,
            iat: now,
            ip: req.ip,
        });
        return res.json({
            cleared: true,
            score,
            token,
            flags: flags.length > 0 ? flags : undefined,
        });
    }

    res.json({
        cleared: false,
        score,
        flags,
    });
});

// ── Clearance Verification Middleware ──
// Protected endpoints use this to verify clearance tokens.

export function requireClearance(req, res, next) {
    const header = req.headers.authorization;
    if (!header?.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'No clearance token' });
    }

    const payload = verifyClearance(header.slice(7));
    if (!payload) return res.status(401).json({ error: 'Invalid or expired clearance' });

    req.clearance = payload;
    next();
}

// ── Test Endpoint ──

app.get('/protected', requireClearance, (req, res) => {
    res.json({
        message: 'Access granted — browser signals verified',
        clearance: req.clearance,
    });
});

app.listen(PORT, () => {
    console.log(`Browser Signals running on http://localhost:${PORT}`);
});
