import express from 'express';
import crypto from 'crypto';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, writeFileSync, unlinkSync, existsSync } from 'fs';
import { execFileSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3002;
const CHALLENGE_TTL_MS = parseInt(process.env.CHALLENGE_TTL || '30000', 10);
const CLEARANCE_TTL_MS = parseInt(process.env.CLEARANCE_TTL || '3600000', 10);
const MAX_CHALLENGES = 10_000;
const ROTATION_INTERVAL_MS = parseInt(process.env.WASM_ROTATION_INTERVAL || '60', 10) * 1000;
const SCORE_THRESHOLD = parseFloat(process.env.SCORE_THRESHOLD || '0.3');

const SERVER_SECRET = process.env.VM_SECRET || crypto.randomBytes(32).toString('hex');

const HEADER_MAGIC = 0x564d4243;
const HEADER_SIZE = 8;

const challenges = new Map();
const bundleCache = new Map();
const generations = new Map();
let currentGenerationId = null;

function createGeneration() {
    const id = crypto.randomUUID();
    const nonce = crypto.randomBytes(16).toString('hex');
    const signingKey = crypto.randomBytes(32).toString('hex');
    const bytecode = compilePayloadSync(nonce, signingKey);

    generations.set(id, {
        nonce,
        signingKey,
        bytecode,
        createdAt: Date.now(),
    });

    const ids = [...generations.keys()];
    while (ids.length > 2) {
        generations.delete(ids.shift());
    }

    currentGenerationId = id;
    console.log(`WASM generation rotated: ${id.slice(0, 8)}...`);
    return id;
}

setInterval(() => {
    const now = Date.now();
    for (const [id, c] of challenges) {
        if (now > c.expiresAt) challenges.delete(id);
    }
    for (const [id, b] of bundleCache) {
        if (now > b.expiresAt) bundleCache.delete(id);
    }
}, 15_000);

function createChallenge() {
    if (challenges.size >= MAX_CHALLENGES) {
        const oldest = challenges.keys().next().value;
        challenges.delete(oldest);
    }

    const id = crypto.randomUUID();
    const encKey = crypto.randomBytes(32);
    const createdAt = Date.now();

    challenges.set(id, {
        encKey,
        createdAt,
        expiresAt: createdAt + CHALLENGE_TTL_MS,
        used: false,
        generationId: currentGenerationId,
    });

    return { id, encKey, createdAt };
}

function validateChallenge(challengeId) {
    const challenge = challenges.get(challengeId);
    if (!challenge) {
        return { valid: false, error: 'Unknown challenge' };
    }
    if (challenge.used) {
        return { valid: false, error: 'Challenge used' };
    }
    if (Date.now() > challenge.expiresAt) {
        challenges.delete(challengeId);
        return { valid: false, error: 'Challenge expired' };
    }
    return { valid: true, challenge };
}

function consumeChallenge(challengeId) {
    const challenge = challenges.get(challengeId);
    if (!challenge) return null;
    challenge.used = true;
    challenges.delete(challengeId);
    return challenge;
}

function encryptBytecode(bytecode, encKey) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-ctr', encKey, iv);
    const encrypted = Buffer.concat([cipher.update(bytecode), cipher.final()]);

    const header = Buffer.alloc(HEADER_SIZE);
    header.writeUInt32BE(HEADER_MAGIC, 0);
    header.writeUInt32BE(encrypted.length, 4);

    return Buffer.concat([header, iv, encrypted]);
}

function signClearance(payload) {
    const str = JSON.stringify(payload);
    const encoded = Buffer.from(str).toString('base64url');
    const sig = crypto.createHmac('sha256', SERVER_SECRET).update(str).digest('base64url');
    return `${encoded}.${sig}`;
}

function verifyClearance(token) {
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

    try {
        if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
    } catch {
        return null;
    }

    const payload = JSON.parse(str);
    if (Date.now() > payload.exp) return null;
    return payload;
}

const app = express();
app.use(express.json({ limit: '64kb' }));
app.use(express.static(join(__dirname, 'public')));

app.post('/vm/init', (req, res) => {
    if (!currentGenerationId) {
        return res.status(503).json({
            error: 'Server initializing',
        });
    }

    const { id, encKey, createdAt } = createChallenge();
    const generation = generations.get(currentGenerationId);

    const bundle = encryptBytecode(generation.bytecode, encKey);
    bundleCache.set(id, {
        bundle,
        expiresAt: createdAt + CHALLENGE_TTL_MS,
    });

    res.json({
        challengeId: id,
        bundleUrl: `/vm/bundle/${id}.bin`,
        key: encKey.toString('hex'),
        wasmUrl: '/vm.wasm',
    });
});

