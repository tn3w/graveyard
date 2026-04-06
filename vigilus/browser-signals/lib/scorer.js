// Signal Scoring Engine
// Evaluates collected browser signals and returns a human-likelihood score (0.0-1.0).
// Score 0.0 = definite bot, 1.0 = definitely human.
// Each signal category contributes a weighted penalty.

export function scoreSignals(signals, headers = {}) {
    let score = 1.0;
    const flags = [];

    const p = (amount, reason) => {
        score = Math.max(0, score - amount);
        flags.push(reason);
    };

    // ── a0: Direct Automation Globals ──
    if (signals.a0 !== undefined) {
        const bits = countBits(signals.a0);
        if (bits > 0) p(Math.min(0.5, bits * 0.15), `a0:${bits} automation globals`);
    }

    // ── a1: Enhanced Automation Detection ──
    if (signals.a1 !== undefined) {
        const bits = countBits(signals.a1);
        if (bits > 0) p(Math.min(0.5, bits * 0.12), `a1:${bits} enhanced automation`);
    }

    // ── a2: Browser Feature Presence ──
    if (signals.a2 !== undefined) {
        const ua = signals.nav?.ua || '';
        const isChrome = /Chrome/.test(ua);
        // Chrome should have chrome in navigator, permissions, languages
        if (isChrome) {
            if (!(signals.a2 & 1)) p(0.08, 'a2:chrome not in navigator');
            if (!(signals.a2 & 2)) p(0.05, 'a2:permissions missing');
        }
        if (!(signals.a2 & 4)) p(0.1, 'a2:no languages');
    }

    // ── x: Tampering Bitmap ──
    // Bits are SET when native — all should be set (0xFFF)
    if (signals.x !== undefined) {
        const expected = 0xfff; // 12 bits
        const tampered = ~signals.x & expected;
        const bits = countBits(tampered);
        if (bits > 0) p(Math.min(0.4, bits * 0.08), `x:${bits} tampered natives`);
    }

    // ── p0: Property Integrity ──
    if (signals.p0 !== undefined) {
        // Bits 0-2: defineProperty, getOwnPropertyDescriptor, Reflect.get should be native (set)
        if (!(signals.p0 & 1)) p(0.1, 'p0:Object.defineProperty tampered');
        if (!(signals.p0 & 2)) p(0.1, 'p0:getOwnPropertyDescriptor tampered');
        if (!(signals.p0 & 4)) p(0.08, 'p0:Reflect.get tampered');
        // Bit 10: navigator.toString() wrong
        if (signals.p0 & (1 << 10)) p(0.1, 'p0:navigator.toString wrong');
        // Bit 11: navigator.toString() throws
        if (signals.p0 & (1 << 11)) p(0.15, 'p0:navigator.toString throws');
        // Bit 13: Symbol.toStringTag wrong
        if (signals.p0 & (1 << 13)) p(0.1, 'p0:toStringTag wrong');
        // Bit 14: prototype getter not native
        if (signals.p0 & (1 << 14)) p(0.15, 'p0:proto getter not native');
        // Bit 15: Reflect.get tampered (second check)
        if (signals.p0 & (1 << 15)) p(0.1, 'p0:Reflect.get tampered v2');
    }

    // ── p_overrides: Direct property overrides on navigator ──
    if (signals.p_ov > 0) p(Math.min(0.3, signals.p_ov * 0.1), `p_ov:${signals.p_ov} overrides`);

    // ── p_proto: Prototype inconsistencies ──
    if (signals.p_pi > 0) p(0.15, 'p_pi:proto inconsistency');

    // ── c0: Canvas/WebGL/Audio ──
    if (signals.c0 !== undefined) {
        if (signals.c0 & 2) p(0.05, 'c0:canvas error');
        if (signals.c0 & 4) p(0.15, 'c0:canvas all zeros');
        if (signals.c0 & 16) p(0.05, 'c0:webgl error');
        if (signals.c0 & 64) p(0.05, 'c0:audio error');
        // SwiftShader/llvmpipe renderer
        if (signals.gl_r && /SwiftShader|llvmpipe|softpipe/i.test(signals.gl_r)) {
            p(0.2, 'c0:software renderer');
        }
    }

    // ── f: Features Bitmap ──
    if (signals.f !== undefined) {
        // Bits 0-10 should all be set in modern browsers
        const missing = ~signals.f & 0x7ff;
        const bits = countBits(missing);
        if (bits > 3) p(0.15, `f:${bits} features missing`);
        // Inconsistency: WebGL2+WASM present but localStorage/WebSocket missing
        const hasAdvanced = (signals.f & 0x30) === 0x30; // WebGL2 + WASM
        const missingBasic = !(signals.f & 1) || !(signals.f & 4); // localStorage or WebSocket
        if (hasAdvanced && missingBasic) p(0.2, 'f:inconsistent features');
    }

    // ── nav: Navigator ──
    if (signals.nav) {
        const n = signals.nav;
        if (n.hw === 1) p(0.08, 'nav:1 core');
        if (n.hw === 0) p(0.15, 'nav:0 cores');
        if (n.pl === 0 && !/mobile|android/i.test(n.ua || '')) p(0.12, 'nav:0 plugins desktop');
        if (n.lang === 0) p(0.12, 'nav:no languages');
        // deviceMemory check
        if (n.dm !== undefined && n.dm !== null) {
            const valid = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64];
            if (!valid.includes(n.dm)) p(0.1, 'nav:invalid deviceMemory');
        }
        // connection.rtt
        if (n.rtt === 0) p(0.1, 'nav:rtt=0');
        // productSub check
        const ua = n.ua || '';
        if (/Chrome/.test(ua) && n.ps !== '20030107') p(0.08, 'nav:wrong productSub');
        if (/Firefox/.test(ua) && n.ps !== '20100101') p(0.08, 'nav:wrong productSub');
        // vendor check
        if (/Chrome/.test(ua) && n.vd !== 'Google Inc.') p(0.08, 'nav:wrong vendor');
    }

    // ── scr: Screen ──
    if (signals.scr) {
        const s = signals.scr;
        if (s.w === 0 || s.h === 0) p(0.15, 'scr:zero dimensions');
        if ((s.w === 800 && s.h === 600) || (s.w === 1024 && s.h === 768))
            p(0.1, 'scr:VM-typical resolution');
        if (s.cd > 0 && s.cd < 24) p(0.1, 'scr:low colorDepth');
        if (s.dpr === 0) p(0.1, 'scr:zero devicePixelRatio');
    }

    // ── env: Environment/Timezone ──
    if (signals.env) {
        const e = signals.env;
        // Timezone range check
        if (e.tz < -720 || e.tz > 840) p(0.1, 'env:impossible timezone');
        // Timezone name vs offset inconsistency
        if (e.tzn === 'UTC' && e.tz !== 0) p(0.1, 'env:UTC name but non-zero offset');
        if (e.tzn === '') p(0.08, 'env:empty timezone name');
        // Touch inconsistency
        if ((e.touch & 1) !== ((e.touch >> 1) & 1)) p(0.05, 'env:touch inconsistency');
        // Document state: hidden && hasFocus
        if (e.doc & 1 && e.doc & 2) p(0.08, 'env:hidden+focused');
        // Visibility changes
        if (e.vc > 10) p(0.03, 'env:excessive visibility changes');
    }

    // ── b0: Sophisticated Bot Detection - Chromium/Selenium ──
    if (signals.b0 !== undefined) {
        const bits = countBits(signals.b0);
        if (bits > 0) p(Math.min(0.5, bits * 0.08), `b0:${bits} selenium signals`);
    }

    // ── b1: Sophisticated Bot Detection - Stealth/Advanced ──
    if (signals.b1 !== undefined) {
        const bits = countBits(signals.b1);
        if (bits > 0) p(Math.min(0.5, bits * 0.08), `b1:${bits} stealth signals`);
    }

    // ── b2: Sophisticated Bot Detection - Undetected-Chromedriver ──
    if (signals.b2 !== undefined) {
        const bits = countBits(signals.b2);
        if (bits >= 3) p(0.35, `b2:${bits} undetected-cd signals`);
        else if (bits > 0) p(bits * 0.08, `b2:${bits} undetected-cd signals`);
    }

    // ── eng: Engine Fingerprint ──
    if (signals.eng) {
        const e = signals.eng;
        const ua = signals.nav?.ua || '';
        // eval.toString().length
        if (/Chrome/.test(ua) && e.evl !== 33) p(0.1, 'eng:wrong eval length for Chrome');
        if (/Firefox/.test(ua) && e.evl !== 37) p(0.1, 'eng:wrong eval length for Firefox');
        // Error stack format mismatch
        if (e.stk === 'v8' && /Firefox/.test(ua)) p(0.15, 'eng:V8 stack in Firefox UA');
        if (e.stk === 'spidermonkey' && /Chrome/.test(ua)) p(0.15, 'eng:SM stack in Chrome UA');
        // Math fingerprint mismatch
        if (e.math !== undefined && e.math === 0) p(0.05, 'eng:math fingerprint zero');
    }

    // ── mq: CSS Media Queries ──
    if (signals.mq) {
        const q = signals.mq;
        const ua = signals.nav?.ua || '';
        // pointer:fine=false + no touch = headless
        if (!q.pf && !q.touch) p(0.1, 'mq:no pointer no touch');
        // hover:hover should be true on desktop
        if (!/mobile|android/i.test(ua) && !q.hover) p(0.05, 'mq:no hover on desktop');
    }

    // ── vm: Voices/Media ──
    if (signals.vm) {
        const v = signals.vm;
        const ua = signals.nav?.ua || '';
        if (/Chrome/.test(ua) && v.voices === 0) p(0.08, 'vm:no voices in Chrome');
        if (/Chrome/.test(ua) && !/Android/.test(ua) && v.media === 0)
            p(0.1, 'vm:no media devices desktop Chrome');
    }

    // ── wk: Worker Context Consistency ──
    if (signals.wk) {
        const w = signals.wk;
        if (w.ua_match === false) p(0.2, 'wk:UA mismatch main vs worker');
        if (w.hw_match === false) p(0.15, 'wk:hardwareConcurrency mismatch');
        if (w.plat_match === false) p(0.15, 'wk:platform mismatch');
        if (w.lang_match === false) p(0.1, 'wk:languages mismatch');
    }

    // ── rt: WebRTC ──
    if (signals.rt) {
        // WebRTC missing in Chrome is suspicious
        const ua = signals.nav?.ua || '';
        if (/Chrome/.test(ua) && !signals.rt.support) p(0.05, 'rt:no WebRTC in Chrome');
    }

    // ── gl: WebGL Deep ──
    if (signals.gl) {
        const g = signals.gl;
        if (g.vendor === 'Google Inc.' && /SwiftShader/.test(g.renderer))
            p(0.2, 'gl:Google+SwiftShader');
        if (g.maxTex === 0) p(0.1, 'gl:zero maxTextureSize');
    }

    // ── tm: Timing Analysis ──
    if (signals.tm) {
        const t = signals.tm;
        // rAF should be ~16.7ms, huge deviation is suspicious
        if (t.raf > 0 && (t.raf < 5 || t.raf > 100)) p(0.05, 'tm:abnormal rAF timing');
        // performance.now identical diffs = headless
        if (t.pn_identical) p(0.1, 'tm:identical perf.now diffs');
    }

    // ── dr: DOMRect/TextMetrics ──
    if (signals.dr) {
        if (signals.dr.emoji_w === 0 && signals.dr.emoji_h === 0)
            p(0.08, 'dr:zero emoji dimensions');
    }

    // ── ch: Client Hints Consistency ──
    if (signals.ch) {
        const c = signals.ch;
        const ua = signals.nav?.ua || '';
        if (/Chrome/.test(ua) && !c.has_uad) p(0.08, 'ch:no userAgentData in Chrome');
        if (c.mobile_mismatch) p(0.1, 'ch:mobile flag mismatch');
        if (c.platform_mismatch) p(0.1, 'ch:platform mismatch');
    }

    // ── bhv: Behavioral (if enough time elapsed) ──
    if (signals.bhv) {
        const b = signals.bhv;
        // Zero mouse movement over >3s is suspicious (unless mobile)
        if (b.mouse === 0 && b.elapsed > 3000 && !/mobile|android/i.test(signals.nav?.ua || ''))
            p(0.05, 'bhv:no mouse movement');
    }

    // ── Request Headers ──
    if (headers) {
        if (!headers['accept']) p(0.05, 'hdr:no Accept');
        if (!headers['accept-language']) p(0.05, 'hdr:no Accept-Language');
        if (!headers['accept-encoding']) p(0.05, 'hdr:no Accept-Encoding');
    }

    return { score: Math.round(score * 10000) / 10000, flags };
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
