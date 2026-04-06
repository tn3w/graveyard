var QJSModule = (() => {
    var _scriptName = globalThis.document?.currentScript?.src;
    return async function (moduleArg = {}) {
        var moduleRtn;
        var e = moduleArg,
            k = './this.program',
            l = '',
            m;
        try {
            l = new URL('.', _scriptName).href;
        } catch {}
        m = async (a) => {
            a = await fetch(a, { credentials: 'same-origin' });
            if (a.ok) return a.arrayBuffer();
            throw Error(a.status + ' : ' + a.url);
        };
        var n = console.error.bind(console),
            p,
            q = !1,
            r,
            t,
            u,
            v,
            w,
            x,
            y = !1;
        function z(a) {
            e.onAbort?.(a);
            a = 'Aborted(' + a + ')';
            n(a);
            q = !0;
            a = new WebAssembly.RuntimeError(a + '. Build with -sASSERTIONS for more info.');
            u?.(a);
            throw a;
        }
        var A;
        async function B(a) {
            if (!p)
                try {
                    var b = await m(a);
                    return new Uint8Array(b);
                } catch {}
            if (a == A && p) a = new Uint8Array(p);
            else throw 'both async and sync fetching of the wasm failed';
            return a;
        }
        async function C(a, b) {
            try {
                var c = await B(a);
                return await WebAssembly.instantiate(c, b);
            } catch (d) {
                (n(`failed to asynchronously prepare wasm: ${d}`), z(d));
            }
        }
        async function D(a) {
            var b = A;
            if (!p)
                try {
                    var c = fetch(b, { credentials: 'same-origin' });
                    return await WebAssembly.instantiateStreaming(c, a);
                } catch (d) {
                    (n(`wasm streaming compile failed: ${d}`),
                        n('falling back to ArrayBuffer instantiation'));
                }
            return C(b, a);
        }
        class E {
            name = 'ExitStatus';
            constructor(a) {
                this.message = `Program terminated with exit(${a})`;
                this.status = a;
            }
        }
        var F = (a) => {
                for (; 0 < a.length; ) a.shift()(e);
            },
            G = [],
            H = [],
            I = () => {
                var a = e.preRun.shift();
                H.push(a);
            },
            J = !0,
            K = globalThis.TextDecoder && new TextDecoder(),
            L = (a = 0, b, c) => {
                var d = v;
                var f = a;
                b = f + b;
                if (c) c = b;
                else {
                    for (; d[f] && !(f >= b); ) ++f;
                    c = f;
                }
                if (16 < c - a && d.buffer && K) return K.decode(d.subarray(a, c));
                for (f = ''; a < c; )
                    if (((b = d[a++]), b & 128)) {
                        var h = d[a++] & 63;
                        if (192 == (b & 224)) f += String.fromCharCode(((b & 31) << 6) | h);
                        else {
                            var g = d[a++] & 63;
                            b =
                                224 == (b & 240)
                                    ? ((b & 15) << 12) | (h << 6) | g
                                    : ((b & 7) << 18) | (h << 12) | (g << 6) | (d[a++] & 63);
                            65536 > b
                                ? (f += String.fromCharCode(b))
                                : ((b -= 65536),
                                  (f += String.fromCharCode(
                                      55296 | (b >> 10),
                                      56320 | (b & 1023)
                                  )));
                        }
                    } else f += String.fromCharCode(b);
                return f;
            },
            M = 0,
            aa = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
            ba = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
            N = {},
            O = (a) => {
                if (!(a instanceof E || 'unwind' == a)) throw a;
            },
            P = (a) => {
                r = a;
                J || 0 < M || (e.onExit?.(a), (q = !0));
                throw new E(a);
            },
            ca = (a) => {
                if (!q)
                    try {
                        a();
                    } catch (b) {
                        O(b);
                    } finally {
                        if (!(J || 0 < M))
                            try {
                                ((r = a = r), P(a));
                            } catch (b) {
                                O(b);
                            }
                    }
            },
            Q = (a, b, c) => {
                var d = v;
                if (!(0 < c)) return 0;
                var f = b;
                c = b + c - 1;
                for (var h = 0; h < a.length; ++h) {
                    var g = a.codePointAt(h);
                    if (127 >= g) {
                        if (b >= c) break;
                        d[b++] = g;
                    } else if (2047 >= g) {
                        if (b + 1 >= c) break;
                        d[b++] = 192 | (g >> 6);
                        d[b++] = 128 | (g & 63);
                    } else if (65535 >= g) {
                        if (b + 2 >= c) break;
                        d[b++] = 224 | (g >> 12);
                        d[b++] = 128 | ((g >> 6) & 63);
                        d[b++] = 128 | (g & 63);
                    } else {
                        if (b + 3 >= c) break;
                        d[b++] = 240 | (g >> 18);
                        d[b++] = 128 | ((g >> 12) & 63);
                        d[b++] = 128 | ((g >> 6) & 63);
                        d[b++] = 128 | (g & 63);
                        h++;
                    }
                }
                d[b] = 0;
                return b - f;
            },
            R = {},
            T = () => {
                if (!S) {
                    var a = {
                            USER: 'web_user',
                            LOGNAME: 'web_user',
                            PATH: '/',
                            PWD: '/',
                            HOME: '/home/web_user',
                            LANG:
                                (globalThis.navigator?.language ?? 'C').replace('-', '_') +
                                '.UTF-8',
                            _: k || './this.program',
                        },
                        b;
                    for (b in R) void 0 === R[b] ? delete a[b] : (a[b] = R[b]);
                    var c = [];
                    for (b in a) c.push(`${b}=${a[b]}`);
                    S = c;
                }
                return S;
            },
            S,
            U = (a) => {
                for (var b = 0, c = 0; c < a.length; ++c) {
                    var d = a.charCodeAt(c);
                    127 >= d
                        ? b++
                        : 2047 >= d
                          ? (b += 2)
                          : 55296 <= d && 57343 >= d
                            ? ((b += 4), ++c)
                            : (b += 3);
                }
                return b;
            };
        e.noExitRuntime && (J = e.noExitRuntime);
        e.printErr && (n = e.printErr);
        e.wasmBinary && (p = e.wasmBinary);
        e.thisProgram && (k = e.thisProgram);
        if (e.preInit)
            for (
                'function' == typeof e.preInit && (e.preInit = [e.preInit]);
                0 < e.preInit.length;
            )
                e.preInit.shift()();
        e.UTF8ToString = (a, b, c) => (a ? L(a, b, c) : '');
        var W,
            X,
            Y,
            da = {
                a: (a, b, c, d) =>
                    z(
                        `Assertion failed: ${a ? L(a) : ''}, at: ` +
                            [
                                b ? (b ? L(b) : '') : 'unknown filename',
                                c,
                                d ? (d ? L(d) : '') : 'unknown function',
                            ]
                    ),
                f: () => z(''),
                l: () => {
                    J = !1;
                    M = 0;
                },
                c: function (a, b) {
                    a = -9007199254740992 > a || 9007199254740992 < a ? NaN : Number(a);
                    a = new Date(1e3 * a);
                    w[b >> 2] = a.getSeconds();
                    w[(b + 4) >> 2] = a.getMinutes();
                    w[(b + 8) >> 2] = a.getHours();
                    w[(b + 12) >> 2] = a.getDate();
                    w[(b + 16) >> 2] = a.getMonth();
                    w[(b + 20) >> 2] = a.getFullYear() - 1900;
                    w[(b + 24) >> 2] = a.getDay();
                    var c = a.getFullYear();
                    w[(b + 28) >> 2] =
                        ((0 !== c % 4 || (0 === c % 100 && 0 !== c % 400) ? ba : aa)[a.getMonth()] +
                            a.getDate() -
                            1) |
                        0;
                    w[(b + 36) >> 2] = -(60 * a.getTimezoneOffset());
                    c = new Date(a.getFullYear(), 6, 1).getTimezoneOffset();
                    var d = new Date(a.getFullYear(), 0, 1).getTimezoneOffset();
                    w[(b + 32) >> 2] = (c != d && a.getTimezoneOffset() == Math.min(d, c)) | 0;
                },
                j: (a, b) => {
                    N[a] && (clearTimeout(N[a].id), delete N[a]);
                    if (!b) return 0;
                    var c = setTimeout(() => {
                        delete N[a];
                        ca(() => X(a, performance.now()));
                    }, b);
                    N[a] = { id: c, A: b };
                    return 0;
                },
                d: (a, b, c, d) => {
                    var f = new Date().getFullYear(),
                        h = new Date(f, 0, 1).getTimezoneOffset();
                    f = new Date(f, 6, 1).getTimezoneOffset();
                    x[a >> 2] = 60 * Math.max(h, f);
                    w[b >> 2] = Number(h != f);
                    b = (g) => {
                        var V = Math.abs(g);
                        return `UTC${0 <= g ? '-' : '+'}${String(Math.floor(V / 60)).padStart(2, '0')}${String(V % 60).padStart(2, '0')}`;
                    };
                    a = b(h);
                    b = b(f);
                    f < h ? (Q(a, c, 17), Q(b, d, 17)) : (Q(a, d, 17), Q(b, c, 17));
                },
                e: () => Date.now(),
                b: () => performance.now(),
                k: () => {
                    z('OOM');
                },
                h: (a, b) => {
                    var c = 0,
                        d = 0,
                        f;
                    for (f of T()) {
                        var h = b + c;
                        x[(a + d) >> 2] = h;
                        c += Q(f, h, Infinity) + 1;
                        d += 4;
                    }
                    return 0;
                },
                i: (a, b) => {
                    var c = T();
                    x[a >> 2] = c.length;
                    a = 0;
                    for (var d of c) a += U(d) + 1;
                    x[b >> 2] = a;
                    return 0;
                },
                m: function (a) {
                    try {
                        var b = (0, eval)(a ? L(a) : '');
                        if (void 0 === b || null === b) return 0;
                        var c = 'object' === typeof b ? JSON.stringify(b) : String(b),
                            d = U(c) + 1,
                            f = W(d);
                        Q(c, f, d);
                        return f;
                    } catch (h) {
                        return 0;
                    }
                },
                g: P,
            },
            Z;
        Z = await (async function () {
            function a(c) {
                c = Z = c.exports;
                W = e._malloc = c.p;
                e._free = c.q;
                e._vm_init = c.r;
                e._vm_destroy = c.s;
                e._vm_exec_bytecode = c.t;
                e._vm_free = c.u;
                X = c.v;
                Y = c.n;
                c = Y.buffer;
                new Int8Array(c);
                new Int16Array(c);
                e.HEAPU8 = v = new Uint8Array(c);
                new Uint16Array(c);
                w = new Int32Array(c);
                x = new Uint32Array(c);
                new Float32Array(c);
                new Float64Array(c);
                new BigInt64Array(c);
                new BigUint64Array(c);
                return Z;
            }
            var b = { a: da };
            if (e.instantiateWasm)
                return new Promise((c) => {
                    e.instantiateWasm(b, (d, f) => {
                        c(a(d, f));
                    });
                });
            A ??= e.locateFile ? e.locateFile('vm.wasm', l) : l + 'vm.wasm';
            return a((await D(b)).instance);
        })();
        (function () {
            function a() {
                e.calledRun = !0;
                if (!q) {
                    y = !0;
                    Z.o();
                    t?.(e);
                    e.onRuntimeInitialized?.();
                    if (e.postRun)
                        for (
                            'function' == typeof e.postRun && (e.postRun = [e.postRun]);
                            e.postRun.length;
                        ) {
                            var b = e.postRun.shift();
                            G.push(b);
                        }
                    F(G);
                }
            }
            if (e.preRun)
                for ('function' == typeof e.preRun && (e.preRun = [e.preRun]); e.preRun.length; )
                    I();
            F(H);
            e.setStatus
                ? (e.setStatus('Running...'),
                  setTimeout(() => {
                      setTimeout(() => e.setStatus(''), 1);
                      a();
                  }, 1))
                : a();
        })();
        y
            ? (moduleRtn = e)
            : (moduleRtn = new Promise((a, b) => {
                  t = a;
                  u = b;
              }));
        return moduleRtn;
    };
})();
if (typeof exports === 'object' && typeof module === 'object') {
    module.exports = QJSModule;
    module.exports.default = QJSModule;
} else if (typeof define === 'function' && define['amd']) define([], () => QJSModule);
