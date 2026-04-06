// Polymorphic JS Payload Generator
// Generates a unique, self-contained JS file per challenge with:
//   1. Comprehensive browser signal collection
//   2. Nonce hidden via multiple obfuscation layers (scattered + encoded)
//   3. Client-side HMAC signing with the nonce
//   4. Submission to verification endpoint
//
// The nonce (64 hex chars) is split into 8 fragments of 8 chars each.
// Each fragment is encoded with a randomly chosen method and scattered
// throughout the code. Variable names are randomized per generation.

import crypto from 'crypto';

// ── Random Name Generation ──

const ALPHA = 'abcdefghijklmnopqrstuvwxyz';
const ALPHA_NUM = ALPHA + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

function rndName(len = 6) {
    let s = ALPHA[Math.floor(Math.random() * ALPHA.length)];
    for (let i = 1; i < len; i++) s += ALPHA_NUM[Math.floor(Math.random() * ALPHA_NUM.length)];
    return '_' + s;
}

function rndNames(count) {
    const names = new Set();
    while (names.size < count) names.add(rndName(4 + Math.floor(Math.random() * 6)));
    return [...names];
}

// ── Nonce Fragment Encoding Methods ──

function xorHex(a, b) {
    let r = '';
    for (let i = 0; i < a.length; i++) {
        r += (parseInt(a[i], 16) ^ parseInt(b[i], 16)).toString(16);
    }
    return r;
}

function rndHex(len) {
    return crypto
        .randomBytes(Math.ceil(len / 2))
        .toString('hex')
        .slice(0, len);
}

// Each method returns { decls: [code lines], expr: expression that yields the fragment }
const encoders = [
    // Method 0: XOR pair
    function xorPair(fragment) {
        const key = rndHex(fragment.length);
        const encoded = xorHex(fragment, key);
        const vk = rndName(),
            ve = rndName();
        return {
            decls: [`const ${vk}="${key}";`, `const ${ve}="${encoded}";`],
            expr: `${ve}.split("").map((c,i)=>(parseInt(c,16)^parseInt(${vk}[i],16)).toString(16)).join("")`,
        };
    },
    // Method 1: Char code array
    function charCodes(fragment) {
        const codes = [...fragment].map((c) => c.charCodeAt(0));
        const va = rndName();
        return {
            decls: [`const ${va}=[${codes.join(',')}];`],
            expr: `${va}.map(c=>String.fromCharCode(c)).join("")`,
        };
    },
    // Method 2: Base64
    function base64(fragment) {
        const b64 = Buffer.from(fragment).toString('base64');
        const vb = rndName();
        return {
            decls: [`const ${vb}="${b64}";`],
            expr: `atob(${vb})`,
        };
    },
    // Method 3: Reverse string
    function reverse(fragment) {
        const rev = [...fragment].reverse().join('');
        const vr = rndName();
        return {
            decls: [`const ${vr}="${rev}";`],
            expr: `${vr}.split("").reverse().join("")`,
        };
    },
    // Method 4: Math derivation (pairs of numbers that XOR to fragment bytes)
    function mathDerive(fragment) {
        const pairs = [];
        for (let i = 0; i < fragment.length; i += 2) {
            const val = parseInt(fragment.slice(i, i + 2), 16);
            const a = Math.floor(Math.random() * 256);
            const b = a ^ val;
            pairs.push([a, b]);
        }
        const va = rndName();
        return {
            decls: [`const ${va}=[[${pairs.map((p) => p.join(',')).join('],[')}]];`],
            expr: `${va}.map(p=>(p[0]^p[1]).toString(16).padStart(2,"0")).join("")`,
        };
    },
    // Method 5: String slice from decoy
    function stringSlice(fragment) {
        const pre = rndHex(Math.floor(Math.random() * 8) + 2);
        const post = rndHex(Math.floor(Math.random() * 8) + 2);
        const full = pre + fragment + post;
        const vs = rndName();
        return {
            decls: [`const ${vs}="${full}";`],
            expr: `${vs}.slice(${pre.length},${pre.length + fragment.length})`,
        };
    },
    // Method 6: Split interleave
    function interleave(fragment) {
        let even = '',
            odd = '';
        for (let i = 0; i < fragment.length; i++) {
            if (i % 2 === 0) even += fragment[i];
            else odd += fragment[i];
        }
        const ve = rndName(),
            vo = rndName();
        return {
            decls: [`const ${ve}="${even}";`, `const ${vo}="${odd}";`],
            expr: `Array.from({length:${fragment.length}},(q,i)=>i%2===0?${ve}[i/2]:${vo}[(i-1)/2]).join("")`,
        };
    },
    // Method 7: Char shift
    function charShift(fragment) {
        const shift = Math.floor(Math.random() * 10) + 1;
        const shifted = [...fragment]
            .map((c) => String.fromCharCode(c.charCodeAt(0) + shift))
            .join('');
        const vsh = rndName();
        return {
            decls: [`const ${vsh}="${escapeJS(shifted)}";`],
            expr: `${vsh}.split("").map(c=>String.fromCharCode(c.charCodeAt(0)-${shift})).join("")`,
        };
    },
];

