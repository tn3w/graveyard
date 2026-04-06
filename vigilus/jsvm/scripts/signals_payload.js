(function () {
    var t0 = __vm_ts();

    var tGate = __vm_ts();
    if (tGate - t0 > 5000) return JSON.stringify({ e: 'timing' });

    var __rn = '__ROTATION_NONCE__';
    var __sk = '__SIGNING_KEY__';

    var _trap0 = __vm_trap();

    var _cc0 = __vm_ccode();
    __vm_csum(0, 256);

    function h(expr) {
        try {
            return __vm_host(expr);
        } catch (_) {
            return null;
        }
    }

    function hNum(expr) {
        var r = h(expr);
        if (r === null) return -1;
        return parseInt(r, 10) || 0;
    }

    function hBool(expr) {
        return h(expr) === 'true';
    }

    function hJSON(expr) {
        var r = h(expr);
        if (!r || r === 'null' || r === 'undefined') return null;
        try {
            return JSON.parse(r);
        } catch (_) {
            return null;
        }
    }

    function _rotr(x, n) {
        return ((x >>> n) | (x << (32 - n))) >>> 0;
    }

    function _sha256(data) {
        var K = [
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
            0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
            0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
            0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
            0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
            0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
            0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
            0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
            0xc67178f2,
        ];
        var H0 = 0x6a09e667,
            H1 = 0xbb67ae85,
            H2 = 0x3c6ef372,
            H3 = 0xa54ff53a,
            H4 = 0x510e527f,
            H5 = 0x9b05688c,
            H6 = 0x1f83d9ab,
            H7 = 0x5be0cd19;
        var bitLen = data.length * 8;
        var padLen = (data.length + 9 + 63) & ~63;
        var p = new Uint8Array(padLen);
        for (var i = 0; i < data.length; i++) p[i] = data[i];
        p[data.length] = 0x80;
        p[padLen - 4] = (bitLen >>> 24) & 0xff;
        p[padLen - 3] = (bitLen >>> 16) & 0xff;
        p[padLen - 2] = (bitLen >>> 8) & 0xff;
        p[padLen - 1] = bitLen & 0xff;
        var W = new Array(64);
        for (var off = 0; off < padLen; off += 64) {
            for (var i = 0; i < 16; i++) {
                W[i] =
                    ((p[off + i * 4] << 24) |
                        (p[off + i * 4 + 1] << 16) |
                        (p[off + i * 4 + 2] << 8) |
                        p[off + i * 4 + 3]) >>>
                    0;
            }
            for (var i = 16; i < 64; i++) {
                var s0 = _rotr(W[i - 15], 7) ^ _rotr(W[i - 15], 18) ^ (W[i - 15] >>> 3);
                var s1 = _rotr(W[i - 2], 17) ^ _rotr(W[i - 2], 19) ^ (W[i - 2] >>> 10);
                W[i] = (W[i - 16] + s0 + W[i - 7] + s1) >>> 0;
            }
            var a = H0,
                b = H1,
                c = H2,
                d = H3,
                e = H4,
                f = H5,
                g = H6,
                hv = H7;
            for (var i = 0; i < 64; i++) {
                var S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25);
                var ch = (e & f) ^ ((~e >>> 0) & g);
                var t1 = (hv + S1 + ch + K[i] + W[i]) >>> 0;
                var S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22);
                var maj = (a & b) ^ (a & c) ^ (b & c);
                var t2 = (S0 + maj) >>> 0;
                hv = g;
                g = f;
                f = e;
                e = (d + t1) >>> 0;
                d = c;
                c = b;
                b = a;
                a = (t1 + t2) >>> 0;
            }
            H0 = (H0 + a) >>> 0;
            H1 = (H1 + b) >>> 0;
            H2 = (H2 + c) >>> 0;
            H3 = (H3 + d) >>> 0;
            H4 = (H4 + e) >>> 0;
            H5 = (H5 + f) >>> 0;
            H6 = (H6 + g) >>> 0;
            H7 = (H7 + hv) >>> 0;
        }
        var out = new Uint8Array(32);
        var hs = [H0, H1, H2, H3, H4, H5, H6, H7];
        for (var i = 0; i < 8; i++) {
            out[i * 4] = (hs[i] >>> 24) & 0xff;
            out[i * 4 + 1] = (hs[i] >>> 16) & 0xff;
            out[i * 4 + 2] = (hs[i] >>> 8) & 0xff;
            out[i * 4 + 3] = hs[i] & 0xff;
        }
        return out;
    }

    function _hmac(keyBytes, msgBytes) {
        if (keyBytes.length > 64) keyBytes = _sha256(keyBytes);
        var ip = new Uint8Array(64 + msgBytes.length);
        var op = new Uint8Array(64 + 32);
        for (var i = 0; i < 64; i++) {
            var k = i < keyBytes.length ? keyBytes[i] : 0;
            ip[i] = k ^ 0x36;
            op[i] = k ^ 0x5c;
        }
        for (var i = 0; i < msgBytes.length; i++) ip[64 + i] = msgBytes[i];
        var inner = _sha256(ip);
        for (var i = 0; i < 32; i++) op[64 + i] = inner[i];
        return _sha256(op);
    }

    function _s2b(str) {
        var bytes = [];
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 0x80) {
                bytes.push(c);
            } else if (c < 0x800) {
                bytes.push(0xc0 | (c >> 6));
                bytes.push(0x80 | (c & 0x3f));
            } else {
                bytes.push(0xe0 | (c >> 12));
                bytes.push(0x80 | ((c >> 6) & 0x3f));
                bytes.push(0x80 | (c & 0x3f));
            }
        }
        return new Uint8Array(bytes);
    }

    function _h2b(hex) {
        var b = new Uint8Array(hex.length / 2);
        for (var i = 0; i < hex.length; i += 2) b[i / 2] = parseInt(hex.slice(i, i + 2), 16);
        return b;
    }

    function _b64u(bytes) {
        var c = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' + 'abcdefghijklmnopqrstuvwxyz' + '0123456789-_';
        var r = '';
        for (var i = 0; i < bytes.length; i += 3) {
            var b0 = bytes[i],
                b1 = i + 1 < bytes.length ? bytes[i + 1] : 0,
                b2 = i + 2 < bytes.length ? bytes[i + 2] : 0;
            r += c[b0 >> 2];
            r += c[((b0 & 3) << 4) | (b1 >> 4)];
            if (i + 1 < bytes.length) r += c[((b1 & 15) << 2) | (b2 >> 6)];
            if (i + 2 < bytes.length) r += c[b2 & 63];
        }
        return r;
    }

    // a0
    var a0 = hNum(
        '(function(){var b=0,' +
            'w=window,n=navigator,d=document;' +
            'try{if(n.webdriver)b|=1}catch(e){}' +
            'try{if(w.__nightmare)b|=2}catch(e){}' +
            'try{if(w._phantom||w.callPhantom)' +
            'b|=4}catch(e){}' +
            'try{if(w.__selenium_unwrapped)b|=8' +
            '}catch(e){}' +
            'try{if(w._Selenium_IDE_Recorder)' +
            'b|=16}catch(e){}' +
            'try{if(w.domAutomation)b|=32}catch(e){}' +
            'try{if(w.domAutomationController)' +
            'b|=64}catch(e){}' +
            'try{if(d.__webdriver_evaluate||' +
            'w.__webdriver_evaluate)b|=128}catch(e){}' +
            'try{if(w.__selenium_evaluate)' +
            'b|=256}catch(e){}' +
            'try{if(w.__fxdriver_evaluate)' +
            'b|=512}catch(e){}' +
            'try{if(w.__webdriver_unwrapped)' +
            'b|=1024}catch(e){}' +
            'try{if(w.__webdriver_script_fn)' +
            'b|=2048}catch(e){}' +
            'try{if(w.Cypress||w.__cypress)' +
            'b|=(1<<12)}catch(e){}' +
            'try{if(w.__playwright_evaluate||' +
            'w.__playwright_resume||w.playwright)' +
            'b|=(1<<13)}catch(e){}' +
            'try{if(w.__playwright__binding__||' +
            'w.__pwInitScripts)b|=(1<<14)}catch(e){}' +
            'try{if(n.userAgent&&n.userAgent' +
            ".indexOf('HeadlessChrome')>=0)" +
            'b|=(1<<15)}catch(e){}' +
            'try{if(w._headless||n.userAgent' +
            ".toLowerCase().indexOf('headless')>=0)" +
            'b|=(1<<16)}catch(e){}' +
            'try{if(w.Buffer&&typeof w.Buffer' +
            "==='function')b|=(1<<17)}catch(e){}" +
            'return b})()'
    );

    // a1
    var a1 = hNum(
        '(function(){var b=0,' +
            'w=window,n=navigator,d=document;' +
            'try{var wd=Object.getOwnPropertyDescriptor' +
            "(n,'webdriver');" +
            "if(wd){b|=1;if(typeof wd.get==='function')" +
            "b|=2;if('value' in wd)b|=4;" +
            'if(wd.configurable)b|=8;' +
            'if(wd.enumerable)b|=16}}catch(e){}' +
            'try{var cdc=' +
            '/^cdc_|^\\$cdc_|_Array$|_Promise$|_Symbol$' +
            '|_Object$|_Proxy$/;' +
            'b|=(Object.keys(w).some(function(k){' +
            'return cdc.test(k)})?1:0)<<5}catch(e){}' +
            'try{b|=((w.__cdp_binding__||' +
            'w.__chromeSendMessage)?1:0)<<6}catch(e){}' +
            "try{throw new Error('x')}catch(e){" +
            'try{b|=(/selenium|webdriver|puppeteer' +
            '|playwright|cypress/i' +
            ".test(e.stack||'')?1:0)<<7}catch(e2){}}" +
            'try{var np=Object.getPrototypeOf(n),' +
            'wd2=Object.getOwnPropertyDescriptor' +
            "(np,'webdriver');" +
            'if(wd2&&wd2.get&&!wd2.get.toString()' +
            ".includes('[native code]'))b|=1<<9" +
            '}catch(e){}' +
            'try{b|=(d.querySelector(' +
            "'[selenium],[webdriver],[driver]')" +
            '?1:0)<<10}catch(e){}' +
            'try{var fts=Function.prototype.toString' +
            '.call(Function.prototype.toString);' +
            "b|=(!fts.includes('[native code]')" +
            '?1:0)<<11}catch(e){}' +
            'try{b|=((d.documentElement.getAttribute' +
            "('webdriver'))?1:0)<<13}catch(e){}" +
            'try{b|=(Object.getOwnPropertyNames(n)' +
            ".includes('webdriver')?1:0)<<15" +
            '}catch(e){}' +
            'return b})()'
    );

    // a2
    var a2 = hNum(
        '(function(){var b=0,n=navigator;' +
            "b|=('chrome' in window?1:0);" +
            "b|=('permissions' in n?1:0)<<1;" +
            'b|=(n.languages&&n.languages.length>0' +
            '?1:0)<<2;' +
            'try{b|=(!!n.connection?1:0)<<3}catch(e){}' +
            "try{b|=('getBattery' in n?1:0)<<4" +
            '}catch(e){}' +
            "try{b|=('bluetooth' in n?1:0)<<5" +
            '}catch(e){}' +
            "try{b|=('usb' in n?1:0)<<6}catch(e){}" +
            "try{b|=('serial' in n?1:0)<<7}catch(e){}" +
            'return b})()'
    );

    // a3
    var a3 = hNum(
        '(function(){var b=0,' +
            'w=window,n=navigator,d=document;' +
            'try{if(w.awesomium)b|=1}catch(e){}' +
            'try{if(w.RunPerfTest)b|=2}catch(e){}' +
            'try{if(w.CefSharp)b|=4}catch(e){}' +
            'try{if(w.emit&&typeof w.emit' +
            "==='function')b|=8}catch(e){}" +
            'try{if(w.fmget_targets)b|=16}catch(e){}' +
            'try{if(w.geb)b|=32}catch(e){}' +
            'try{if(w.__phantomas)b|=64}catch(e){}' +
            'try{if(w.spawn)b|=128}catch(e){}' +
            'try{if(w.wdioElectron)b|=256}catch(e){}' +
            'try{if(w._selenium||w.calledSelenium)' +
            'b|=512}catch(e){}' +
            'try{if(w._WEBDRIVER_ELEM_CACHE||' +
            'w.ChromeDriverw)b|=1024}catch(e){}' +
            'try{if(d.__driver_evaluate||' +
            'd.__driver_unwrapped)' +
            'b|=2048}catch(e){}' +
            'try{if(d.__webdriver_script_func||' +
            'w.$chrome_asyncScriptInfo||' +
            'w.__$webdriverAsyncExecutor)' +
            'b|=(1<<12)}catch(e){}' +
            'try{if(w.process&&(w.process.type' +
            "==='renderer'||w.process.versions" +
            '&&w.process.versions.electron))' +
            'b|=(1<<13)}catch(e){}' +
            'try{if(w.external&&/Sequentum/i' +
            '.test(w.external.toString()))' +
            'b|=(1<<14)}catch(e){}' +
            'try{b|=(Object.keys(w).some(' +
            'function(k){return' +
            ' /^([a-z]){3}_.*_(Array|Promise' +
            '|Symbol)$/.test(k)})?1:0)<<15' +
            '}catch(e){}' +
            'try{if(/Headless|Electron|SlimerJS/i' +
            '.test(n.appVersion))' +
            'b|=(1<<16)}catch(e){}' +
            'return b})()'
    );

    var h0 = hJSON(
        '(function(){var o={},w=window,' +
            'n=navigator,s=w.screen||{},' +
            'mm=w.matchMedia;' +
            'try{o.pdf_off=n.pdfViewerEnabled' +
            '===false?1:0}catch(e){o.pdf_off=0}' +
            'try{o.no_tb=(s.height===s.availHeight' +
            '&&s.width===s.availWidth)?1:0' +
            '}catch(e){o.no_tb=0}' +
            'try{if(w.visualViewport){' +
            'o.vvp_match=(w.visualViewport.width' +
            '===s.width&&w.visualViewport.height' +
            '===s.height)?1:0}else{o.vvp_match=0}' +
            '}catch(e){o.vvp_match=0}' +
            "try{var ua=n.userAgent||'';" +
            'o.no_share=(/Chrome/.test(ua)&&' +
            "!('share' in n))?1:0" +
            '}catch(e){o.no_share=0}' +
            "try{var dv=document.createElement('div');" +
            "dv.style.display='none';" +
            "dv.style.color='ActiveText';" +
            'document.body.appendChild(dv);' +
            'var clr=getComputedStyle(dv).color;' +
            'document.body.removeChild(dv);' +
            "o.at_red=(clr==='rgb(255, 0, 0)')" +
            '?1:0}catch(e){o.at_red=0}' +
            'try{o.uad_blank=(n.userAgentData&&' +
            "n.userAgentData.platform==='')" +
            '?1:0}catch(e){o.uad_blank=0}' +
            'try{var keys=Object.keys(w);' +
            "var ci=keys.indexOf('chrome');" +
            'o.chrome_pos=(ci>keys.length-50&&' +
            'ci!==-1)?1:0' +
            '}catch(e){o.chrome_pos=0}' +
            'try{var fn=w.chrome&&' +
            'w.chrome.runtime&&' +
            'w.chrome.runtime.sendMessage;' +
            'if(fn){o.rt_proto=' +
            "('prototype' in fn)?1:0" +
            '}else{o.rt_proto=0}' +
            '}catch(e){o.rt_proto=0}' +
            'try{var ifr=document' +
            ".createElement('iframe');" +
            "ifr.srcdoc='';" +
            'o.ifr_proxy=!!ifr.contentWindow' +
            '?1:0}catch(e){o.ifr_proxy=0}' +
            'try{o.plugins_inst=' +
            '(n.plugins instanceof PluginArray)' +
            '?0:1}catch(e){o.plugins_inst=0}' +
            'try{o.mesa=(function(){' +
            "var c=document.createElement('canvas');" +
            "var g=c.getContext('webgl');" +
            'if(!g)return 0;' +
            'var d=g.getExtension' +
            "('WEBGL_debug_renderer_info');" +
            'if(!d)return 0;' +
            'var vn=g.getParameter' +
            "(d.UNMASKED_VENDOR_WEBGL)||'';" +
            'var rn=g.getParameter' +
            "(d.UNMASKED_RENDERER_WEBGL)||'';" +
            "return(vn==='Brian Paul'&&" +
            '/Mesa OffScreen/i.test(rn))?1:0' +
            '})()}catch(e){o.mesa=0}' +
            'return JSON.stringify(o)})()'
    );

    var tMid = __vm_ts();
    if (tMid - tGate > 20000) return JSON.stringify({ e: 'timing' });

    var _trap1 = __vm_trap();

    __vm_csum(256, 256);

    var b0 = hNum(
        '(function(){var b=0,w=window,n=navigator,' +
            "d=document,ua=n.userAgent||'';" +
            'try{b|=(Object.keys(w).some(function(k){' +
            "return k.indexOf('$cdc_')===0||" +
            "k.indexOf('cdc_')===0})?1:0)}catch(e){}" +
            "try{b|=(('__selenium_unwrapped' in w||" +
            "'__selenium_evaluate' in w)?1:0)<<1" +
            '}catch(e){}' +
            'try{if(n.plugins){' +
            'b|=((n.plugins.length===0&&' +
            '!/mobile|android/i.test(ua))?1:0)<<2;' +
            'b|=((Object.prototype.toString.call' +
            "(n.plugins)!=='[object PluginArray]')" +
            '?1:0)<<3;' +
            'b|=((typeof n.plugins.refresh' +
            "!=='function')?1:0)<<4}}catch(e){}" +
            'try{b|=((Object.prototype.toString.call' +
            "(n.mimeTypes)!=='[object MimeTypeArray]')" +
            '?1:0)<<5}catch(e){}' +
            'try{if(n.permissions&&n.permissions.query)' +
            'b|=(!n.permissions.query.toString()' +
            ".includes('[native code]')?1:0)<<6" +
            '}catch(e){}' +
            'try{if(w.chrome){' +
            "var hasCsi=typeof w.chrome.csi==='function';" +
            'var hasLT=typeof w.chrome.loadTimes' +
            "==='function';" +
            'b|=((w.chrome.runtime&&!hasCsi&&!hasLT)' +
            '?1:0)<<7}}catch(e){}' +
            'try{b|=((w.outerWidth===0||' +
            'w.outerHeight===0)?1:0)<<10}catch(e){}' +
            "try{b|=((!('speechSynthesis' in w)&&" +
            '/Chrome/.test(ua))?1:0)<<11}catch(e){}' +
            "try{var gl=d.createElement('canvas')" +
            ".getContext('webgl');" +
            'if(gl){var dbg=gl.getExtension' +
            "('WEBGL_debug_renderer_info');" +
            'if(dbg){var r=gl.getParameter' +
            "(dbg.UNMASKED_RENDERER_WEBGL)||'';" +
            'b|=(/SwiftShader|llvmpipe|softpipe/i' +
            '.test(r)?1:0)<<12}}}catch(e){}' +
            'return b})()'
    );

    var b1 = hNum(
        '(function(){var b=0,w=window,n=navigator,' +
            "d=document,ua=n.userAgent||'';" +
            'try{b|=(Object.getOwnPropertyNames(n)' +
            ".includes('webdriver')?1:0)<<1}catch(e){}" +
            'try{b|=(/pptr:|playwright' +
            '|__puppeteer_evaluation_script__/' +
            ".test(new Error().stack||'')?1:0)<<2" +
            '}catch(e){}' +
            'try{var ts=[];for(var i=0;i<10;i++)' +
            'ts.push(performance.now());' +
            'var df=[];for(var j=1;j<ts.length;j++)' +
            'df.push(ts[j]-ts[j-1]);' +
            'b|=((df.every(function(x){' +
            'return x===df[0]})&&df[0]>0)?1:0)<<3' +
            '}catch(e){}' +
            "try{b|=((!('PerformanceObserver' in w)&&" +
            '/Chrome/.test(ua))?1:0)<<4}catch(e){}' +
            'try{b|=((!n.mediaDevices&&' +
            '/Chrome/.test(ua)&&!/Android/.test(ua))' +
            '?1:0)<<6}catch(e){}' +
            'try{b|=((n.connection&&' +
            'n.connection.rtt===0)?1:0)<<7}catch(e){}' +
            'try{b|=((/Chrome/.test(ua)&&w.chrome&&' +
            '!w.chrome.app)?1:0)<<8}catch(e){}' +
            'try{b|=((Object.keys(d).some(function(k){' +
            "return k.indexOf('cdc')>=0||" +
            "k.indexOf('selenium')>=0}))?1:0)<<9" +
            '}catch(e){}' +
            'try{var desc=Object.getOwnPropertyDescriptor' +
            "(Object.getPrototypeOf(n),'webdriver');" +
            'if(desc&&desc.get){var src=desc.get' +
            '.toString();' +
            'b|=((src.length<30||' +
            '/return\\\\s*(false|!1)/.test(src))' +
            '?1:0)<<10}}catch(e){}' +
            'try{b|=((!w.clientInformation&&' +
            '/Chrome/.test(ua))?1:0)<<12}catch(e){}' +
            "try{if('deviceMemory' in n){" +
            'var vl=[0.25,0.5,1,2,4,8,16,32,64];' +
            'b|=(!vl.includes(n.deviceMemory)' +
            '?1:0)<<14}}catch(e){}' +
            'return b})()'
    );

    var b2 = hNum(
        '(function(){var b=0,w=window,n=navigator,' +
            "d=document,ua=n.userAgent||'';" +
            'try{var pr=Object.getPrototypeOf(n);' +
            'var desc=Object.getOwnPropertyDescriptor' +
            "(pr,'webdriver');" +
            'if(desc&&desc.get)b|=(desc.get.call(n)' +
            '===undefined?1:0)}catch(e){}' +
            "try{var mq=w.matchMedia('(pointer: fine)');" +
            "b|=((!mq.matches&&!('ontouchstart' in w))" +
            '?1:0)<<2}catch(e){}' +
            "try{if('Notification' in w)" +
            'b|=(!Notification.toString()' +
            ".includes('[native code]')?1:0)<<3" +
            '}catch(e){}' +
            'try{var ent=performance' +
            ".getEntriesByType('navigation');" +
            'if(ent.length>0){' +
            'b|=((ent[0].domContentLoadedEventStart' +
            '===0)?1:0)<<4;' +
            'b|=((ent[0].loadEventStart===0&&' +
            "d.readyState==='complete')?1:0)<<5" +
            '}}catch(e){}' +
            'try{var cp=Object.getOwnPropertyNames(w)' +
            '.filter(function(p){' +
            'return /cdc|_selenium|_webdriver' +
            '|\\$cdc|domAutomation/.test(p)});' +
            'b|=((cp.length>0)?1:0)<<7}catch(e){}' +
            "try{b|=((!('SharedWorker' in w)&&" +
            '/Chrome/.test(ua))?1:0)<<10}catch(e){}' +
            'try{var cvp=' +
            '/Chrome\\/[89]\\d|Chrome\\/1[0-2]\\d/;' +
            "b|=((!('usb' in n)&&cvp.test(ua))" +
            '?1:0)<<12;' +
            "b|=((!('serial' in n)&&cvp.test(ua))" +
            '?1:0)<<13;' +
            "b|=((!('hid' in n)&&cvp.test(ua))" +
            '?1:0)<<14}catch(e){}' +
            'return b})()'
    );

    var _tMid2 = __vm_ts();
    if (_tMid2 - tMid > 25000) return JSON.stringify({ e: 'timing' });

    var propRes = hJSON(
        '(function(){var p0=0,ov=0,pi=0,' +
            'n=navigator,w=window;' +
            'try{p0|=(Object.defineProperty.toString()' +
            ".includes('[native code]')?1:0)}catch(e){}" +
            'try{p0|=(Object.getOwnPropertyDescriptor' +
            ".toString().includes('[native code]')" +
            '?1:0)<<1}catch(e){}' +
            "try{if(typeof Reflect!=='undefined')" +
            'p0|=(Reflect.get.toString()' +
            ".includes('[native code]')?1:0)<<2" +
            '}catch(e){}' +
            'try{p0|=(n.toString()' +
            "!=='[object Navigator]'?1:0)<<10" +
            '}catch(e){p0|=1<<11}' +
            'try{p0|=(n[Symbol.toStringTag]' +
            "!=='Navigator'?1:0)<<13}catch(e){}" +
            "try{var props=['userAgent','platform'," +
            "'languages','plugins','webdriver'];" +
            'for(var i=0;i<props.length;i++){' +
            'var d=Object.getOwnPropertyDescriptor' +
            '(Object.getPrototypeOf(n),props[i]);' +
            'if(d&&d.get&&!d.get.toString()' +
            ".includes('[native code]')){" +
            'p0|=1<<14;break}}}catch(e){}' +
            "try{if(typeof Reflect!=='undefined')" +
            'p0|=(!Reflect.get.toString()' +
            ".includes('[native code]')?1:0)<<15" +
            '}catch(e){}' +
            'try{if(Object.getPrototypeOf(n)' +
            ".constructor.name!=='Navigator')" +
            'pi++}catch(e){}' +
            "var cp=['webdriver','plugins','languages'," +
            "'platform','userAgent'];" +
            'for(var j=0;j<cp.length;j++){' +
            'try{var dd=Object.getOwnPropertyDescriptor' +
            '(n,cp[j]);' +
            'if(dd){if(dd.get&&!dd.get.toString()' +
            ".includes('[native code]'))ov++;" +
            "else if('value' in dd)ov++}}catch(e){}}" +
            'return JSON.stringify(' +
            '{p0:p0,ov:ov,pi:pi})})()'
    );
    var p0 = 0,
        p_ov = 0,
        p_pi = 0;
    if (propRes) {
        p0 = propRes.p0 || 0;
        p_ov = propRes.ov || 0;
        p_pi = propRes.pi || 0;
    }

    var x = hNum(
        '(function(){var bm=0;' +
            'var fns=[[Function.prototype.toString,0],' +
            '[setTimeout,1],[setInterval,2],' +
            '[Date.now,3],[Math.random,4],' +
            '[Array.prototype.push,5],' +
            '[JSON.stringify,6],[Object.keys,7],' +
            '[Promise.resolve,8],[Array.from,9]];' +
            'try{fns.push([Reflect.get,10])}catch(e){}' +
            'try{fns.push([console.log,11])}catch(e){}' +
            'fns.forEach(function(pair){' +
            'try{bm|=(pair[0].toString()' +
            ".includes('[native code]')?1:0)" +
            '<<pair[1]}catch(e){}});' +
            'return bm})()'
    );

    var f = hNum(
        '(function(){var b=0,w=window;' +
            "var feats=[['localStorage',0]," +
            "['sessionStorage',1],['WebSocket',2]," +
            "['WebGLRenderingContext',3]," +
            "['WebGL2RenderingContext',4]," +
            "['indexedDB',6],['Notification',7]," +
            "['fetch',8],['Promise',9],['Intl',10]," +
            "['SharedArrayBuffer',11]," +
            "['SharedWorker',12]," +
            "['BroadcastChannel',13]," +
            "['PerformanceObserver',14]," +
            "['IntersectionObserver',15]];" +
            'feats.forEach(function(pair){' +
            'b|=(pair[0] in w?1:0)<<pair[1]});' +
            "b|=(typeof WebAssembly==='object'" +
            '?1:0)<<5;' +
            'return b})()'
    );

    var nav =
        hJSON(
            '(function(){var n=navigator,o={};' +
                "o.ua=n.userAgent||'';" +
                "o.plat=n.platform||'';" +
                'o.pl=n.plugins?n.plugins.length:0;' +
                'o.lang=n.languages?n.languages.length:0;' +
                'o.langs=n.languages?' +
                'Array.from(n.languages):[];' +
                'o.cook=!!n.cookieEnabled;' +
                "o.dnt=n.doNotTrack||'';" +
                'o.hw=n.hardwareConcurrency||0;' +
                'try{o.dm=n.deviceMemory}catch(e){}' +
                'try{o.rtt=n.connection?n.connection.rtt' +
                ':undefined;' +
                'o.dl=n.connection?n.connection.downlink' +
                ':undefined;' +
                'o.ect=n.connection?' +
                'n.connection.effectiveType' +
                ':undefined}catch(e){}' +
                'o.mtp=n.maxTouchPoints||0;' +
                'try{o.pdf=!!n.pdfViewerEnabled}catch(e){}' +
                "o.vd=n.vendor||'';" +
                "o.ps=n.productSub||'';" +
                "o.av=n.appVersion||'';" +
                'try{if(n.userAgentData){' +
                'o.uad_brands=n.userAgentData.brands?' +
                'n.userAgentData.brands.map(function(b){' +
                "return b.brand+'/'+b.version}):[];" +
                'o.uad_mobile=n.userAgentData.mobile;' +
                'o.uad_plat=n.userAgentData.platform' +
                '}}catch(e){}' +
                'return JSON.stringify(o)})()'
        ) || {};

    var scr =
        hJSON(
            '(function(){var s=window.screen||{};' +
                'return JSON.stringify({' +
                'w:s.width||0,h:s.height||0,' +
                'aw:s.availWidth||0,ah:s.availHeight||0,' +
                'cd:s.colorDepth||0,pd:s.pixelDepth||0,' +
                'dpr:window.devicePixelRatio||0,' +
                "ot:s.orientation?s.orientation.type:''," +
                'ie:s.isExtended})})()'
        ) || {};

    var eng =
        hJSON(
            '(function(){var o={};' +
                'try{o.evl=eval.toString().length' +
                '}catch(e){o.evl=-1}' +
                "try{o.stk='unknown';" +
                "try{throw new Error('detect')}" +
                "catch(e){var s=e.stack||'';" +
                "if(s.indexOf(' at ')>=0)o.stk='v8';" +
                "else if(s.indexOf('@')>=0)" +
                "o.stk='spidermonkey';" +
                "else if(s.indexOf('global code')>=0)" +
                "o.stk='jsc'}}catch(e){}" +
                'try{o.math=Math.tan(-1e308)}' +
                'catch(e){o.math=0}' +
                'try{o.acosh=Math.acosh(1e308)}' +
                'catch(e){o.acosh=0}' +
                'try{var fb=Function.prototype.bind;' +
                'o.bind=fb.toString()' +
                ".includes('[native code]')?1:0" +
                '}catch(e){o.bind=-1}' +
                'try{o.ext=typeof window.external}' +
                'catch(e){}' +
                'return JSON.stringify(o)})()'
        ) || {};

    var mq = hJSON(
        '(function(){var w=window,mm=w.matchMedia;' +
            "if(!mm)return'null';" +
            'var q={};' +
            "try{q.hover=mm('(hover: hover)').matches" +
            '}catch(e){}' +
            "try{q.ah=mm('(any-hover: hover)').matches" +
            '}catch(e){}' +
            "try{q.pf=mm('(pointer: fine)').matches" +
            '}catch(e){}' +
            "try{q.pc=mm('(pointer: coarse)').matches" +
            '}catch(e){}' +
            'try{q.dark=mm(' +
            "'(prefers-color-scheme: dark)').matches" +
            '}catch(e){}' +
            'try{q.rm=mm(' +
            "'(prefers-reduced-motion: reduce)').matches" +
            '}catch(e){}' +
            'try{q.hc=mm(' +
            "'(prefers-contrast: more)').matches" +
            '}catch(e){}' +
            'try{q.fc=mm(' +
            "'(forced-colors: active)').matches" +
            '}catch(e){}' +
            'try{q.cg_p3=mm(' +
            "'(color-gamut: p3)').matches" +
            '}catch(e){}' +
            'try{q.cg_srgb=mm(' +
            "'(color-gamut: srgb)').matches" +
            '}catch(e){}' +
            "try{q.touch='ontouchstart' in w" +
            '}catch(e){q.touch=false}' +
            'return JSON.stringify(q)})('
    );

    var dt = hJSON(
        '(function(){var bm=0,' +
            'wd=window.outerWidth-window.innerWidth,' +
            'hd=window.outerHeight-window.innerHeight;' +
            'if(wd>160||hd>160)bm|=1;' +
            'try{var t1=performance.now();' +
            'for(var i=0;i<100;i++){' +
            'console.log;console.clear}' +
            'if(performance.now()-t1>100)bm|=4' +
            '}catch(e){}' +
            'return JSON.stringify(' +
            '{bm:bm,wd:wd,hd:hd,oc:0})})()'
    );

    var env = hJSON(
        '(function(){var w=window,n=navigator,' +
            'd=document,o={};' +
            'try{o.tz=new Date().getTimezoneOffset()}' +
            'catch(e){o.tz=0}' +
            'try{o.tzn=Intl.DateTimeFormat()' +
            ".resolvedOptions().timeZone||''}" +
            "catch(e){o.tzn=''}" +
            "o.touch=('ontouchstart' in w?1:0)|" +
            '((n.maxTouchPoints>0?1:0)<<1);' +
            'o.doc=(d.hidden?1:0)|' +
            '((d.hasFocus()?1:0)<<1)|' +
            "((d.visibilityState==='visible'" +
            '?1:0)<<2);' +
            'try{o.online=n.onLine}catch(e){}' +
            'try{if(n.getBattery){' +
            'o.bat_api=1}else{o.bat_api=0}' +
            '}catch(e){o.bat_api=0}' +
            'return JSON.stringify(o)})('
    );

    var tm = hJSON(
        '(function(){var o=' +
            '{raf:0,pn_identical:false};' +
            'try{var ts=[];' +
            'for(var i=0;i<10;i++)' +
            'ts.push(performance.now());' +
            'var df=[];' +
            'for(var j=1;j<ts.length;j++)' +
            'df.push(ts[j]-ts[j-1]);' +
            'o.pn_identical=df.length>1&&' +
            'df.every(function(d){' +
            'return d===df[0]})&&df[0]>0' +
            '}catch(e){}' +
            'return JSON.stringify(o)})()'
    );

    var gl = hJSON(
        '(function(){var d=document;' +
            "try{var cv=d.createElement('canvas');" +
            "var g=cv.getContext('webgl')||" +
            "cv.getContext('experimental-webgl');" +
            'if(g){var o={};' +
            'var dbg=g.getExtension' +
            "('WEBGL_debug_renderer_info');" +
            'if(dbg){o.vendor=g.getParameter' +
            "(dbg.UNMASKED_VENDOR_WEBGL)||'';" +
            'o.renderer=g.getParameter' +
            "(dbg.UNMASKED_RENDERER_WEBGL)||''}" +
            'o.maxTex=g.getParameter' +
            '(g.MAX_TEXTURE_SIZE);' +
            'o.maxVA=g.getParameter' +
            '(g.MAX_VERTEX_ATTRIBS);' +
            'o.exts=g.getSupportedExtensions()?' +
            'g.getSupportedExtensions().length:0;' +
            'return JSON.stringify(o)}}' +
            'catch(e){}' +
            "return'null'})()"
    );

    var dr = hJSON(
        '(function(){var o=' +
            '{emoji_w:0,emoji_h:0,tm_w:0,' +
            'tm_asc:0,tm_desc:0};' +
            "try{var el=document.createElement('span');" +
            'el.textContent=' +
            "'\\u{1F600}\\u{1F44D}\\u{1F3FD}';" +
            "el.style.cssText='position:absolute;" +
            "left:-9999px;font:16px sans-serif';" +
            'document.body.appendChild(el);' +
            'var r=el.getBoundingClientRect();' +
            'o.emoji_w=r.width;o.emoji_h=r.height;' +
            'document.body.removeChild(el)}catch(e){}' +
            "try{var cv=document.createElement('canvas')" +
            ".getContext('2d');" +
            "if(cv){cv.font='16px monospace';" +
            "var m=cv.measureText('Vigilus');" +
            'o.tm_w=m.width;' +
            'if(m.actualBoundingBoxAscent!==undefined){' +
            'o.tm_asc=m.actualBoundingBoxAscent;' +
            'o.tm_desc=m.actualBoundingBoxDescent}' +
            '}}catch(e){}' +
            'return JSON.stringify(o)})('
    );

    var ch = hJSON(
        '(function(){var n=navigator,' +
            "ua=n.userAgent||'';" +
            'var o={has_uad:false,' +
            'mobile_mismatch:false,' +
            'platform_mismatch:false};' +
            'try{if(n.userAgentData){o.has_uad=true;' +
            'o.mobile_mismatch=' +
            'n.userAgentData.mobile!==' +
            '(n.maxTouchPoints>0&&' +
            '/mobile|android/i.test(ua));' +
            'if(n.userAgentData.platform){' +
            'var plat=n.userAgentData.platform' +
            '.toLowerCase();' +
            'var np=n.platform.toLowerCase();' +
            'o.platform_mismatch=!(' +
            "plat.indexOf('win')>=0&&" +
            "np.indexOf('win')>=0||" +
            "plat.indexOf('mac')>=0&&" +
            "np.indexOf('mac')>=0||" +
            "plat.indexOf('linux')>=0&&" +
            "np.indexOf('linux')>=0||" +
            "plat.indexOf('android')>=0&&" +
            "np.indexOf('linux')>=0||" +
            'plat===np)}}}catch(e){}' +
            'return JSON.stringify(o)})()'
    );

    var sc = hJSON(
        '(function(){var o={},s=window.screen||{},' +
            'mm=window.matchMedia;' +
            'try{if(mm){o.dim_lie=!mm(' +
            "'(device-width:'+s.width+'px)" +
            " and (device-height:'+s.height+'px)')" +
            '.matches?1:0}else{o.dim_lie=0}' +
            '}catch(e){o.dim_lie=0}' +
            'try{if(mm){o.always_light=' +
            "(mm('(prefers-color-scheme: light)')" +
            '.matches&&!mm' +
            "('(prefers-color-scheme: dark)')" +
            '.matches)?1:0}else{o.always_light=0}' +
            '}catch(e){o.always_light=0}' +
            'return JSON.stringify(o)})()'
    );

    var lc = hJSON(
        '(function(){var o={},n=navigator;' +
            'try{var l=n.language,ls=n.languages;' +
            'o.lang_pfx=(ls&&ls.length>0&&' +
            "!ls[0].startsWith(l.split('-')[0]))" +
            '?1:0}catch(e){o.lang_pfx=0}' +
            'try{var f1=(1000).toLocaleString();' +
            'var f2=(1000).toLocaleString(n.language);' +
            'o.locale_lie=(f1!==f2)?1:0' +
            '}catch(e){o.locale_lie=0}' +
            'return JSON.stringify(o)})()'
    );

    var pf = hJSON(
        '(function(){var o={lie_count:0};' +
            'function chk(fn){' +
            'try{Object.setPrototypeOf(fn,fn);' +
            'return true}' +
            'catch(e){return!/chain cycle|Cyclic __proto__/' +
            '.test(e.message)}}' +
            'var targets=[' +
            "['CanvasRenderingContext2D'," +
            "'getImageData']," +
            "['CanvasRenderingContext2D'," +
            "'measureText']," +
            "['HTMLCanvasElement','toDataURL']," +
            "['HTMLCanvasElement','getContext']," +
            "['Element'," +
            "'getBoundingClientRect']," +
            "['Document','createElement']," +
            "['Navigator','hardwareConcurrency']," +
            "['Screen','width']," +
            "['Screen','height']," +
            "['Screen','colorDepth']," +
            "['WebGLRenderingContext'," +
            "'getParameter']];" +
            'for(var i=0;i<targets.length;i++){' +
            'try{var cls=window[targets[i][0]];' +
            'if(!cls||!cls.prototype)continue;' +
            'var d=Object.getOwnPropertyDescriptor' +
            '(cls.prototype,targets[i][1]);' +
            'if(!d)continue;' +
            'var fn=d.get||d.value;' +
            'if(!fn)continue;' +
            'var ts=fn.toString();' +
            "if(!ts.includes('[native code]'))" +
            'o.lie_count++;' +
            'else if(chk(fn))o.lie_count++' +
            '}catch(e){}}' +
            'try{var mt=navigator.mimeTypes;' +
            'o.mt_proto=(Object.getPrototypeOf(mt)' +
            '===MimeTypeArray.prototype)?0:1' +
            '}catch(e){o.mt_proto=0}' +
            'return JSON.stringify(o)})()'
    );

    var css_v = hNum(
        '(function(){' +
            'if(!window.CSS||!CSS.supports)return 0;' +
            'var checks=[' +
            "[115,'scroll-timeline-axis:block']," +
            "[105,':has(*)']," +
            "[100,'text-emphasis-color:initial']," +
            "[95,'accent-color:initial']," +
            "[89,'border-end-end-radius:initial']," +
            "[88,'aspect-ratio:initial']," +
            "[84,'appearance:initial']," +
            "[81,'color-scheme:initial']];" +
            'for(var i=0;i<checks.length;i++){' +
            'try{if(CSS.supports(checks[i][1]))' +
            'return checks[i][0]}catch(e){}}' +
            'return 0})()'
    );

    var cdp = hNum(
        '(function(){var b=0;' +
            'try{var err=new Error();' +
            'var triggered=false;' +
            "Object.defineProperty(err,'stack'," +
            '{get:function(){triggered=true;' +
            "return''}});" +
            'console.log(err);console.clear();' +
            'if(triggered)b=1}catch(e){}' +
            'return b})()'
    );

    var canvasHash =
        h(
            '(function(){' +
                'try{' +
                "var c=document.createElement('canvas');" +
                'c.width=240;c.height=60;' +
                "var x=c.getContext('2d');" +
                "x.textBaseline='alphabetic';" +
                "x.fillStyle='#f60';" +
                'x.fillRect(100,1,62,20);' +
                "x.fillStyle='#069';" +
                "x.font='11pt Arial';" +
                "x.fillText('vigilus,\\ud83d\\ude03',2,15);" +
                "x.fillStyle='rgba(102,204,0,0.7)';" +
                "x.font='18pt Arial';" +
                "x.fillText('vigilus,\\ud83d\\ude03',4,45);" +
                'var d=c.toDataURL();' +
                'var h=0;' +
                'for(var i=0;i<d.length;i++){' +
                'h=((h<<5)-h)+d.charCodeAt(i);h|=0;}' +
                'return h.toString(16);' +
                "}catch(e){return 'err'}" +
                '})()'
        ) || 'err';

    var glVendor =
        h(
            '(function(){try{' +
                "var c=document.createElement('canvas');" +
                "var g=c.getContext('webgl');" +
                "if(!g)return '';" +
                'var d=g.getExtension' +
                "('WEBGL_debug_renderer_info');" +
                'return d?g.getParameter' +
                "(d.UNMASKED_VENDOR_WEBGL):'';" +
                "}catch(e){return ''}})()"
        ) || '';
    var glRenderer =
        h(
            '(function(){try{' +
                "var c=document.createElement('canvas');" +
                "var g=c.getContext('webgl');" +
                "if(!g)return '';" +
                'var d=g.getExtension' +
                "('WEBGL_debug_renderer_info');" +
                'return d?g.getParameter' +
                "(d.UNMASKED_RENDERER_WEBGL):'';" +
                "}catch(e){return ''}})()"
        ) || '';

    var fe = hJSON(
        '(function(){var o={widths:[],count:0};' +
            'try{var cv=document.createElement' +
            "('canvas').getContext('2d');" +
            'if(!cv)return JSON.stringify(o);' +
            "var base='72px monospace';" +
            "var test='mmmmmmmmlli';" +
            'cv.font=base;' +
            'var bw=cv.measureText(test).width;' +
            "var fonts=['Arial','Verdana'," +
            "'Times New Roman','Courier New'," +
            "'Georgia','Palatino','Garamond'," +
            "'Comic Sans MS','Impact'," +
            "'Lucida Console','Tahoma'," +
            "'Trebuchet MS','Helvetica'," +
            "'Segoe UI','Roboto'," +
            "'Ubuntu','Consolas'," +
            "'Menlo','Monaco'," +
            "'Liberation Mono'];" +
            'var w=[];var ct=0;' +
            'for(var i=0;i<fonts.length;i++){' +
            "cv.font='72px '+" +
            "'\"'+fonts[i]+'\",monospace';" +
            'var mw=cv.measureText(test).width;' +
            'w.push(Math.round(mw*100)/100);' +
            'if(mw!==bw)ct++}' +
            'o.widths=w;o.count=ct' +
            '}catch(e){}' +
            'return JSON.stringify(o)})()'
    );
    var vmd = hJSON(
        '(function(){var o={},w=window,' +
            'n=navigator,s=w.screen||{};' +
            'o.sw_gl=0;o.hw_low=0;' +
            'o.vm_res=0;o.vm_audio=0;' +
            'try{var cv=document.createElement' +
            "('canvas');" +
            "var g=cv.getContext('webgl');" +
            'if(g){var d=g.getExtension' +
            "('WEBGL_debug_renderer_info');" +
            'if(d){var r=g.getParameter' +
            '(d.UNMASKED_RENDERER_WEBGL)' +
            "||'';" +
            'var v=g.getParameter' +
            '(d.UNMASKED_VENDOR_WEBGL)' +
            "||'';" +
            'o.sw_gl=(/llvmpipe|softpipe' +
            '|SwiftShader|SVGA3D|VirtualBox' +
            '|VMware|Parallels|QEMU' +
            '|Mesa DRI|Chromium|Microsoft' +
            ' Basic Render/i.test(r)||' +
            '/Brian Paul/i.test(v))?1:0}}}' +
            'catch(e){}' +
            'try{o.hw_low=(n.hardwareConcurrency' +
            '<=2&&(!n.deviceMemory||' +
            'n.deviceMemory<=2))?1:0}catch(e){}' +
            'try{var vr=[[800,600],[1024,768],' +
            '[1280,720],[1280,800],[1280,1024]];' +
            'for(var i=0;i<vr.length;i++){' +
            'if(s.width===vr[i][0]&&' +
            's.height===vr[i][1]&&' +
            's.availHeight===s.height){' +
            'o.vm_res=1;break}}' +
            '}catch(e){}' +
            'try{var ac=new(w.AudioContext||' +
            'w.webkitAudioContext)();' +
            'o.vm_audio=(ac.destination' +
            '.maxChannelCount===0)?1:0;' +
            'ac.close()' +
            '}catch(e){o.vm_audio=0}' +
            'return JSON.stringify(o)})()'
    );
    var ct = hJSON(
        '(function(){var o={rand:0,err:0,' +
            'dl:0,inconsist:0};' +
            "try{var c=document.createElement('canvas');" +
            'c.width=64;c.height=16;' +
            "var x=c.getContext('2d');" +
            "x.fillStyle='#f00';" +
            'x.fillRect(0,0,64,16);' +
            "x.fillStyle='#0f0';x.font='12px Arial';" +
            "x.fillText('test',2,12);" +
            'var d1=c.toDataURL();' +
            'o.dl=d1.length;' +
            "x.fillStyle='#f00';" +
            'x.fillRect(0,0,64,16);' +
            "x.fillStyle='#0f0';x.font='12px Arial';" +
            "x.fillText('test',2,12);" +
            'var d2=c.toDataURL();' +
            'o.rand=(d1!==d2)?1:0;' +
            'var id=x.getImageData(0,0,64,16);' +
            'var allZ=true;' +
            'for(var i=0;i<id.data.length;i+=4){' +
            'if(id.data[i]||id.data[i+1]||' +
            'id.data[i+2]){allZ=false;break}}' +
            'o.inconsist=(d1.length>100&&allZ)?1:0' +
            '}catch(e){o.err=1}' +
            'return JSON.stringify(o)})()'
    );
    var vms = hJSON(
        '(function(){var o={vc:0,md:0,' +
            'ai:0,ao:0,vi:0,rtc:0};' +
            'try{if(window.speechSynthesis){' +
            'var v=speechSynthesis.getVoices();' +
            'o.vc=v?v.length:0}' +
            '}catch(e){}' +
            'try{if(navigator.mediaDevices&&' +
            'navigator.mediaDevices' +
            '.enumerateDevices){' +
            'o.md=1}' +
            '}catch(e){}' +
            'try{o.rtc=!!(window.RTCPeerConnection||' +
            'window.webkitRTCPeerConnection)' +
            '?1:0}catch(e){}' +
            'return JSON.stringify(o)})()'
    );
    var perf = hJSON(
        '(function(){var o={};' +
            'try{if(performance.memory){' +
            'o.jshl=performance.memory' +
            '.jsHeapSizeLimit;' +
            'o.tjhs=performance.memory' +
            '.totalJSHeapSize;' +
            'o.ujhs=performance.memory' +
            '.usedJSHeapSize}' +
            '}catch(e){}' +
            'return JSON.stringify(o)})()'
    );
    var ec = __vm_ec();
    if (ec > 1) return JSON.stringify({ e: 'replay' });

    var _trap2 = __vm_trap();

    var _cc1 = __vm_ccode();
    if (_cc1 !== _cc0) return JSON.stringify({ e: 'tamper' });

    var _chk0 = __vm_chk();

    var t1 = __vm_ts();
    var elapsed = t1 - t0;
    if (elapsed > 60000000) return JSON.stringify({ e: 'timing' });

    var integrity = __vm_integrity();

    var signals = {
        a0: a0,
        a1: a1,
        a2: a2,
        a3: a3,
        b0: b0,
        b1: b1,
        b2: b2,
        p0: p0,
        p_ov: p_ov,
        p_pi: p_pi,
        x: x,
        f: f,
        nav: nav,
        scr: scr,
        eng: eng,
        mq: mq,
        dt: dt,
        env: env,
        tm: tm,
        gl: gl,
        dr: dr,
        ch: ch,
        cdp: cdp,
        h0: h0,
        sc: sc,
        lc: lc,
        pf: pf,
        css_v: css_v,
        cv: canvasHash,
        gl_v: glVendor,
        gl_r: glRenderer,
        fe: fe,
        vmd: vmd,
        ct: ct,
        vms: vms,
        perf: perf,
        cc: _cc0,
        ck: _chk0,
        t: elapsed,
        rn: __rn,
    };

    var json = JSON.stringify({
        s: signals,
        ts: parseInt(h('Date.now()'), 10) || 0,
        i: integrity,
        ec: ec,
    });

    var jsonBytes = _s2b(json);
    var keyBytes = _h2b(__sk);
    var sig = _hmac(keyBytes, jsonBytes);
    return _b64u(jsonBytes) + '.' + _b64u(sig);
})();