app.get('/vm/bundle/:id.bin', (req, res) => {
    const cached = bundleCache.get(req.params.id);
    if (!cached) return res.status(404).send('');

    const { valid, error } = validateChallenge(req.params.id);
    if (!valid) {
        bundleCache.delete(req.params.id);
        return res.status(410).send('');
    }

    res.set({
        'Content-Type': 'application/octet-stream',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'X-Content-Type-Options': 'nosniff',
    });
    res.send(cached.bundle);
});

app.post('/vm/verify', (req, res) => {
    const { cid, payload: signedPayload } = req.body;

    if (!cid || !signedPayload) {
        return res.status(400).json({
            error: 'Missing fields',
        });
    }

    const { valid, error, challenge } = validateChallenge(cid);
    if (!valid) {
        return res.status(400).json({ error });
    }

    const generation = generations.get(challenge.generationId);
    if (!generation) {
        consumeChallenge(cid);
        return res.status(400).json({
            error: 'Invalid generation',
        });
    }

    const dotIdx = signedPayload.indexOf('.');
    if (dotIdx < 0) {
        consumeChallenge(cid);
        return res.status(400).json({
            error: 'Invalid payload format',
        });
    }

    const encodedBody = signedPayload.slice(0, dotIdx);
    const encodedSig = signedPayload.slice(dotIdx + 1);
    const payloadBuf = Buffer.from(encodedBody, 'base64url');
    const receivedSig = Buffer.from(encodedSig, 'base64url');

    if (receivedSig.length !== 32) {
        consumeChallenge(cid);
        return res.status(400).json({
            error: 'Invalid signature',
        });
    }

    const expectedSig = crypto
        .createHmac('sha256', Buffer.from(generation.signingKey, 'hex'))
        .update(payloadBuf)
        .digest();

    try {
        if (!crypto.timingSafeEqual(receivedSig, expectedSig)) {
            consumeChallenge(cid);
            return res.status(400).json({
                error: 'Signature mismatch',
            });
        }
    } catch {
        consumeChallenge(cid);
        return res.status(400).json({
            error: 'Signature mismatch',
        });
    }

    let parsed;
    try {
        parsed = JSON.parse(payloadBuf.toString());
    } catch {
        consumeChallenge(cid);
        return res.status(400).json({
            error: 'Malformed payload',
        });
    }

    const { s, ts } = parsed;

    if (!s || s.rn !== generation.nonce) {
        consumeChallenge(cid);
        return res.status(400).json({
            error: 'Invalid generation',
        });
    }

    const now = Date.now();
    if (Math.abs(now - ts) > CHALLENGE_TTL_MS) {
        return res.status(400).json({
            error: 'Timestamp out of range',
        });
    }

    consumeChallenge(cid);
    bundleCache.delete(cid);

    const score = scoreSignals(s, req.headers);
    console.log(
        `Challenge ${cid.slice(0, 8)}: score=${score.value} flags=[${score.flags.join(', ')}]`
    );

    if (score.value < SCORE_THRESHOLD) {
        return res.json({ ok: false });
    }

    const fpHash = computeFingerprintHash(s, req.headers);
    const uaHash = computeRequestFingerprint(req.headers);

    const clearance = signClearance({
        cid,
        score: score.value,
        fp: fpHash,
        ua_fp: uaHash,
        iat: now,
        exp: now + CLEARANCE_TTL_MS,
    });

    res.json({ ok: true, token: clearance });
});

app.get('/vm/protected', (req, res) => {
    const auth = req.headers.authorization;
    if (!auth?.startsWith('Bearer ')) {
        return res.status(401).json({
            error: 'Missing token',
        });
    }

    const payload = verifyClearance(auth.slice(7));
    if (!payload) {
        return res.status(403).json({
            error: 'Invalid/expired token',
        });
    }

    if (payload.ua_fp) {
        const reqFp = computeRequestFingerprint(req.headers);
        if (reqFp !== payload.ua_fp) {
            return res.status(403).json({
                error: 'Fingerprint mismatch',
            });
        }
    }

    res.json({ message: 'Access granted' });
});