function escapeJS(s) {
    return s
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r');
}

// ── Signal Collector Code Sections ──
// Each returns a JS code block that populates a part of the signals object.
// Variable name `S` is the signals accumulator (renamed per generation).

function sectionAutomation(S) {
    return `
// Automation detection
(()=>{const w=window,n=navigator,d=document,ua=n.userAgent||"";
let a0=0,a1=0,a2=0;
const ap=["callPhantom","_phantom","__nightmare","domAutomation",
"domAutomationController","_selenium","selenium","webdriver",
"__webdriver_script_fn","__driver_evaluate","__webdriver_evaluate",
"_Selenium_IDE_Recorder","__fxdriver_evaluate","__webdriver_unwrapped",
"__selenium_unwrapped","__selenium_evaluate","phantom"];
ap.forEach((p,i)=>{try{if(w[p])a0|=1<<i}catch{}});
try{a0|=(n.webdriver?1:0)<<17}catch{}
try{a0|=((w._headless||ua.toLowerCase().includes("headless"))?1:0)<<18}catch{}
try{a0|=((w.Cypress||w.__cypress)?1:0)<<19}catch{}
try{a0|=((w.__playwright_evaluate||w.__playwright_resume||w.playwright)?1:0)<<20}catch{}
try{a0|=((w.__playwright__binding__||w.__pwInitScripts)?1:0)<<21}catch{}
try{a0|=(ua.includes("HeadlessChrome")?1:0)<<22}catch{}
try{a0|=((w.Buffer&&typeof w.Buffer==="function")?1:0)<<23}catch{}
try{const wd=Object.getOwnPropertyDescriptor(n,"webdriver");
if(wd){a1|=1;if(typeof wd.get==="function")a1|=2;if("value" in wd)a1|=4;
if(wd.configurable)a1|=8;if(wd.enumerable)a1|=16}}catch{}
try{const cdc=/^cdc_|^\\$cdc_|_Array$|_Promise$|_Symbol$|_Object$|_Proxy$/;
a1|=(Object.keys(w).some(k=>cdc.test(k))?1:0)<<5}catch{}
try{a1|=((w.__cdp_binding__||w.__chromeSendMessage)?1:0)<<6}catch{}
try{throw new Error("x")}catch(e){try{
a1|=(/selenium|webdriver|puppeteer|playwright|cypress/i.test(e.stack||"")?1:0)<<7}catch{}}
try{for(const sc of d.querySelectorAll("script")){
if(!sc.src&&sc.textContent?.includes("Object.defineProperty")&&
sc.textContent.includes("webdriver")&&sc.textContent.includes("navigator")){
a1|=1<<8;break}}}catch{}
try{const np=Object.getPrototypeOf(n),wd2=Object.getOwnPropertyDescriptor(np,"webdriver");
if(wd2?.get&&!wd2.get.toString().includes("[native code]"))a1|=1<<9}catch{}
try{a1|=(d.querySelector("[selenium],[webdriver],[driver]")?1:0)<<10}catch{}
try{const fts=Function.prototype.toString.call(Function.prototype.toString);
a1|=(!fts.includes("[native code]")?1:0)<<11}catch{}
try{a1|=((w.emit&&typeof w.emit==="function")||(w.spawn&&typeof w.spawn==="function")?1:0)<<12}catch{}
try{a1|=((d.documentElement.getAttribute("webdriver"))?1:0)<<13}catch{}
try{a1|=((w.awesomium||w.geb)?1:0)<<14}catch{}
try{a1|=(Object.getOwnPropertyNames(n).includes("webdriver")?1:0)<<15}catch{}
a2|=("chrome" in n?1:0);
a2|=("permissions" in n?1:0)<<1;
a2|=(n.languages?.length>0?1:0)<<2;
try{a2|=(!!n.connection?1:0)<<3}catch{}
try{a2|=("getBattery" in n?1:0)<<4}catch{}
try{a2|=("bluetooth" in n?1:0)<<5}catch{}
try{a2|=("usb" in n?1:0)<<6}catch{}
try{a2|=("serial" in n?1:0)<<7}catch{}
${S}.a0=a0;${S}.a1=a1;${S}.a2=a2})();`;
}

