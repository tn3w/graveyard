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
const MIN_SOLVE_MS = 50;
const SPACE_COST = parseInt(process.env.POW_SPACE_COST || '512', 10);
const TIME_COST = parseInt(process.env.POW_TIME_COST || '1', 10);
const DELTA = 3;
const DIFFICULTY = parseInt(process.env.POW_DIFFICULTY || '10', 10);

const challenges = new Map();

setInterval(() => {
    const now = Date.now();
    for (const [id, challenge] of challenges) {
        if (now > challenge.expiresAt) {
            challenges.delete(id);
        }
    }
}, 60_000);

app.use(express.json({ limit: '4kb' }));
app.use(express.static(join(__dirname, 'public')));

function hmac(data) {
    return crypto.createHmac('sha256', SERVER_SECRET).update(data).digest('hex');
}

function countLeadingZeroBits(hexHash) {
    for (let i = 0; i < hexHash.length; i++) {
        const nibble = parseInt(hexHash[i], 16);
        if (nibble === 0) continue;
        return i * 4 + Math.clz32(nibble) - 28;
    }
    return hexHash.length * 4;
}

function balloonHash(input, spaceCost, timeCost, delta) {
    const buf = Buffer.alloc(spaceCost * 32);
    const cntBuf = Buffer.alloc(4);
    const paramBuf = Buffer.alloc(16);
    let cnt = 0;

    function hashWithCounter(...data) {
        cntBuf.writeUInt32LE(cnt++);
        const h = crypto.createHash('sha256');
        h.update(cntBuf);
        for (const d of data) h.update(d);
        return h.digest();
    }

    function block(i) {
        return buf.subarray(i * 32, (i + 1) * 32);
    }

    hashWithCounter(Buffer.from(input)).copy(buf, 0);

    for (let i = 1; i < spaceCost; i++) {
        hashWithCounter(block(i - 1)).copy(buf, i * 32);
    }

    for (let t = 0; t < timeCost; t++) {
        for (let i = 0; i < spaceCost; i++) {
            const prev = (i || spaceCost) - 1;
            hashWithCounter(block(prev), block(i)).copy(buf, i * 32);

            for (let j = 0; j < delta; j++) {
                paramBuf.writeUInt32LE(cnt++, 0);
                paramBuf.writeUInt32LE(t, 4);
                paramBuf.writeUInt32LE(i, 8);
                paramBuf.writeUInt32LE(j, 12);
                const idx = crypto.createHash('sha256').update(paramBuf).digest();
                const other = idx.readUInt32BE(0) % spaceCost;

                hashWithCounter(block(i), block(other)).copy(buf, i * 32);
            }
        }
    }

    return block(spaceCost - 1).toString('hex');
}

app.post('/challenge', (_req, res) => {
    const id = crypto.randomUUID();
    const salt = crypto.randomBytes(32).toString('hex');
    const prefix = hmac(`${id}:${salt}`);

    challenges.set(id, {
        prefix,
        difficulty: DIFFICULTY,
        spaceCost: SPACE_COST,
        timeCost: TIME_COST,
        createdAt: Date.now(),
        expiresAt: Date.now() + CHALLENGE_TTL_MS,
    });

    res.json({
        challengeId: id,
        prefix,
        difficulty: DIFFICULTY,
        spaceCost: SPACE_COST,
        timeCost: TIME_COST,
        delta: DELTA,
    });
});

app.post('/challenge/:id/solve', (req, res) => {
    const challenge = challenges.get(req.params.id);

    if (!challenge) {
        return res.status(400).json({
            error: 'Unknown challenge',
        });
    }

    if (Date.now() > challenge.expiresAt) {
        challenges.delete(req.params.id);
        return res.status(400).json({
            error: 'Challenge expired',
        });
    }

    if (Date.now() - challenge.createdAt < MIN_SOLVE_MS) {
        return res.status(400).json({
            error: 'Too fast',
        });
    }

    const { nonce } = req.body;

    if (typeof nonce !== 'number' || !Number.isInteger(nonce) || nonce < 0) {
        return res.status(400).json({
            error: 'Invalid nonce',
        });
    }

    const hash = balloonHash(
        challenge.prefix + nonce.toString(),
        challenge.spaceCost,
        challenge.timeCost,
        DELTA
    );

    if (countLeadingZeroBits(hash) < challenge.difficulty) {
        return res.status(400).json({
            error: 'Insufficient proof of work',
        });
    }

    challenges.delete(req.params.id);

    const proof = hmac(`${req.params.id}:${nonce}:${hash}`);
    const token = signToken({
        sub: req.params.id,
        proof,
        iat: Date.now(),
    });

    res.json({ token, expiresAt: Date.now() + TOKEN_TTL_MS });
});

function signToken(payload) {
    const raw = JSON.stringify(payload);
    const encoded = Buffer.from(raw).toString('base64url');
    const signature = crypto.createHmac('sha256', SERVER_SECRET).update(raw).digest('base64url');
    return `${encoded}.${signature}`;
}

function verifyToken(req, res, next) {
    const header = req.headers.authorization;

    if (!header?.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'No token' });
    }

    const parts = header.slice(7).split('.');

    if (parts.length !== 2) {
        return res.status(401).json({
            error: 'Malformed token',
        });
    }

    const [encoded, signature] = parts;
    const raw = Buffer.from(encoded, 'base64url').toString();
    const expected = crypto.createHmac('sha256', SERVER_SECRET).update(raw).digest('base64url');

    const sigBuf = Buffer.from(signature, 'base64url');
    const expBuf = Buffer.from(expected, 'base64url');

    if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) {
        return res.status(401).json({
            error: 'Invalid token',
        });
    }

    const payload = JSON.parse(raw);

    if (Date.now() > payload.iat + TOKEN_TTL_MS) {
        return res.status(401).json({
            error: 'Token expired',
        });
    }

    req.challengeAuth = payload;
    next();
}

app.get('/protected', verifyToken, (req, res) => {
    res.json({
        message: 'Access granted — PoW verified',
        auth: req.challengeAuth,
    });
});

app.listen(PORT, () => {
    console.log(`Vigilus PoW running on http://localhost:${PORT}`);
});