function scoreSignals(signals, headers = {}) {
    let score = 1.0;
    const flags = [];

    const p = (amount, reason) => {
        score = Math.max(0, score - amount);
        flags.push(reason);
    };

    if (signals.a0 !== undefined) {
        const bits = countBits(signals.a0);
        if (bits > 0) p(Math.min(0.5, bits * 0.15), `a0:${bits} automation globals`);
    }

    if (signals.a1 !== undefined) {
        const bits = countBits(signals.a1);
        if (bits > 0) p(Math.min(0.5, bits * 0.12), `a1:${bits} enhanced automation`);
    }

    if (signals.a2 !== undefined) {
        const ua = signals.nav?.ua || '';
        const isChrome = /Chrome/.test(ua);
        if (isChrome) {
            if (!(signals.a2 & 1)) p(0.08, 'a2:chrome not in navigator');
            if (!(signals.a2 & 2)) p(0.05, 'a2:permissions missing');
        }
        if (!(signals.a2 & 4)) p(0.1, 'a2:no languages');
    }

    if (signals.x !== undefined) {
        const expected = 0xfff;
        const tampered = ~signals.x & expected;
        const bits = countBits(tampered);
        if (bits > 0) p(Math.min(0.4, bits * 0.08), `x:${bits} tampered natives`);
    }

    if (signals.p0 !== undefined) {
        if (!(signals.p0 & 1)) p(0.1, 'p0:defineProperty tampered');
        if (!(signals.p0 & 2)) p(0.1, 'p0:getOwnPropDesc tampered');
        if (!(signals.p0 & 4)) p(0.08, 'p0:Reflect.get tampered');
        if (signals.p0 & (1 << 10)) p(0.1, 'p0:navigator.toString wrong');
        if (signals.p0 & (1 << 11)) p(0.15, 'p0:navigator.toString throws');
        if (signals.p0 & (1 << 13)) p(0.1, 'p0:toStringTag wrong');
        if (signals.p0 & (1 << 14)) p(0.15, 'p0:proto getter not native');
        if (signals.p0 & (1 << 15)) p(0.1, 'p0:Reflect.get tampered v2');
    }

    if (signals.p_ov > 0) p(Math.min(0.3, signals.p_ov * 0.1), `p_ov:${signals.p_ov} overrides`);

    if (signals.p_pi > 0) p(0.15, 'p_pi:proto inconsistency');

    if (signals.f !== undefined) {
        const missing = ~signals.f & 0x7ff;
        const bits = countBits(missing);
        if (bits > 3) p(0.15, `f:${bits} features missing`);
        const hasAdvanced = (signals.f & 0x30) === 0x30;
        const missingBasic = !(signals.f & 1) || !(signals.f & 4);
        if (hasAdvanced && missingBasic) p(0.2, 'f:inconsistent features');
    }

    if (signals.nav) {
        const n = signals.nav;
        if (n.hw === 1) p(0.08, 'nav:1 core');
        if (n.hw === 0) p(0.15, 'nav:0 cores');
        if (n.lang === 0 && !/mobile|android/i.test(n.ua || '')) p(0.12, 'nav:no languages');
        if (n.dm !== undefined && n.dm !== null) {
            const valid = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64];
            if (!valid.includes(n.dm)) p(0.1, 'nav:invalid deviceMemory');
        }
        if (n.rtt === 0) p(0.05, 'nav:rtt=0');
        const ua = n.ua || '';
        if (/Chrome/.test(ua) && n.ps !== '20030107') p(0.08, 'nav:wrong productSub');
        if (/Firefox/.test(ua) && n.ps !== '20100101') p(0.08, 'nav:wrong productSub');
        if (/Chrome/.test(ua) && n.vd !== 'Google Inc.') p(0.08, 'nav:wrong vendor');
    }

    if (signals.scr) {
        const s = signals.scr;
        if (s.w === 0 || s.h === 0) p(0.15, 'scr:zero dimensions');
        if ((s.w === 800 && s.h === 600) || (s.w === 1024 && s.h === 768))
            p(0.1, 'scr:VM-typical resolution');
        if (s.cd > 0 && s.cd < 24) p(0.1, 'scr:low colorDepth');
        if (s.dpr === 0) p(0.1, 'scr:zero devicePixelRatio');
    }

    if (signals.env) {
        const e = signals.env;
        if (e.tz < -720 || e.tz > 840) p(0.1, 'env:impossible timezone');
        if (e.tzn === 'UTC' && e.tz !== 0) p(0.1, 'env:UTC name non-zero offset');
        if (e.tzn === '') p(0.08, 'env:empty timezone name');
        if ((e.touch & 1) !== ((e.touch >> 1) & 1)) p(0.05, 'env:touch inconsistency');
        if (e.doc & 1 && e.doc & 2) p(0.08, 'env:hidden+focused');
    }

    if (signals.b0 !== undefined) {
        const bits = countBits(signals.b0);
        if (bits > 0) p(Math.min(0.5, bits * 0.08), `b0:${bits} selenium signals`);
    }

    if (signals.b1 !== undefined) {
        const bits = countBits(signals.b1 & ~128); // ignore rtt=0 as stealth signal
        if (bits > 0) p(Math.min(0.5, bits * 0.08), `b1:${bits} stealth signals`);
    }

    if (signals.b2 !== undefined) {
        const bits = countBits(signals.b2);
        if (bits >= 3) p(0.35, `b2:${bits} undetected-cd`);
        else if (bits > 0) p(bits * 0.08, `b2:${bits} undetected-cd`);
    }

    if (signals.eng) {
        const e = signals.eng;
        const ua = signals.nav?.ua || '';
        if (/Chrome/.test(ua) && e.evl !== 33) p(0.1, 'eng:wrong eval length Chrome');
        if (/Firefox/.test(ua) && e.evl !== 37) p(0.1, 'eng:wrong eval length FF');
        if (e.stk === 'v8' && /Firefox/.test(ua)) p(0.15, 'eng:V8 stack in Firefox UA');
        if (e.stk === 'spidermonkey' && /Chrome/.test(ua)) p(0.15, 'eng:SM stack in Chrome UA');
        if (e.math === 0) p(0.05, 'eng:math fingerprint zero');
    }

    if (signals.mq) {
        const ua = signals.nav?.ua || '';
        if (!signals.mq.pf && !signals.mq.touch) p(0.1, 'mq:no pointer no touch');
        if (!/mobile|android/i.test(ua) && !signals.mq.hover) p(0.05, 'mq:no hover on desktop');
    }

    if (signals.gl) {
        if (signals.gl.vendor === 'Google Inc.' && /SwiftShader/.test(signals.gl.renderer))
            p(0.2, 'gl:Google+SwiftShader');
        if (signals.gl.maxTex === 0) p(0.1, 'gl:zero maxTextureSize');
    }

    if (signals.gl_r && /SwiftShader|llvmpipe|softpipe/i.test(signals.gl_r))
        p(0.2, 'software renderer');

    if (signals.tm) {
        if (signals.tm.pn_identical) p(0.1, 'tm:identical perf.now diffs');
    }

    if (signals.dr) {
        if (signals.dr.emoji_w === 0 && signals.dr.emoji_h === 0)
            p(0.08, 'dr:zero emoji dimensions');
    }

    if (signals.ch) {
        const ua = signals.nav?.ua || '';
        if (/Chrome/.test(ua) && !signals.ch.has_uad) p(0.08, 'ch:no userAgentData Chrome');
        if (signals.ch.mobile_mismatch) p(0.1, 'ch:mobile flag mismatch');
        if (signals.ch.platform_mismatch) p(0.1, 'ch:platform mismatch');
    }

    if (signals.cdp) p(0.15, 'cdp:console side-effect');

    if (signals.a3 !== undefined) {
        const bits = countBits(signals.a3);
        if (bits > 0) p(Math.min(0.5, bits * 0.12), `a3:${bits} extra automation globals`);
    }

    if (signals.h0) {
        const hd = signals.h0;
        const ua = signals.nav?.ua || '';
        const isChrome = /Chrome/.test(ua);

        if (isChrome && hd.pdf_off) p(0.1, 'h0:pdf viewer disabled');
        if (hd.no_tb) p(0.03, 'h0:no taskbar');
        if (hd.vvp_match) p(0.04, 'h0:viewport matches screen');
        if (isChrome && hd.no_share) p(0.02, 'h0:no Web Share API');
        if (hd.at_red) p(0.05, 'h0:ActiveText red');
        if (hd.uad_blank) p(0.12, 'h0:blank UAData platform');
        if (hd.chrome_pos) p(0.02, 'h0:chrome key injected');
        if (hd.rt_proto) p(0.12, 'h0:runtime constructable');
        if (hd.ifr_proxy) p(0.15, 'h0:iframe proxy detected');
        if (hd.plugins_inst) p(0.1, 'h0:plugins not PluginArray');
        if (hd.mesa) p(0.2, 'h0:Mesa OffScreen renderer');
    }

    if (signals.sc) {
        if (signals.sc.dim_lie) p(0.15, 'sc:screen dimensions spoofed');
        if (signals.sc.always_light) p(0.04, 'sc:always light scheme');
    }

    if (signals.lc) {
        if (signals.lc.lang_pfx) p(0.1, 'lc:language prefix mismatch');
        if (signals.lc.locale_lie) p(0.02, 'lc:locale formatting mismatch');
    }

    if (signals.pf) {
        if (signals.pf.lie_count > 2)
            p(
                Math.min(0.4, signals.pf.lie_count * 0.06),
                `pf:${signals.pf.lie_count}` + ' API prototype lies'
            );
        else if (signals.pf.lie_count > 0)
            p(signals.pf.lie_count * 0.05, `pf:${signals.pf.lie_count}` + ' API prototype lies');
        if (signals.pf.mt_proto) p(0.1, 'pf:MimeType proto tampered');
    }

    if (signals.css_v > 0 && signals.nav) {
        const ua = signals.nav.ua || '';
        const m = ua.match(/Chrome\/(\d+)/);
        if (m) {
            const uaVer = parseInt(m[1], 10);
            if (uaVer < signals.css_v || (signals.css_v < 115 && uaVer - signals.css_v > 5))
                p(0.15, 'css_v:UA version mismatch');
        }
    }

    if (signals.cv === 'err') p(0.1, 'canvas error');

    if (signals.fe) {
        if (signals.fe.count === 0 && signals.fe.widths?.length > 0)
            p(0.1, 'fe:zero detected fonts');
    }

    if (signals.vmd) {
        if (signals.vmd.sw_gl) p(0.2, 'vmd:software/VM GL renderer');
        if (signals.vmd.hw_low) p(0.06, 'vmd:low hardware specs');
        if (signals.vmd.vm_res) p(0.08, 'vmd:VM-typical resolution');
        if (signals.vmd.vm_audio) p(0.1, 'vmd:zero audio channels');

        const vmHits =
            (signals.vmd.sw_gl || 0) +
            (signals.vmd.hw_low || 0) +
            (signals.vmd.vm_res || 0) +
            (signals.vmd.vm_audio || 0);
        if (vmHits >= 3) p(0.15, 'vmd:multiple VM indicators');
    }

    if (signals.ct) {
        if (signals.ct.rand) p(0.25, 'ct:canvas randomization');
        if (signals.ct.err) p(0.05, 'ct:canvas error');
        if (signals.ct.inconsist) p(0.15, 'ct:canvas data/pixel mismatch');
    }

    if (signals.vms) {
        const ua = signals.nav?.ua || '';
        if (/Chrome/.test(ua) && !/Android/.test(ua)) {
            if (signals.vms.vc === 0) p(0.08, 'vms:no voices Chrome');
            if (!signals.vms.md) p(0.1, 'vms:no mediaDevices');
        }
        if (/Chrome/.test(ua) && !signals.vms.rtc) p(0.05, 'vms:no WebRTC Chrome');
    }

    if (signals.perf) {
        if (signals.perf.jshl && signals.perf.tjhs) {
            if (signals.perf.tjhs > signals.perf.jshl) p(0.1, 'perf:heap exceeds limit');
        }
    }

    if (signals.nav && signals.gl_r && signals.cv) {
        const ua = signals.nav.ua || '';
        const renderer = signals.gl_r || '';
        const isChromeUA = /Chrome/.test(ua) && !/Edge/.test(ua);
        const isFirefoxUA = /Firefox/.test(ua);
        const isSafariUA = /Safari/.test(ua) && !isChromeUA;
        const isLinux = /Linux/.test(ua) && !/Android/.test(ua);
        const isMac = /Mac/.test(ua);
        const isWin = /Windows/.test(ua);

        if (isChromeUA && /Gecko\/\d/.test(ua) && !/like Gecko/.test(ua))
            p(0.2, 'xv:Chrome UA with Gecko engine');

        if (isFirefoxUA && /ANGLE/.test(renderer)) p(0.15, 'xv:Firefox UA with ANGLE renderer');

        if (isSafariUA && isLinux) p(0.2, 'xv:Safari UA on Linux');

        if (isMac && /NVIDIA|GeForce/i.test(renderer) && /Mac OS X 1[1-9]|macOS 1[2-9]/.test(ua))
            p(0.1, 'xv:NVIDIA on modern macOS');

        if (signals.scr) {
            const { w, h, dpr } = signals.scr;
            if (isMac && dpr === 1 && w > 1920) p(0.08, 'xv:Mac non-retina high-res');
        }

        if (signals.eng) {
            if (isChromeUA && signals.eng.stk === 'spidermonkey')
                p(0.2, 'xv:Chrome UA SpiderMonkey stack');
            if (isFirefoxUA && signals.eng.stk === 'v8') p(0.2, 'xv:Firefox UA V8 stack');
        }
    }

    if (headers) {
        if (!headers['accept']) p(0.05, 'hdr:no Accept');
        if (!headers['accept-language']) p(0.05, 'hdr:no Accept-Language');
        if (!headers['accept-encoding']) p(0.05, 'hdr:no Accept-Encoding');
        const ua = headers['user-agent'] || '';
        if (/HeadlessChrome|PhantomJS|SlimerJS/i.test(ua)) p(0.2, 'hdr:headless UA string');
        if (ua && !/Mozilla\//.test(ua)) p(0.08, 'hdr:non-standard UA');
    }

    return {
        value: Math.round(score * 10000) / 10000,
        flags,
    };
}