function sectionTampering(S) {
    return `
// Tampering detection
(()=>{let bm=0;const fns=[[Function.prototype.toString,0],[setTimeout,1],[setInterval,2],
[Date.now,3],[Math.random,4],[Array.prototype.push,5],[JSON.stringify,6],[Object.keys,7],
[Promise.resolve,8],[Array.from,9]];
try{fns.push([Reflect.get,10])}catch{}
try{fns.push([console.log,11])}catch{}
fns.forEach(([fn,bit])=>{try{bm|=(fn.toString().includes("[native code]")?1:0)<<bit}catch{}});
${S}.x=bm})();`;
}

function sectionPropertyIntegrity(S) {
    return `
// Property integrity
(()=>{const n=navigator,w=window;let p0=0,ov=0,pi=0;
const nc=[[Object.defineProperty,0],[Object.getOwnPropertyDescriptor,1]];
nc.forEach(([fn,bit])=>{try{p0|=(fn.toString().includes("[native code]")?1:0)<<bit}catch{}});
try{if(typeof Reflect!=="undefined")p0|=(Reflect.get.toString().includes("[native code]")?1:0)<<2}catch{}
try{if(n.permissions?.query){p0|=1<<3;p0|=(n.permissions.query.toString().includes("[native code]")?1:0)<<4}}catch{}
if(w.chrome){p0|=1<<5;try{p0|=(!!w.chrome.app?1:0)<<6}catch{}
try{p0|=(!!w.chrome.runtime?1:0)<<7}catch{}
try{p0|=(typeof w.chrome.csi==="function"?1:0)<<8}catch{}
try{p0|=(typeof w.chrome.loadTimes==="function"?1:0)<<9}catch{}}
try{p0|=(n.toString()!=="[object Navigator]"?1:0)<<10}catch{p0|=1<<11}
try{p0|=(n[Symbol.toStringTag]!=="Navigator"?1:0)<<13}catch{}
try{const props=["userAgent","platform","languages","plugins","webdriver"];
for(const prop of props){const desc=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(n),prop);
if(desc?.get&&!desc.get.toString().includes("[native code]")){p0|=1<<14;break}}}catch{}
try{if(typeof Reflect!=="undefined")p0|=(!Reflect.get.toString().includes("[native code]")?1:0)<<15}catch{}
try{if(Object.getPrototypeOf(n).constructor.name!=="Navigator")pi++}catch{}
["webdriver","plugins","languages","platform","userAgent"].forEach(prop=>{
try{const desc=Object.getOwnPropertyDescriptor(n,prop);
if(desc){if(desc.get&&!desc.get.toString().includes("[native code]"))ov++;
else if("value" in desc)ov++}}catch{}});
${S}.p0=p0;${S}.p_ov=ov;${S}.p_pi=pi})();`;
}

function sectionCanvasWebGLAudio(S) {
    return `
// Canvas, WebGL, Audio
(()=>{const d=document,w=window;let bm=0,cdl=0,glr="",glv="",sr=0;
try{const cv=d.createElement("canvas");const ctx=cv.getContext("2d");
if(ctx){bm|=1;cv.width=200;cv.height=50;ctx.textBaseline="top";ctx.font="14px Arial";
ctx.fillStyle="#f60";ctx.fillRect(10,10,80,30);ctx.fillStyle="#069";
ctx.fillText("Vigilus",20,20);const id=ctx.getImageData(0,0,cv.width,cv.height);
bm|=(id.data.every(p=>p===0)?1:0)<<2;cdl=cv.toDataURL().length}}catch{bm|=1<<1}
try{const cv=d.createElement("canvas");
const gl=cv.getContext("webgl")||cv.getContext("experimental-webgl");
if(gl){bm|=1<<3;glr=gl.getParameter(gl.RENDERER)||"";
const dbg=gl.getExtension("WEBGL_debug_renderer_info");
if(dbg){glr=gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)||glr;
glv=gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)||""}}}catch{bm|=1<<4}
try{const AC=w.AudioContext||w.webkitAudioContext;
if(AC){bm|=1<<5;const ac=new AC();sr=ac.sampleRate;ac.close()}}catch{bm|=1<<6}
${S}.c0=bm;${S}.cdl=cdl;${S}.gl_r=glr;${S}.gl_v=glv;${S}.sr=sr})();`;
}

function sectionFeatures(S) {
    return `
// Features bitmap
(()=>{const w=window;let bm=0;
const feats=[["localStorage",0],["sessionStorage",1],["WebSocket",2],
["WebGLRenderingContext",3],["WebGL2RenderingContext",4],
["indexedDB",6],["Notification",7],["fetch",8],["Promise",9],["Intl",10],
["SharedArrayBuffer",11],["SharedWorker",12],["BroadcastChannel",13],
["PerformanceObserver",14],["IntersectionObserver",15]];
feats.forEach(([p,bit])=>{bm|=(p in w?1:0)<<bit});
bm|=(typeof WebAssembly==="object"?1:0)<<5;
${S}.f=bm})();`;
}

