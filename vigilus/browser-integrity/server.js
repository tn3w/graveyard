import express from 'express';
import crypto from 'crypto';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;

const SERVER_SECRET = process.env.VIGILUS_SECRET || crypto.randomBytes(32).toString('hex');

const CHALLENGE_TTL_MS = 120_000;
const TOKEN_TTL_MS = 3_600_000;
const STAGE_MIN_MS = 5;
const CANVAS_W = 280;
const CANVAS_H = 80;

// Stage types shuffled per challenge. "pixel_verify" is the only stage
// the server can verify exactly (deterministic math, no rendering).
// The other stages require browser rendering engines and produce
// browser-specific hashes that the server validates for format/timing.
const STAGE_TYPES = ['canvas_text', 'audio', 'canvas_geometry', 'pixel_verify'];

const challenges = new Map();

setInterval(() => {
    const now = Date.now();
    for (const [id, c] of challenges) {
        if (now > c.expiresAt) challenges.delete(id);
    }
}, 60_000);

app.use(express.json({ limit: '16kb' }));
app.use(express.static(join(__dirname, 'public')));

// --- Helpers ---

function hmac(data) {
    return crypto.createHmac('sha256', SERVER_SECRET).update(data).digest('hex');
}

function timingSafeHexEqual(a, b) {
    try {
        return crypto.timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex'));
    } catch {
        return false;
    }
}

// Each stage's seed depends on the server secret, challenge ID, base seed,
// stage index, and ALL previous stage hashes. This creates a chain where
// each stage's parameters can only be computed after the previous stage
// is submitted to the server — preventing pre-computation.
function computeStageSeed(challengeId, baseSeed, stageIndex, previousHashes) {
    return hmac([challengeId, baseSeed, stageIndex, ...previousHashes].join(':'));
}