function countBits(n) {
    let count = 0;
    let v = n >>> 0;
    while (v) {
        count += v & 1;
        v >>>= 1;
    }
    return count;
}

function computeFingerprintHash(signals, headers) {
    const parts = [
        signals.cv || '',
        signals.gl_r || '',
        signals.gl_v || '',
        signals.nav?.ua || '',
        signals.nav?.plat || '',
        String(signals.scr?.w || 0),
        String(signals.scr?.h || 0),
        String(signals.scr?.cd || 0),
        String(signals.scr?.dpr || 0),
        String(signals.nav?.hw || 0),
        signals.eng?.stk || '',
        headers?.['user-agent'] || '',
    ];
    return crypto.createHash('sha256').update(parts.join('|')).digest('hex').slice(0, 16);
}

function computeRequestFingerprint(headers) {
    return crypto
        .createHash('sha256')
        .update(headers['user-agent'] || '')
        .digest('hex')
        .slice(0, 12);
}

function compilePayloadSync(nonce, signingKey) {
    const payloadPath = join(__dirname, 'scripts', 'signals_payload.js');
    const source = readFileSync(payloadPath, 'utf-8')
        .replace('__ROTATION_NONCE__', nonce)
        .replace('__SIGNING_KEY__', signingKey);

    const qjsDir = join(__dirname, 'quickjs');
    const qjscPath = join(qjsDir, 'qjsc');

    if (!existsSync(qjscPath)) {
        console.log('Building qjsc compiler...');
        execFileSync('make', ['qjsc'], {
            cwd: qjsDir,
            stdio: 'inherit',
            timeout: 120000,
        });
    }

    const timingTrap =
        'var __fence=__vm_integrity();\n' +
        '__vm_trap();\n' +
        '__vm_ccode();\n' +
        '__vm_csum(0,128);\n';

    const epilogue = '\n__vm_trap();\n' + '__vm_chk();\n' + '__result;\n';

    const instrumented = timingTrap + 'var __result = ' + source + epilogue;

    const tmpPath = join(__dirname, '.tmp_payload.js');
    writeFileSync(tmpPath, instrumented);

    const tmpC = join(__dirname, '.tmp_payload.c');

    try {
        execFileSync(qjscPath, ['-c', '-s', '-N', 'payload_bc', '-o', tmpC, tmpPath], {
            stdio: 'pipe',
            timeout: 30000,
        });

        const cSource = readFileSync(tmpC, 'utf-8');
        const match = cSource.match(/\{\s*([\s\S]*?)\s*\};\s*$/m);
        if (!match) throw new Error('Parse failed');

        const bytes = match[1]
            .split(',')
            .map((s) => Number(s.trim()))
            .filter((n) => !isNaN(n));

        return Buffer.from(bytes);
    } finally {
        try {
            unlinkSync(tmpPath);
        } catch {}
        try {
            unlinkSync(tmpC);
        } catch {}
    }
}

createGeneration();

setInterval(() => {
    try {
        createGeneration();
    } catch (err) {
        console.error('Rotation failed:', err.message);
    }
}, ROTATION_INTERVAL_MS);

app.listen(PORT, () => {
    console.log(`JSVM server on :${PORT}`);
    console.log(`WASM rotation: every ${ROTATION_INTERVAL_MS / 1000}s`);
});