function sectionNavigator(S) {
    return `
// Navigator properties
(()=>{const n=navigator;const o={};
o.ua=n.userAgent||"";o.plat=n.platform||"";
o.pl=n.plugins?.length||0;o.lang=n.languages?.length||0;
o.langs=n.languages?[...n.languages]:[];o.cook=!!n.cookieEnabled;
o.dnt=n.doNotTrack||"";o.hw=n.hardwareConcurrency||0;
try{o.dm=n.deviceMemory}catch{}
try{o.rtt=n.connection?.rtt;o.dl=n.connection?.downlink;o.ect=n.connection?.effectiveType}catch{}
o.mtp=n.maxTouchPoints||0;
try{o.pdf=!!n.pdfViewerEnabled}catch{}
try{if(n.userAgentData){o.uad_brands=n.userAgentData.brands?.map(b=>b.brand+"/"+b.version);
o.uad_mobile=n.userAgentData.mobile;o.uad_plat=n.userAgentData.platform}}catch{}
o.vd=n.vendor||"";o.ps=n.productSub||"";o.av=n.appVersion||"";
${S}.nav=o})();`;
}

function sectionScreen(S) {
    return `
// Screen properties
(()=>{const s=window.screen||{};${S}.scr={
w:s.width||0,h:s.height||0,aw:s.availWidth||0,ah:s.availHeight||0,
cd:s.colorDepth||0,pd:s.pixelDepth||0,dpr:window.devicePixelRatio||0,
ot:s.orientation?.type||"",ie:s.isExtended}})();`;
}

function sectionEnvironment(S) {
    return `
// Environment, timezone, touch, document state
(()=>{const w=window,n=navigator,d=document;const o={};
try{o.tz=new Date().getTimezoneOffset()}catch{o.tz=0}
try{o.tzn=Intl.DateTimeFormat().resolvedOptions().timeZone||""}catch{o.tzn=""}
o.touch=("ontouchstart" in w?1:0)|((n.maxTouchPoints>0?1:0)<<1);
o.doc=(d.hidden?1:0)|((d.hasFocus()?1:0)<<1)|((d.visibilityState==="visible"?1:0)<<2);
o.vc=0;try{o.online=n.onLine}catch{}
try{if("getBattery" in n){n.getBattery().then(b=>{o.bat_l=b.level;o.bat_c=b.charging}).catch(()=>{})}}catch{}
${S}.env=o})();`;
}

