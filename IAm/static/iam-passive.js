((global) => {
    const eventData = { m: [], c: [], k: 0, s: [], f: 0, v: 0, r: [], t: 0 };
    let tracking = false, startTime = null, cleanup = null;
    let devToolsOpen = false, devToolsOpenCount = 0;
    const MAX_MOUSE = 200, MIN_TIME = 2000;

    const bool = value => value ? 1 : 0;

    const detectDevTools = () => {
        const widthDiff = window.outerWidth - window.innerWidth;
        const heightDiff = window.outerHeight - window.innerHeight;
        let bitmap = 0;
        if (widthDiff > 160 || heightDiff > 160) bitmap |= 1;
        if (window.Firebug?.chrome?.isInitialized) bitmap |= 2;

        const t1 = performance.now();
        for (let i = 0; i < 100; i++) { console.log; console.clear; }
        if (performance.now() - t1 > 100) bitmap |= 4;

        const el = document.createElement('div');
        Object.defineProperty(el, 'id', { get: () => { bitmap |= 8; return 'devtools-detect'; } });

        const r = /./;
        r.toString = () => { bitmap |= 16; return 'devtools'; };

        return { bitmap, widthDiff, heightDiff, openCount: devToolsOpenCount, wasOpen: devToolsOpen };
    };

    const monitorDevTools = () => {
        const check = () => {
            const isOpen = window.outerWidth - window.innerWidth > 160 ||
                          window.outerHeight - window.innerHeight > 160;
            if (isOpen && !devToolsOpen) devToolsOpenCount++;
            devToolsOpen = isOpen;
        };
        window.addEventListener('resize', check);
        setInterval(check, 1000);
    };

    const collectAutomationBitmaps = () => {
        const nav = navigator, w = window, d = document;
        const ua = nav.userAgent || '';
        let a0 = 0, a1 = 0, a2 = 0;

        const automationProps = [
            'callPhantom', '_phantom', '__nightmare', 'domAutomation',
            'domAutomationController', '_selenium', 'selenium', 'webdriver',
            '__webdriver_script_fn', '__driver_evaluate', '__webdriver_evaluate'
        ];
        automationProps.forEach((prop, i) => { if (w[prop]) a0 |= 1 << i; });

        a0 |= bool(nav.webdriver) << 11;
        a0 |= bool(w._headless || ua.toLowerCase().includes('headless')) << 12;
        a0 |= bool(w.Cypress || w.__cypress) << 13;
        a0 |= bool(w.__playwright_evaluate || w.__playwright_resume || w.playwright) << 15;
        a0 |= bool(ua.includes('HeadlessChrome')) << 18;
        a0 |= bool(w.Buffer) << 19;
        a0 |= bool(w.emit || w.spawn) << 20;
        a0 |= bool(d.documentElement.getAttribute('webdriver')) << 21;
        a0 |= bool(w.awesomium || w.geb) << 22;

        try {
            const wd = Object.getOwnPropertyDescriptor(nav, 'webdriver');
            if (wd) {
                a1 |= 1;
                a1 |= bool(typeof wd.get === 'function') << 1;
                a1 |= bool('value' in wd) << 2;
                a1 |= bool(wd.configurable) << 3;
                a1 |= bool(wd.enumerable) << 4;
            }
        } catch {}

        try {
            const cdcProps = ['cdc_adoQpoasnfa76pfcZLmcfl_Array',
                'cdc_adoQpoasnfa76pfcZLmcfl_Promise', 'cdc_adoQpoasnfa76pfcZLmcfl_Symbol'];
            a1 |= bool(cdcProps.some(p => w[p]) || d.$cdc_asdjflasutopfhvcZLmcfl_) << 5;
        } catch {}

        try {
            a1 |= bool(w.chrome?.runtime?.connect) << 6;
        } catch {}

        try {
            throw new Error('x');
        } catch (e) {
            a1 |= bool(/selenium|webdriver|puppeteer|playwright|cypress/i.test(e.stack || '')) << 7;
        }

        try {
            for (const sc of d.querySelectorAll('script')) {
                if (!sc.src && sc.textContent?.includes('Object.defineProperty') &&
                    sc.textContent.includes('webdriver') && sc.textContent.includes('navigator')) {
                    a1 |= 1 << 9; break;
                }
            }
        } catch {}

        try {
            const np = Object.getPrototypeOf(nav);
            const wd2 = Object.getOwnPropertyDescriptor(np, 'webdriver');
            if (wd2?.get && !wd2.get.toString().includes('[native code]')) a1 |= 1 << 10;
        } catch {}

        try {
            a1 |= bool(d.querySelector('[selenium],[webdriver],[driver]')) << 11;
        } catch {}

        try {
            const fts = Function.prototype.toString.call(Function.prototype.toString);
            a1 |= bool(!fts.includes('[native code]')) << 13;
        } catch {}

        try { a1 |= bool(w.__cdp_binding__ || w.__chromeSendMessage) << 14; } catch {}

        try {
            const cdcPattern = /^cdc_|^_cdc_|_Array$|_Promise$|_Symbol$|_Object$|_Proxy$/;
            a1 |= bool(Object.keys(w).some(k => cdcPattern.test(k))) << 15;
        } catch {}

        a2 |= bool('chrome' in nav);
        a2 |= bool('permissions' in nav) << 1;
        a2 |= bool(nav.languages?.length > 0) << 2;
        try { a2 |= bool(nav.connection?.type) << 3; } catch {}
        try { a2 |= bool('getBattery' in nav) << 4; } catch {}

        let npn = '';
        try { npn = Object.getPrototypeOf(nav).constructor.name; } catch {}

        return [a0, a1, a2, npn];
    };

    const collectTamperingBitmap = () => {
        let bitmap = 0;
        const nativeFns = [
            [Function.prototype.toString, 0], [setTimeout, 1], [setInterval, 2],
            [Date.now, 3], [Math.random, 4], [Array.prototype.push, 5],
            [JSON.stringify, 6], [Object.keys, 7]
        ];
        nativeFns.forEach(([fn, bit]) => {
            try { bitmap |= bool(fn.toString().includes('[native code]')) << bit; } catch {}
        });
        return bitmap;
    };

    const collectPropertyIntegrity = () => {
        const nav = navigator, w = window;
        let p0 = 0, overrides = 0, protoInconsistencies = 0;

        const nativeChecks = [
            [Object.defineProperty, 0], [Object.getOwnPropertyDescriptor, 1]
        ];
        nativeChecks.forEach(([fn, bit]) => {
            try { p0 |= bool(fn.toString().includes('[native code]')) << bit; } catch {}
        });

        try {
            if (typeof Reflect !== 'undefined')
                p0 |= bool(Reflect.get.toString().includes('[native code]')) << 2;
        } catch {}

        try {
            if (nav.permissions?.query) {
                p0 |= 1 << 3;
                p0 |= bool(nav.permissions.query.toString().includes('[native code]')) << 4;
            }
        } catch {}

        if (w.chrome) {
            p0 |= 1 << 5;
            p0 |= bool(w.chrome.app) << 6;
            p0 |= bool(w.chrome.runtime) << 7;
            p0 |= bool(typeof w.chrome.csi === 'function') << 8;
            p0 |= bool(typeof w.chrome.loadTimes === 'function') << 9;
        }

        try { p0 |= bool(nav.toString() !== '[object Navigator]') << 10; }
        catch { p0 |= 1 << 11; }

        try { p0 |= bool(nav[Symbol.toStringTag] !== 'Navigator') << 13; } catch {}

        try {
            const props = ['userAgent', 'platform', 'languages', 'plugins', 'webdriver'];
            for (const prop of props) {
                const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(nav), prop);
                if (desc?.get && !desc.get.toString().includes('[native code]')) {
                    p0 |= 1 << 14; break;
                }
            }
        } catch {}

        try {
            if (typeof Reflect !== 'undefined')
                p0 |= bool(!Reflect.get.toString().includes('[native code]')) << 15;
        } catch {}

        try {
            if (Object.getPrototypeOf(nav).constructor.name !== 'Navigator') protoInconsistencies++;
        } catch {}

        ['webdriver', 'plugins', 'languages', 'platform', 'userAgent'].forEach(prop => {
            try {
                const desc = Object.getOwnPropertyDescriptor(nav, prop);
                if (desc) {
                    if (desc.get && !desc.get.toString().includes('[native code]')) overrides++;
                    else if ('value' in desc) overrides++;
                }
            } catch {}
        });

        return [p0, overrides, protoInconsistencies, nav.toString?.() || ''];
    };

    const collectFeaturesBitmap = () => {
        const w = window;
        let bitmap = 0;
        const features = [
            ['localStorage', 0], ['sessionStorage', 1], ['WebSocket', 2],
            ['WebGLRenderingContext', 3], ['WebGL2RenderingContext', 4],
            ['indexedDB', 6], ['Notification', 7], ['fetch', 8],
            ['Promise', 9], ['Intl', 10], ['SharedArrayBuffer', 11]
        ];
        features.forEach(([prop, bit]) => { bitmap |= bool(prop in w) << bit; });
        bitmap |= bool(typeof WebAssembly === 'object') << 5;
        return bitmap;
    };

    const collectCanvasWebGLAudio = () => {
        const d = document, w = window;
        let bitmap = 0, canvasDataLen = 0, webglRenderer = '', sampleRate = 0;

        try {
            const cv = d.createElement('canvas');
            const ctx = cv.getContext('2d');
            if (ctx) {
                bitmap |= 1;
                cv.width = 200; cv.height = 50;
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillStyle = '#f60';
                ctx.fillRect(10, 10, 80, 30);
                ctx.fillStyle = '#069';
                ctx.fillText('IAm', 20, 20);
                const id = ctx.getImageData(0, 0, cv.width, cv.height);
                bitmap |= bool(id.data.every(p => p === 0)) << 2;
                canvasDataLen = cv.toDataURL().length;
            }
        } catch { bitmap |= 1 << 1; }

        try {
            const cv = d.createElement('canvas');
            const gl = cv.getContext('webgl') || cv.getContext('experimental-webgl');
            if (gl) {
                bitmap |= 1 << 3;
                webglRenderer = gl.getParameter(gl.RENDERER) || '';
                const dbg = gl.getExtension('WEBGL_debug_renderer_info');
                if (dbg) {
                    const unmasked = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
                    bitmap |= bool(unmasked !== webglRenderer) << 7;
                }
            }
        } catch { bitmap |= 1 << 4; }

        try {
            const AC = w.AudioContext || w.webkitAudioContext;
            if (AC) {
                bitmap |= 1 << 5;
                const ac = new AC();
                sampleRate = ac.sampleRate;
                ac.close();
            }
        } catch { bitmap |= 1 << 6; }

        return [bitmap, canvasDataLen, webglRenderer, sampleRate];
    };

    const collectPerformanceStats = () => {
        const times = [];
        for (let i = 0; i < 5; i++) {
            const start = performance.now();
            let x = 0;
            for (let j = 0; j < 1000; j++) x += Math.sqrt(j);
            times.push(performance.now() - start);
        }
        const mean = times.reduce((a, b) => a + b, 0) / times.length;
        const variance = times.map(x => (x - mean) ** 2).reduce((a, b) => a + b, 0) / times.length;
        let memoryLimit = 0;
        try { memoryLimit = performance.memory?.jsHeapSizeLimit || 0; } catch {}
        return [mean, variance, memoryLimit];
    };

    const collectBotDetectionSb0 = () => {
        const nav = navigator, w = window, d = document;
        const ua = nav.userAgent || '';
        let bitmap = 0;

        try {
            const wKeys = Object.keys(w);
            bitmap |= bool(wKeys.some(k => k.startsWith('$cdc_') || k.startsWith('cdc_')));
            bitmap |= bool('__selenium_unwrapped' in w || '__selenium_evaluate' in w) << 1;
        } catch {}

        try {
            const plugins = nav.plugins;
            if (plugins) {
                bitmap |= bool(plugins.length === 0 && !/mobile|android/i.test(ua)) << 2;
                bitmap |= bool(Object.prototype.toString.call(plugins) !== '[object PluginArray]') << 3;
                bitmap |= bool(typeof plugins.refresh !== 'function') << 4;
            }
        } catch {}

        try {
            const mimes = nav.mimeTypes;
            if (mimes)
                bitmap |= bool(Object.prototype.toString.call(mimes) !== '[object MimeTypeArray]') << 5;
        } catch {}

        try {
            if (nav.permissions?.query)
                bitmap |= bool(!nav.permissions.query.toString().includes('[native code]')) << 6;
        } catch {}

        try {
            if (w.chrome) {
                const hasCsi = typeof w.chrome.csi === 'function';
                const hasLoadTimes = typeof w.chrome.loadTimes === 'function';
                bitmap |= bool(w.chrome.runtime && !hasCsi && !hasLoadTimes) << 7;
                try {
                    w.chrome.runtime?.connect?.();
                } catch (e) {
                    bitmap |= bool(!e.message.includes('Extension')) << 8;
                }
            }
        } catch {}

        try {
            if ('Notification' in w)
                bitmap |= bool(Notification.permission === 'denied' && !d.hidden) << 9;
        } catch {}

        try { bitmap |= bool(w.outerWidth === 0 || w.outerHeight === 0) << 10; } catch {}
        try { bitmap |= bool(!('speechSynthesis' in w) && /Chrome/.test(ua)) << 11; } catch {}

        try {
            const dtf = new Intl.DateTimeFormat().resolvedOptions();
            const tzOffset = new Date().getTimezoneOffset();
            bitmap |= bool(!dtf.timeZone || (dtf.timeZone === 'UTC' && tzOffset !== 0)) << 12;
        } catch {}

        try {
            const cv = d.createElement('canvas');
            const gl = cv.getContext('webgl');
            if (gl) {
                const dbg = gl.getExtension('WEBGL_debug_renderer_info');
                if (dbg) {
                    const vendor = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL);
                    const renderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
                    bitmap |= bool(/SwiftShader|llvmpipe|softpipe/i.test(renderer)) << 13;
                    bitmap |= bool(vendor === 'Google Inc.' && /SwiftShader/.test(renderer)) << 14;
                }
            }
        } catch {}

        try {
            bitmap |= bool(!('bluetooth' in nav) &&
                /Chrome\/[89]\d|Chrome\/1[0-2]\d/.test(ua)) << 15;
        } catch {}

        return bitmap;
    };

    const collectBotDetectionSb1 = () => {
        const nav = navigator, w = window, d = document;
        const ua = nav.userAgent || '';
        let bitmap = 0;

        try {
            for (const iframe of d.querySelectorAll('iframe[srcdoc]')) {
                if (/webdriver|navigator|defineProperty/.test(iframe.srcdoc)) {
                    bitmap |= 1; break;
                }
            }
        } catch {}

        try {
            bitmap |= bool(Object.getOwnPropertyNames(nav).includes('webdriver')) << 1;
        } catch {}

        try {
            bitmap |= bool(/pptr:|playwright|__puppeteer_evaluation_script__/
                .test(new Error().stack || '')) << 2;
        } catch {}

        try {
            const times = Array.from({ length: 10 }, () => performance.now());
            const diffs = times.slice(1).map((t, i) => t - times[i]);
            bitmap |= bool(diffs.every(d => d === diffs[0]) && diffs[0] > 0) << 3;
        } catch {}

        try { bitmap |= bool(!('PerformanceObserver' in w) && /Chrome/.test(ua)) << 4; } catch {}

        try {
            const wp = Object.getPrototypeOf(w);
            bitmap |= bool(wp?.constructor?.name === 'Proxy') << 5;
        } catch {}

        try {
            const s = w.screen;
            bitmap |= bool(s.width === s.availWidth && s.height === s.availHeight &&
                s.width > 800) << 6;
        } catch {}

        try {
            bitmap |= bool(!nav.mediaDevices && /Chrome/.test(ua) && !/Android/.test(ua)) << 7;
        } catch {}

        try { bitmap |= bool(nav.connection?.rtt === 0) << 8; } catch {}
        try { bitmap |= bool(/Chrome/.test(ua) && w.chrome && !w.chrome.app) << 9; } catch {}

        try {
            bitmap |= bool(Object.keys(d).some(k =>
                k.includes('cdc') || k.includes('selenium'))) << 10;
        } catch {}

        try {
            const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(nav), 'webdriver');
            if (desc?.get) {
                const src = desc.get.toString();
                bitmap |= bool(src.length < 30 || /return\s*(false|!1)/.test(src)) << 11;
            }
        } catch {}

        try {
            bitmap |= bool(/HeadlessChrome|Headless/.test(ua) && nav.plugins?.length > 0) << 12;
        } catch {}

        try { bitmap |= bool(!w.clientInformation && /Chrome/.test(ua)) << 13; } catch {}

        try {
            if (nav.permissions) {
                const proto = Object.getPrototypeOf(nav.permissions);
                bitmap |= bool(!proto || proto.constructor.name !== 'Permissions') << 14;
            }
        } catch {}

        try {
            if ('deviceMemory' in nav) {
                const valid = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64];
                bitmap |= bool(!valid.includes(nav.deviceMemory)) << 15;
            }
        } catch {}

        return bitmap;
    };

    const collectBotDetectionSb2 = () => {
        const nav = navigator, w = window, d = document;
        const ua = nav.userAgent || '';
        let bitmap = 0;

        try {
            const proto = Object.getPrototypeOf(nav);
            const desc = Object.getOwnPropertyDescriptor(proto, 'webdriver');
            if (desc?.get) bitmap |= bool(desc.get.call(nav) === undefined);
        } catch {}

        try {
            const proto = Object.getPrototypeOf(nav);
            bitmap |= bool(Reflect.get(proto, 'webdriver', nav) === undefined) << 1;
        } catch {}

        try {
            const mq = w.matchMedia('(pointer: fine)');
            bitmap |= bool(!mq.matches && !('ontouchstart' in w)) << 2;
        } catch {}

        try {
            if ('Notification' in w)
                bitmap |= bool(!Notification.toString().includes('[native code]')) << 3;
        } catch {}

        try {
            const entries = performance.getEntriesByType('navigation');
            if (entries.length > 0) {
                const timing = entries[0];
                bitmap |= bool(timing.domContentLoadedEventStart === 0) << 5;
                bitmap |= bool(timing.loadEventStart === 0 && d.readyState === 'complete') << 6;
            }
        } catch {}

        try {
            const consoleHelpers = ['$', '$$', '$x', '$0', '$1', '$2', '$3', '$4'];
            const count = consoleHelpers.filter(p => p in w && typeof w[p] === 'function').length;
            bitmap |= bool(count >= 6) << 7;
        } catch {}

        try {
            const cdcProps = Object.getOwnPropertyNames(w).filter(p =>
                /cdc|_selenium|_webdriver|\$cdc|domAutomation/.test(p));
            bitmap |= bool(cdcProps.length > 0) << 8;
        } catch {}

        try {
            const wpKeys = Object.getOwnPropertyNames(Object.getPrototypeOf(w));
            bitmap |= bool(wpKeys.some(k => k.includes('cdc') || k.includes('selenium'))) << 9;
        } catch {}

        try {
            bitmap |= bool('isExtended' in screen && !screen.isExtended &&
                screen.width > 1920) << 10;
        } catch {}

        try { bitmap |= bool(!('SharedWorker' in w) && /Chrome/.test(ua)) << 11; } catch {}

        try {
            if ('BroadcastChannel' in w) new BroadcastChannel('test').close();
            else bitmap |= bool(/Chrome/.test(ua)) << 12;
        } catch { bitmap |= 1 << 12; }

        const chromeVersionPattern = /Chrome\/[89]\d|Chrome\/1[0-2]\d/;
        try { bitmap |= bool(!('usb' in nav) && chromeVersionPattern.test(ua)) << 13; } catch {}
        try { bitmap |= bool(!('serial' in nav) && chromeVersionPattern.test(ua)) << 14; } catch {}
        try { bitmap |= bool(!('hid' in nav) && chromeVersionPattern.test(ua)) << 15; } catch {}

        return bitmap;
    };

    const collectData = () => {
        const nav = navigator, w = window;

        const ts = performance.now();
        let r = 0;
        for (let i = 0; i < 10000; i++) r += Math.sqrt(i);
        const calcTime = performance.now() - ts;

        const mouseFlattened = eventData.m.slice(-50).flatMap(p =>
            [Math.round(p[0]), Math.round(p[1]), Math.round(p[2])]);

        let screen = [0, 0, 0, 0, 0];
        try {
            screen = [w.screen.width, w.screen.height, w.screen.colorDepth,
                w.screen.availWidth, w.screen.availHeight];
        } catch {}

        let timezone = 0, touch = 0, docState = 0;
        try { timezone = new Date().getTimezoneOffset(); } catch {}
        try { touch = bool('ontouchstart' in w) | (bool(nav.maxTouchPoints > 0) << 1); } catch {}
        try {
            docState = bool(document.hidden) | (bool(document.hasFocus()) << 1) |
                (bool(document.visibilityState === 'visible') << 2);
        } catch {}

        const dt = detectDevTools();

        return {
            a: collectAutomationBitmaps(),
            n: [nav.platform, nav.plugins?.length || 0, nav.languages?.length || 0,
                bool(nav.cookieEnabled), nav.doNotTrack || '', nav.hardwareConcurrency || 0,
                nav.languages ? [...nav.languages] : []],
            c: collectCanvasWebGLAudio(),
            f: collectFeaturesBitmap(),
            t: [calcTime, performance.now()],
            x: collectTamperingBitmap(),
            p: collectPropertyIntegrity(),
            e: collectPerformanceStats(),
            m: [eventData.m.length, eventData.c.length, eventData.k, mouseFlattened,
                eventData.s.length, eventData.f],
            d: [dt.bitmap, dt.widthDiff, dt.heightDiff, dt.openCount, bool(dt.wasOpen)],
            s: screen,
            z: [timezone, touch, docState, eventData.v],
            b: [collectBotDetectionSb0(), collectBotDetectionSb1(), collectBotDetectionSb2()]
        };
    };

    const setupTracking = () => {
        Object.assign(eventData, { m: [], c: [], k: 0, s: [], f: 0, v: 0, r: [], t: Date.now() });

        const handlers = {
            mousemove: e => {
                if (!tracking) return;
                eventData.m.push([e.clientX, e.clientY, Date.now() - startTime]);
                if (eventData.m.length > MAX_MOUSE) eventData.m.shift();
                eventData.t = Date.now();
            },
            mousedown: e => {
                if (!tracking) return;
                eventData.c.push([e.clientX, e.clientY, Date.now() - startTime, e.button]);
                eventData.t = Date.now();
            },
            keydown: () => { if (tracking) { eventData.k++; eventData.t = Date.now(); } },
            scroll: () => {
                if (!tracking) return;
                eventData.s.push([window.scrollY, Date.now() - startTime]);
                if (eventData.s.length > 50) eventData.s.shift();
            },
            focus: () => { if (tracking) eventData.f++; },
            blur: () => { if (tracking) eventData.f++; },
            visibilitychange: () => { if (tracking) eventData.v++; },
            resize: () => {
                if (!tracking) return;
                eventData.r.push([window.innerWidth, window.innerHeight, Date.now() - startTime]);
                if (eventData.r.length > 20) eventData.r.shift();
            }
        };

        const docEvents = ['mousemove', 'mousedown', 'keydown', 'scroll', 'visibilitychange'];
        const winEvents = ['focus', 'blur', 'resize'];

        docEvents.forEach(e => document.addEventListener(e, handlers[e], { passive: true }));
        winEvents.forEach(e => window.addEventListener(e, handlers[e]));

        return () => {
            docEvents.forEach(e => document.removeEventListener(e, handlers[e]));
            winEvents.forEach(e => window.removeEventListener(e, handlers[e]));
        };
    };

    const init = () => {
        if (tracking) return;
        startTime = Date.now();
        tracking = true;
        cleanup = setupTracking();
        monitorDevTools();
    };

    const verify = async (siteKey, endpoint = '') => {
        if (!tracking) init();
        const elapsed = Date.now() - startTime;
        if (elapsed < MIN_TIME) await new Promise(r => setTimeout(r, MIN_TIME - elapsed));

        const response = await fetch(`${endpoint || window.location.origin}/captcha/passive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ site_key: siteKey, d: collectData() })
        });

        if (!response.ok) throw new Error(`Status: ${response.status}`);
        return response.json();
    };

    const stop = () => { cleanup?.(); cleanup = null; tracking = false; };

    const IAmPassive = {
        init, verify, cleanup: stop,
        isActive: () => tracking,
        getStats: () => ({
            mouseMovements: eventData.m.length, mouseClicks: eventData.c.length,
            keyPresses: eventData.k, scrollEvents: eventData.s.length,
            trackingDuration: tracking ? Date.now() - startTime : 0
        }),
        version: '2.1.0'
    };

    document.readyState === 'loading'
        ? document.addEventListener('DOMContentLoaded', init) : init();

    global.IAmPassive = IAmPassive;
    if (typeof module === 'object' && module.exports) module.exports = IAmPassive;
})(typeof window !== 'undefined' ? window : this);
