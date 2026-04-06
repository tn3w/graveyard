import crypto from 'node:crypto';

const challenges = new Map();
const MAX_CHALLENGES = 5000;
const CHALLENGE_TTL = 60_000;
const TOKEN_TTL = 3_600_000;

const SECRET = process.env.INTERACTIONS_SECRET || crypto.randomBytes(32).toString('hex');

export function createChallenge() {
    if (challenges.size >= MAX_CHALLENGES) pruneExpired();

    const id = crypto.randomUUID();
    const nonce = crypto.randomBytes(32).toString('hex');
    const created = Date.now();

    challenges.set(id, { nonce, created, used: false });

    return { challengeId: id, nonce, ttl: CHALLENGE_TTL };
}

export function getChallenge(id) {
    const ch = challenges.get(id);
    if (!ch) return null;
    if (Date.now() - ch.created > CHALLENGE_TTL) {
        challenges.delete(id);
        return null;
    }
    return ch;
}

export function consumeChallenge(id) {
    const ch = getChallenge(id);
    if (!ch || ch.used) return null;
    ch.used = true;
    return ch;
}

export function signToken(payload) {
    const data = Buffer.from(JSON.stringify(payload)).toString('base64url');
    const sig = crypto.createHmac('sha256', SECRET).update(data).digest('hex');
    return `${data}.${sig}`;
}

export function verifyToken(token) {
    const [data, sig] = token.split('.');
    if (!data || !sig) return null;
    const expected = crypto.createHmac('sha256', SECRET).update(data).digest('hex');
    if (!crypto.timingSafeEqual(Buffer.from(sig, 'hex'), Buffer.from(expected, 'hex'))) return null;
    try {
        const payload = JSON.parse(Buffer.from(data, 'base64url').toString());
        if (Date.now() - payload.iat > TOKEN_TTL) return null;
        return payload;
    } catch {
        return null;
    }
}

export function verifyHmac(nonce, message, signature) {
    const expected = crypto.createHmac('sha256', nonce).update(message).digest('hex');
    try {
        return crypto.timingSafeEqual(Buffer.from(signature, 'hex'), Buffer.from(expected, 'hex'));
    } catch {
        return false;
    }
}

function pruneExpired() {
    const now = Date.now();
    for (const [id, ch] of challenges) {
        if (now - ch.created > CHALLENGE_TTL) challenges.delete(id);
    }
}

setInterval(pruneExpired, 30_000);