function sectionBotDetection(S) {
    return `
// Sophisticated bot detection (SB0/SB1/SB2)
(()=>{const n=navigator,w=window,d=document,ua=n.userAgent||"";
let b0=0,b1=0,b2=0;
// SB0 - Chromium/Selenium
try{b0|=(Object.keys(w).some(k=>k.startsWith("$cdc_")||k.startsWith("cdc_"))?1:0)}catch{}
try{b0|=(("__selenium_unwrapped" in w||"__selenium_evaluate" in w)?1:0)<<1}catch{}
try{if(n.plugins){b0|=((n.plugins.length===0&&!/mobile|android/i.test(ua))?1:0)<<2;
b0|=((Object.prototype.toString.call(n.plugins)!=="[object PluginArray]")?1:0)<<3;
b0|=((typeof n.plugins.refresh!=="function")?1:0)<<4}}catch{}
try{b0|=((Object.prototype.toString.call(n.mimeTypes)!=="[object MimeTypeArray]")?1:0)<<5}catch{}
try{if(n.permissions?.query)b0|=(!n.permissions.query.toString().includes("[native code]")?1:0)<<6}catch{}
try{if(w.chrome){const hasCsi=typeof w.chrome.csi==="function";
const hasLT=typeof w.chrome.loadTimes==="function";
b0|=((w.chrome.runtime&&!hasCsi&&!hasLT)?1:0)<<7;
try{w.chrome.runtime?.connect?.()}catch(e){b0|=(!e.message?.includes("Extension")?1:0)<<8}}}catch{}
try{if("Notification" in w)b0|=((Notification.permission==="denied"&&!d.hidden)?1:0)<<9}catch{}
try{b0|=((w.outerWidth===0||w.outerHeight===0)?1:0)<<10}catch{}
try{b0|=((!("speechSynthesis" in w)&&/Chrome/.test(ua))?1:0)<<11}catch{}
try{const gl=d.createElement("canvas").getContext("webgl");
if(gl){const dbg=gl.getExtension("WEBGL_debug_renderer_info");
if(dbg){const r=gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)||"";
b0|=(/SwiftShader|llvmpipe|softpipe/i.test(r)?1:0)<<12;
const v=gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)||"";
b0|=((v==="Google Inc."&&/SwiftShader/.test(r))?1:0)<<13}}}catch{}
try{b0|=((!("bluetooth" in n)&&/Chrome\\/[89]\\d|Chrome\\/1[0-2]\\d/.test(ua))?1:0)<<14}catch{}
// SB1 - Stealth/Advanced
try{for(const iframe of d.querySelectorAll("iframe[srcdoc]")){
if(/webdriver|navigator|defineProperty/.test(iframe.srcdoc)){b1|=1;break}}}catch{}
try{b1|=(Object.getOwnPropertyNames(n).includes("webdriver")?1:0)<<1}catch{}
try{b1|=(/pptr:|playwright|__puppeteer_evaluation_script__/.test(new Error().stack||"")?1:0)<<2}catch{}
try{const ts=Array.from({length:10},()=>performance.now());
const df=ts.slice(1).map((t,i)=>t-ts[i]);
b1|=((df.every(x=>x===df[0])&&df[0]>0)?1:0)<<3}catch{}
try{b1|=((!("PerformanceObserver" in w)&&/Chrome/.test(ua))?1:0)<<4}catch{}
try{b1|=((Object.getPrototypeOf(w)?.constructor?.name==="Proxy")?1:0)<<5}catch{}
try{b1|=((!n.mediaDevices&&/Chrome/.test(ua)&&!/Android/.test(ua))?1:0)<<6}catch{}
try{b1|=((n.connection?.rtt===0)?1:0)<<7}catch{}
try{b1|=((/Chrome/.test(ua)&&w.chrome&&!w.chrome.app)?1:0)<<8}catch{}
try{b1|=((Object.keys(d).some(k=>k.includes("cdc")||k.includes("selenium")))?1:0)<<9}catch{}
try{const desc=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(n),"webdriver");
if(desc?.get){const src=desc.get.toString();
b1|=((src.length<30||/return\\s*(false|!1)/.test(src))?1:0)<<10}}catch{}
try{b1|=((/HeadlessChrome/.test(ua)&&n.plugins?.length>0)?1:0)<<11}catch{}
try{b1|=((!w.clientInformation&&/Chrome/.test(ua))?1:0)<<12}catch{}
try{if(n.permissions){const pr=Object.getPrototypeOf(n.permissions);
b1|=((!pr||pr.constructor.name!=="Permissions")?1:0)<<13}}catch{}
try{if("deviceMemory" in n){const vl=[0.25,0.5,1,2,4,8,16,32,64];
b1|=(!vl.includes(n.deviceMemory)?1:0)<<14}}catch{}
try{b1|=((!w.clientInformation&&/Chrome/.test(ua))?1:0)<<15}catch{}
// SB2 - Undetected-Chromedriver
try{const pr=Object.getPrototypeOf(n);const desc=Object.getOwnPropertyDescriptor(pr,"webdriver");
if(desc?.get)b2|=(desc.get.call(n)===undefined?1:0)}catch{}
try{const pr=Object.getPrototypeOf(n);b2|=((Reflect.get(pr,"webdriver",n)===undefined)?1:0)<<1}catch{}
try{const mq=w.matchMedia("(pointer: fine)");
b2|=((!mq.matches&&!("ontouchstart" in w))?1:0)<<2}catch{}
try{if("Notification" in w)b2|=(!Notification.toString().includes("[native code]")?1:0)<<3}catch{}
try{const ent=performance.getEntriesByType("navigation");
if(ent.length>0){b2|=((ent[0].domContentLoadedEventStart===0)?1:0)<<4;
b2|=((ent[0].loadEventStart===0&&d.readyState==="complete")?1:0)<<5}}catch{}
try{const ch=["$","$$","$x","$0","$1","$2","$3","$4"];
b2|=((ch.filter(p=>p in w&&typeof w[p]==="function").length>=6)?1:0)<<6}catch{}
try{const cp=Object.getOwnPropertyNames(w).filter(p=>/cdc|_selenium|_webdriver|\\$cdc|domAutomation/.test(p));
b2|=((cp.length>0)?1:0)<<7}catch{}
try{const wp=Object.getOwnPropertyNames(Object.getPrototypeOf(w));
b2|=(wp.some(k=>k.includes("cdc")||k.includes("selenium"))?1:0)<<8}catch{}
try{b2|=(("isExtended" in screen&&!screen.isExtended&&screen.width>1920)?1:0)<<9}catch{}
try{b2|=((!("SharedWorker" in w)&&/Chrome/.test(ua))?1:0)<<10}catch{}
try{if("BroadcastChannel" in w){new BroadcastChannel("t").close()}
else{b2|=(/Chrome/.test(ua)?1:0)<<11}}catch{b2|=1<<11}
const cvp=/Chrome\\/[89]\\d|Chrome\\/1[0-2]\\d/;
try{b2|=((!("usb" in n)&&cvp.test(ua))?1:0)<<12}catch{}
try{b2|=((!("serial" in n)&&cvp.test(ua))?1:0)<<13}catch{}
try{b2|=((!("hid" in n)&&cvp.test(ua))?1:0)<<14}catch{}
${S}.b0=b0;${S}.b1=b1;${S}.b2=b2})();`;
}

