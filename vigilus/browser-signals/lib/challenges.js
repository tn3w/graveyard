import crypto from 'crypto';

// In-memory challenge store with TTL and single-use enforcement.
// Each challenge binds a nonce to a challenge ID with expiry.

const CHALLENGE_TTL_MS = 30_000; // 30s — nonce must be used quickly
const CLEARANCE_TTL_MS = 3_600_000; // 1h clearance validity
const MAX_CHALLENGES = 10_000;

const challenges = new Map();
const usedNonces = new Set(); // Prevent nonce reuse across restarts within window

// Periodic cleanup
setInterval(() => {
    const now = Date.now();
    for (const [id, c] of challenges) {
        if (now > c.expiresAt) challenges.delete(id);
    }
    // Trim used nonces older than 2x TTL (they can't be replayed anyway)
    if (usedNonces.size > MAX_CHALLENGES * 2) usedNonces.clear();
}, 15_000);

export function createChallenge() {
    if (challenges.size >= MAX_CHALLENGES) {
        // Evict oldest
        const oldest = challenges.keys().next().value;
        challenges.delete(oldest);
    }

    const id = crypto.randomUUID();
    const nonce = crypto.randomBytes(32).toString('hex'); // 64 hex chars
    const createdAt = Date.now();

    challenges.set(id, {
        nonce,
        createdAt,
        expiresAt: createdAt + CHALLENGE_TTL_MS,
        used: false,
    });

    return { id, nonce, createdAt };
}

export function validateChallenge(challengeId) {
    const challenge = challenges.get(challengeId);
    if (!challenge) return { valid: false, error: 'Unknown challenge' };
    if (challenge.used) return { valid: false, error: 'Challenge already used' };
    if (Date.now() > challenge.expiresAt) {
        challenges.delete(challengeId);
        return { valid: false, error: 'Challenge expired' };
    }
    return { valid: true, challenge };
}

export function consumeChallenge(challengeId) {
    const challenge = challenges.get(challengeId);
    if (!challenge) return null;
    challenge.used = true;
    usedNonces.add(challenge.nonce);
    challenges.delete(challengeId);
    return challenge;
}

export function isNonceReused(nonce) {
    return usedNonces.has(nonce);
}

export function verifySignature(nonce, message, signature) {
    const expected = crypto
        .createHmac('sha256', Buffer.from(nonce, 'hex'))
        .update(message)
        .digest('hex');
    try {
        return crypto.timingSafeEqual(Buffer.from(expected, 'hex'), Buffer.from(signature, 'hex'));
    } catch {
        return false;
    }
}

// --- Clearance Tokens ---

const SERVER_SECRET = process.env.SIGNALS_SECRET || crypto.randomBytes(32).toString('hex');

export function signClearance(payload) {
    const str = JSON.stringify(payload);
    const encoded = Buffer.from(str).toString('base64url');
    const sig = crypto.createHmac('sha256', SERVER_SECRET).update(str).digest('base64url');
    return `${encoded}.${sig}`;
}

export function verifyClearance(token) {
    const parts = token.split('.');
    if (parts.length !== 2) return null;
    const [encoded, sig] = parts;
    let str;
    try {
        str = Buffer.from(encoded, 'base64url').toString();
    } catch {
        return null;
    }
    const expected = crypto.createHmac('sha256', SERVER_SECRET).update(str).digest('base64url');
    const sigBuf = Buffer.from(sig, 'base64url');
    const expBuf = Buffer.from(expected, 'base64url');
    if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) return null;
    const payload = JSON.parse(str);
    if (Date.now() > payload.iat + CLEARANCE_TTL_MS) return null;
    return payload;
}

export { CHALLENGE_TTL_MS, CLEARANCE_TTL_MS };