// Shuffle stage order per challenge so attackers can't hardcode the sequence.
function shuffleStages(challengeId) {
    const seed = hmac(`shuffle:${challengeId}`);
    const arr = [...STAGE_TYPES];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = parseInt(seed.slice(i * 2, i * 2 + 2), 16) % (i + 1);
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

// --- Stage Parameter Generation ---

function buildStageParams(type, seed) {
    switch (type) {
        case 'canvas_text':
        case 'canvas_geometry':
        case 'pixel_verify':
            return { type, seed, width: CANVAS_W, height: CANVAS_H };
        case 'audio':
            return {
                type,
                seed,
                frequency: 200 + (parseInt(seed.slice(0, 4), 16) % 800),
                sampleRate: 44100,
                sliceStart: 4500,
                sliceEnd: 5000,
            };
        default:
            return { type, seed };
    }
}

// --- Deterministic Pixel Verification ---
// Computes a pixel pattern using only integer math (no rendering).
// Both server and browser execute the same computation, so the server
// can verify the hash exactly. The seed comes from HMAC chaining,
// binding this verification to all previous rendering stages.

function computePixelVerifyHash(seed) {
    const seedBytes = Buffer.from(seed, 'hex');
    const si = seedBytes.length;
    const data = Buffer.alloc(CANVAS_W * CANVAS_H * 4);

    for (let i = 0; i < CANVAS_W * CANVAS_H; i++) {
        const x = i % CANVAS_W;
        const y = Math.floor(i / CANVAS_W);
        data[i * 4] = (seedBytes[x % si] ^ seedBytes[y % si]) & 0xff;
        data[i * 4 + 1] = (seedBytes[(x + y) % si] * 3) & 0xff;
        data[i * 4 + 2] = (seedBytes[Math.abs(x - y) % si] * 7) & 0xff;
        data[i * 4 + 3] = 255;
    }

    return crypto.createHash('sha256').update(data).digest('hex');
}

// --- Challenge Protocol ---
// Multi-stage: POST /challenge → init, POST /challenge/:id/solve → next stage or token.
// Each stage must be solved sequentially; the server controls progression
// and mixes in its secret between stages.

app.post('/challenge', (req, res) => {
    const id = crypto.randomUUID();
    const baseSeed = crypto.randomBytes(32).toString('hex');
    const stages = shuffleStages(id);
    const firstSeed = computeStageSeed(id, baseSeed, 0, []);

    challenges.set(id, {
        baseSeed,
        stages,
        currentStage: 0,
        stageStartedAt: Date.now(),
        stageHashes: [],
        expiresAt: Date.now() + CHALLENGE_TTL_MS,
    });

    res.json({
        challengeId: id,
        totalStages: stages.length,
        stage: { index: 0, ...buildStageParams(stages[0], firstSeed) },
    });
});

app.post('/challenge/:id/solve', (req, res) => {
    const challenge = challenges.get(req.params.id);
    if (!challenge) return res.status(400).json({ error: 'Unknown challenge' });

    if (Date.now() > challenge.expiresAt) {
        challenges.delete(req.params.id);
        return res.status(400).json({ error: 'Challenge expired' });
    }

    const { stageIndex, hash } = req.body;

    if (stageIndex !== challenge.currentStage)
        return res.status(400).json({ error: 'Wrong stage' });

    if (Date.now() - challenge.stageStartedAt < STAGE_MIN_MS)
        return res.status(400).json({ error: 'Too fast' });

    if (typeof hash !== 'string' || !/^[0-9a-f]{64}$/.test(hash))
        return res.status(400).json({ error: 'Invalid hash' });

    if (/^(.)\1+$/.test(hash)) return res.status(400).json({ error: 'Trivial hash' });

    // Server-verifiable stage: pixel_verify hash must match exactly
    if (challenge.stages[stageIndex] === 'pixel_verify') {
        const seed = computeStageSeed(
            req.params.id,
            challenge.baseSeed,
            stageIndex,
            challenge.stageHashes
        );
        const expected = computePixelVerifyHash(seed);
        if (!timingSafeHexEqual(hash, expected)) {
            challenges.delete(req.params.id);
            return res.status(400).json({ error: 'Pixel verification failed' });
        }
    }

    challenge.stageHashes.push(hash);
    challenge.currentStage++;
    challenge.stageStartedAt = Date.now();

    // All stages complete — issue token
    if (challenge.currentStage >= challenge.stages.length) {
        challenges.delete(req.params.id);
        const chainProof = hmac(`${req.params.id}:${challenge.stageHashes.join('|')}`);
        const token = signToken({ sub: req.params.id, chain: chainProof, iat: Date.now() });
        return res.json({ complete: true, token, expiresAt: Date.now() + TOKEN_TTL_MS });
    }

    // Send next stage
    const nextSeed = computeStageSeed(
        req.params.id,
        challenge.baseSeed,
        challenge.currentStage,
        challenge.stageHashes
    );
    const nextType = challenge.stages[challenge.currentStage];

    res.json({
        complete: false,
        stage: { index: challenge.currentStage, ...buildStageParams(nextType, nextSeed) },
    });
});

// --- Token ---

function signToken(payload) {
    const str = JSON.stringify(payload);
    const encoded = Buffer.from(str).toString('base64url');
    const sig = crypto.createHmac('sha256', SERVER_SECRET).update(str).digest('base64url');
    return `${encoded}.${sig}`;
}

export function verifyToken(req, res, next) {
    const header = req.headers.authorization;
    if (!header?.startsWith('Bearer ')) return res.status(401).json({ error: 'No token' });

    const parts = header.slice(7).split('.');
    if (parts.length !== 2) return res.status(401).json({ error: 'Malformed token' });

    const [encoded, sig] = parts;
    const str = Buffer.from(encoded, 'base64url').toString();
    const expected = crypto.createHmac('sha256', SERVER_SECRET).update(str).digest('base64url');

    const sigBuf = Buffer.from(sig, 'base64url');
    const expBuf = Buffer.from(expected, 'base64url');

    if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf))
        return res.status(401).json({ error: 'Invalid token' });

    const payload = JSON.parse(str);
    if (Date.now() > payload.iat + TOKEN_TTL_MS)
        return res.status(401).json({ error: 'Token expired' });

    req.challengeAuth = payload;
    next();
}

app.get('/protected', verifyToken, (req, res) => {
    res.json({
        message: 'Access granted — browser integrity verified',
        auth: req.challengeAuth,
    });
});

app.listen(PORT, () => {
    console.log(`Vigilus running on http://localhost:${PORT}`);
});