function sectionEngine(S) {
    return `
// Engine fingerprint
(()=>{const o={};
try{o.evl=eval.toString().length}catch{o.evl=-1}
try{new Error("x");o.stk="unknown";
try{throw new Error("detect")}catch(e){const s=e.stack||"";
if(s.includes(" at "))o.stk="v8";
else if(s.includes("@"))o.stk="spidermonkey";
else if(s.includes("global code"))o.stk="jsc"}}catch{}
try{o.math=Math.tan(-1e308)}catch{o.math=0}
try{o.acosh=Math.acosh(1e308)}catch{o.acosh=0}
try{o.ext=typeof window.external}catch{o.ext=""}
try{const fb=Function.prototype.bind;o.bind=fb.toString().includes("[native code]")?1:0}catch{o.bind=-1}
${S}.eng=o})();`;
}

function sectionMediaQueries(S) {
    return `
// CSS media queries
(()=>{const w=window,mm=w.matchMedia;if(!mm){${S}.mq=null;return}
const q={};
try{q.hover=mm("(hover: hover)").matches}catch{}
try{q.pf=mm("(pointer: fine)").matches}catch{}
try{q.pc=mm("(pointer: coarse)").matches}catch{}
try{q.ah=mm("(any-hover: hover)").matches}catch{}
try{q.cg_srgb=mm("(color-gamut: srgb)").matches}catch{}
try{q.cg_p3=mm("(color-gamut: p3)").matches}catch{}
try{q.dark=mm("(prefers-color-scheme: dark)").matches}catch{}
try{q.rm=mm("(prefers-reduced-motion: reduce)").matches}catch{}
try{q.hc=mm("(prefers-contrast: more)").matches}catch{}
try{q.fc=mm("(forced-colors: active)").matches}catch{}
try{q.touch="ontouchstart" in w}catch{q.touch=false}
${S}.mq=q})();`;
}

function sectionVoicesMedia(S) {
    return `
// Speech synthesis voices & media devices
(()=>{const o={voices:0,media:0,rtc:!!window.RTCPeerConnection};
try{if("speechSynthesis" in window){const v=speechSynthesis.getVoices();o.voices=v.length}}catch{}
try{if(navigator.mediaDevices?.enumerateDevices){
navigator.mediaDevices.enumerateDevices().then(d=>{
o.media=d.length;o.ai=d.filter(x=>x.kind==="audioinput").length;
o.ao=d.filter(x=>x.kind==="audiooutput").length;
o.vi=d.filter(x=>x.kind==="videoinput").length}).catch(()=>{})}}catch{}
${S}.vm=o})();`;
}

function sectionWorkerConsistency(S) {
    return `
// Worker context consistency check
(()=>{${S}.wk={ua_match:null,hw_match:null,plat_match:null,lang_match:null};
try{const blob=new Blob([\`self.postMessage({
ua:self.navigator.userAgent,hw:self.navigator.hardwareConcurrency,
plat:self.navigator.platform,lang:self.navigator.languages?[...self.navigator.languages]:[]})\`],
{type:"application/javascript"});const url=URL.createObjectURL(blob);
const ww=new Worker(url);ww.onmessage=e=>{const d=e.data;
${S}.wk.ua_match=d.ua===navigator.userAgent;
${S}.wk.hw_match=d.hw===navigator.hardwareConcurrency;
${S}.wk.plat_match=d.plat===navigator.platform;
${S}.wk.lang_match=JSON.stringify(d.lang)===JSON.stringify([...navigator.languages]);
ww.terminate();URL.revokeObjectURL(url)};
ww.onerror=()=>{ww.terminate();URL.revokeObjectURL(url)};
setTimeout(()=>{try{ww.terminate();URL.revokeObjectURL(url)}catch{}},3000)}catch{}})();`;
}

function sectionTiming(S) {
    return `
// Timing analysis
(()=>{const o={raf:0,pn_identical:false};
try{const ts=Array.from({length:10},()=>performance.now());
const df=ts.slice(1).map((t,i)=>t-ts[i]);
o.pn_identical=df.length>1&&df.every(d=>d===df[0])&&df[0]>0}catch{}
try{let prev=0,diffs=[];const count=5;let done=0;
const tick=t=>{if(prev>0)diffs.push(t-prev);prev=t;done++;
if(done<count)requestAnimationFrame(tick);
else{o.raf=diffs.length?diffs.reduce((a,b)=>a+b)/diffs.length:0}};
requestAnimationFrame(tick)}catch{}
${S}.tm=o})();`;
}

