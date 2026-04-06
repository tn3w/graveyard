import express from 'express';
import {
    createChallenge,
    getChallenge,
    consumeChallenge,
    verifyHmac,
    signToken,
    verifyToken,
} from './lib/challenges.js';
import { generatePayload } from './lib/payload.js';
import { analyze } from './lib/analyzer.js';

const app = express();
app.use(express.json({ limit: '512kb' }));
app.use(express.static('public'));

const PORT = process.env.PORT || 3002;
const SCORE_THRESHOLD = parseFloat(process.env.SCORE_THRESHOLD || '0.5');

// ── Challenge Init ──────────────────────────────────────────────────────────

app.post('/interactions/init', (req, res) => {
    const challenge = createChallenge();
    res.json({
        challengeId: challenge.challengeId,
        scriptUrl: `/interactions/probe/${challenge.challengeId}.js`,
        ttl: challenge.ttl,
    });
});

// ── Serve Collector Script ──────────────────────────────────────────────────

const payloadCache = new Map();

app.get('/interactions/probe/:id.js', (req, res) => {
    const id = req.params.id;
    const challenge = getChallenge(id);

    if (!challenge) {
        return res.status(404).send('// expired');
    }

    if (!payloadCache.has(id)) {
        const origin = `${req.protocol}://${req.get('host')}`;
        payloadCache.set(id, generatePayload(id, challenge.nonce, origin));
        setTimeout(() => payloadCache.delete(id), 65_000);
    }

    res.set({
        'Content-Type': 'application/javascript; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'X-Content-Type-Options': 'nosniff',
    });
    res.send(payloadCache.get(id));
});

// ── Verify Interactions ─────────────────────────────────────────────────────

app.post('/interactions/verify', (req, res) => {
    const { cid, d, ts } = req.body;
    const signature = req.headers['x-signature'];

    if (!cid || !d || !ts || !signature) {
        return res.status(400).json({ cleared: false, error: 'Missing fields' });
    }

    // Verify challenge exists and is unused
    const challenge = consumeChallenge(cid);
    if (!challenge) {
        return res.status(400).json({ cleared: false, error: 'Invalid or expired challenge' });
    }

    // Verify timestamp freshness (30s window)
    if (Math.abs(Date.now() - ts) > 30_000) {
        return res.status(400).json({ cleared: false, error: 'Stale request' });
    }

    // Verify HMAC signature
    const body = JSON.stringify(req.body);
    if (!verifyHmac(challenge.nonce, body, signature)) {
        return res.status(400).json({ cleared: false, error: 'Invalid signature' });
    }

    // Run analysis
    const analysis = analyze(d);
    const cleared = analysis.score >= SCORE_THRESHOLD;

    const response = {
        cleared,
        score: analysis.score,
    };

    if (cleared) {
        response.token = signToken({
            sub: cid,
            score: analysis.score,
            iat: Date.now(),
            ip: req.ip,
        });
    }

    // Include analysis details in debug mode
    if (process.env.DEBUG_ANALYSIS) {
        response.analysis = analysis;
    }

    // Always include flags (reasons) for transparency
    response.flags = analysis.reasons;

    res.json(response);
});

// ── Token Verification (for backend consumers) ─────────────────────────────

app.post('/interactions/validate-token', (req, res) => {
    const { token } = req.body;
    if (!token) return res.status(400).json({ valid: false });

    const payload = verifyToken(token);
    if (!payload) return res.status(401).json({ valid: false });

    res.json({ valid: true, score: payload.score, issued: payload.iat });
});

// ── Test Protected Endpoint ─────────────────────────────────────────────────

app.get('/protected', (req, res) => {
    const auth = req.headers.authorization;
    if (!auth?.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Token required' });
    }

    const payload = verifyToken(auth.slice(7));
    if (!payload) return res.status(401).json({ error: 'Invalid token' });

    res.json({
        message: 'Access granted',
        score: payload.score,
        issued: new Date(payload.iat).toISOString(),
    });
});

// ── Start ───────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
    console.log(`[user-interactions] http://localhost:${PORT}`);
    console.log(`  Score threshold: ${SCORE_THRESHOLD}`);
    if (process.env.DEBUG_ANALYSIS) console.log('  Debug analysis: enabled');
});