function sectionWebGLDeep(S) {
    return `
// WebGL deep fingerprint
(()=>{const d=document;${S}.gl=null;
try{const cv=d.createElement("canvas");
const gl=cv.getContext("webgl")||cv.getContext("experimental-webgl");
if(gl){const o={};const dbg=gl.getExtension("WEBGL_debug_renderer_info");
if(dbg){o.vendor=gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)||"";
o.renderer=gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)||""}
o.maxTex=gl.getParameter(gl.MAX_TEXTURE_SIZE);
o.maxVA=gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
o.maxVV=gl.getParameter(gl.MAX_VARYING_VECTORS);
o.maxRB=gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);
o.exts=gl.getSupportedExtensions()?.length||0;
${S}.gl=o}}catch{}})();`;
}

function sectionDOMRect(S) {
    return `
// DOMRect & TextMetrics fingerprinting
(()=>{const o={emoji_w:0,emoji_h:0,tm_w:0};
try{const el=document.createElement("span");el.textContent="\\u{1F600}\\u{1F44D}\\u{1F3FD}";
el.style.cssText="position:absolute;left:-9999px;font:16px sans-serif";
document.body.appendChild(el);const r=el.getBoundingClientRect();
o.emoji_w=r.width;o.emoji_h=r.height;document.body.removeChild(el)}catch{}
try{const cv=document.createElement("canvas").getContext("2d");
if(cv){cv.font="16px monospace";const m=cv.measureText("Vigilus");
o.tm_w=m.width;o.tm_asc=m.actualBoundingBoxAscent;o.tm_desc=m.actualBoundingBoxDescent}}catch{}
${S}.dr=o})();`;
}

function sectionClientHints(S) {
    return `
// Client Hints consistency
(()=>{const n=navigator,ua=n.userAgent||"";const o={has_uad:false,mobile_mismatch:false,platform_mismatch:false};
try{if(n.userAgentData){o.has_uad=true;
o.mobile_mismatch=n.userAgentData.mobile!==(n.maxTouchPoints>0&&/mobile|android/i.test(ua));
if(n.userAgentData.platform){const plat=n.userAgentData.platform.toLowerCase();
const np=n.platform.toLowerCase();
o.platform_mismatch=!(plat.includes("win")&&np.includes("win")||
plat.includes("mac")&&np.includes("mac")||
plat.includes("linux")&&np.includes("linux")||
plat.includes("android")&&np.includes("linux")||
plat===np)}}}catch{}
${S}.ch=o})();`;
}

function sectionBehavioral(S) {
    return `
// Minimal behavioral snapshot
(()=>{${S}.bhv={mouse:0,keys:0,scroll:0,elapsed:0,start:Date.now()}})();`;
}

function sectionPermissions(S) {
    return `
// Permission consistency
(()=>{${S}.perm={};
try{if("Notification" in window){${S}.perm.notif=Notification.permission;
if(navigator.permissions?.query){navigator.permissions.query({name:"notifications"}).then(r=>{
${S}.perm.notif_q=r.state}).catch(()=>{})}}}catch{}})();`;
}

function sectionPerformanceMemory(S) {
    return `
// Performance memory
(()=>{${S}.perf={};
try{if(performance.memory){${S}.perf.heap=performance.memory.jsHeapSizeLimit;
${S}.perf.total=performance.memory.totalJSHeapSize;
${S}.perf.used=performance.memory.usedJSHeapSize}}catch{}
try{if(navigator.storage?.estimate){navigator.storage.estimate().then(e=>{
${S}.perf.quota=e.quota;${S}.perf.usage=e.usage}).catch(()=>{})}}catch{}})();`;
}

function sectionCDPDetection(S) {
    return `
// CDP detection via console serialization side-effect
(()=>{${S}.cdp=0;
try{const err=new Error();let triggered=false;
Object.defineProperty(err,"stack",{get(){triggered=true;return""}});
console.log(err);console.clear();
if(triggered)${S}.cdp=1}catch{}})();`;
}

// ── All section generators ──
const ALL_SECTIONS = [
    sectionAutomation,
    sectionTampering,
    sectionPropertyIntegrity,
    sectionCanvasWebGLAudio,
    sectionFeatures,
    sectionNavigator,
    sectionScreen,
    sectionEnvironment,
    sectionBotDetection,
    sectionEngine,
    sectionMediaQueries,
    sectionVoicesMedia,
    sectionWorkerConsistency,
    sectionTiming,
    sectionWebGLDeep,
    sectionDOMRect,
    sectionClientHints,
    sectionBehavioral,
    sectionPermissions,
    sectionPerformanceMemory,
    sectionCDPDetection,
];

// ── Decoy Generator ──
function generateDecoys(count) {
    const decoys = [];
    for (let i = 0; i < count; i++) {
        const v = rndName();
        const method = Math.floor(Math.random() * 3);
        if (method === 0) {
            decoys.push(`const ${v}="${rndHex(16)}";`);
        } else if (method === 1) {
            decoys.push(
                `const ${v}=[${Array.from({ length: 8 }, () => Math.floor(Math.random() * 256)).join(',')}];`
            );
        } else {
            const a = rndHex(8),
                b = rndHex(8);
            decoys.push(`const ${v}="${a}"+"${b}";`);
        }
    }
    return decoys;
}

// ── Main Payload Generator ──

export function generatePayload(challengeId, nonce, baseUrl = '') {
    const S = rndName(8); // signals accumulator variable
    const sigVar = rndName(6); // signature variable

    // 1. Split nonce into 8 fragments of 8 hex chars
    const fragments = [];
    for (let i = 0; i < 64; i += 8) {
        fragments.push(nonce.slice(i, i + 8));
    }

    // 2. Encode each fragment with a random method
    const fragVars = rndNames(8);
    const fragCode = []; // { decls: string[], expr: string, varName: string }
    for (let i = 0; i < 8; i++) {
        const encoder = encoders[Math.floor(Math.random() * encoders.length)];
        const encoded = encoder(fragments[i]);
        fragCode.push({ ...encoded, varName: fragVars[i] });
    }

    // 3. Generate section code (shuffled order)
    const shuffled = [...ALL_SECTIONS];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    const sectionCode = shuffled.map((fn) => fn(S));

    // 4. Generate decoys
    const decoys = generateDecoys(12 + Math.floor(Math.random() * 8));

    // 5. Interleave: sections, fragment decls, and decoys
    const allParts = [];

    // Distribute fragment declarations across the code
    const fragDeclBlocks = fragCode.map((fc, i) => {
        const assignment = `const ${fc.varName}=(()=>{${fc.decls.join('')}return ${fc.expr}})();`;
        return assignment;
    });

    // Create interleaving: decoy, section, frag, decoy, section, frag, ...
    let fragIdx = 0,
        decoyIdx = 0;
    for (let i = 0; i < sectionCode.length; i++) {
        if (decoyIdx < decoys.length && Math.random() > 0.4) allParts.push(decoys[decoyIdx++]);
        allParts.push(sectionCode[i]);
        if (fragIdx < fragDeclBlocks.length && (i % 3 === 0 || Math.random() > 0.5))
            allParts.push(fragDeclBlocks[fragIdx++]);
    }
    // Append remaining fragments
    while (fragIdx < fragDeclBlocks.length) {
        if (decoyIdx < decoys.length) allParts.push(decoys[decoyIdx++]);
        allParts.push(fragDeclBlocks[fragIdx++]);
    }
    // Append remaining decoys
    while (decoyIdx < decoys.length) allParts.push(decoys[decoyIdx++]);

    // 6. Build nonce assembly
    const assembleVar = rndName(7);
    const assembleCode = `const ${assembleVar}=${fragVars.join('+')};`;

    // 7. Build signing and submission
    const hexFn = rndName(5);
    const signFn = rndName(6);
    const submitCode = `
const ${hexFn}=b=>Array.from(new Uint8Array(b)).map(x=>x.toString(16).padStart(2,"0")).join("");
async function ${signFn}(nonce,msg){
const k=await crypto.subtle.importKey("raw",new Uint8Array(nonce.match(/.{2}/g).map(h=>parseInt(h,16))),
{name:"HMAC",hash:"SHA-256"},false,["sign"]);
return ${hexFn}(await crypto.subtle.sign("HMAC",k,new TextEncoder().encode(msg)))}
(async()=>{
await new Promise(r=>setTimeout(r,150));
const ts=Date.now();const payload=JSON.stringify(${S});
const msg="${challengeId}:"+ts+":"+payload;
const ${sigVar}=await ${signFn}(${assembleVar},msg);
const res=await fetch("${baseUrl}/signals/verify",{method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({cid:"${challengeId}",s:${S},ts,sig:${sigVar}})});
const result=await res.json();
if(window.__signals_cb)window.__signals_cb(result);
window.__signals_result=result})();`;

    // 8. Assemble full payload
    const payload = `"use strict";(()=>{
const ${S}={};
${allParts.join('\n')}
${assembleCode}
${submitCode}
})();`;

    return payload;
}
