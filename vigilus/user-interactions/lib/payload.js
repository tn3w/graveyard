// Generates the client-side interaction collector script.
// The script is per-challenge with an embedded nonce for HMAC signing.

export function generatePayload(challengeId, nonce, origin) {
    const endpoint = `${origin}/interactions/verify`;

    return `(function(){
"use strict";
var _cid=${JSON.stringify(challengeId)};
var _nonce=${JSON.stringify(nonce)};
var _ep=${JSON.stringify(endpoint)};
var _t0=Date.now();
var _ttfi=0;
var _sent=false;

var MAX_M=500,MAX_C=50,MAX_K=100,MAX_S=200,MAX_TC=300,MAX_SN=200,MAX_EV=500;
var MIN_TIME=3000;

var d={m:[],c:[],k:[],s:[],tc:[],ac:[],gy:[],or:[],ev:[],ttfi:0,dur:0,meta:{}};

// Event type codes for ordering analysis
// 0=mousemove 1=mousedown 2=mouseup 3=click 4=keydown 5=keyup
// 6=scroll 7=touchstart 8=touchmove 9=touchend

function rt(){return Date.now()-_t0;}
function fi(){if(!_ttfi){_ttfi=rt();d.ttfi=_ttfi;}}

// ── Mouse tracking ──
var _lastMx=-1,_lastMy=-1;
document.addEventListener("mousemove",function(e){
    fi();
    if(d.m.length>=MAX_M)d.m.shift();
    d.m.push([e.clientX+e.movementX*0.01,e.clientY+e.movementY*0.01,rt()]);
    if(d.ev.length<MAX_EV)d.ev.push([0,rt()]);
    _lastMx=e.clientX;_lastMy=e.clientY;
},{passive:true});

// ── Click tracking ──
var _downTime=0,_downX=0,_downY=0;
document.addEventListener("mousedown",function(e){
    fi();
    _downTime=rt();_downX=e.clientX;_downY=e.clientY;
    if(d.ev.length<MAX_EV)d.ev.push([1,rt()]);
},{passive:true});

document.addEventListener("mouseup",function(e){
    if(d.ev.length<MAX_EV)d.ev.push([2,rt()]);
},{passive:true});

document.addEventListener("click",function(e){
    fi();
    var now=rt();
    if(d.ev.length<MAX_EV)d.ev.push([3,now]);
    if(d.c.length>=MAX_C)return;

    var dwell=_downTime?now-_downTime:0;
    var rect=e.target?e.target.getBoundingClientRect():null;
    if(rect&&rect.width>0&&rect.height>0){
        var cx=rect.left+rect.width/2;
        var cy=rect.top+rect.height/2;
        // [offsetX, offsetY, dwell, targetW, targetH, clickTime]
        d.c.push([e.clientX-cx,e.clientY-cy,dwell,rect.width,rect.height,now]);
    }else{
        d.c.push([0,0,dwell,0,0,now]);
    }
    _downTime=0;
},{passive:true});

// ── Keystroke tracking ──
var _keyDownTimes={};
var _lastKeyUp=0;
document.addEventListener("keydown",function(e){
    fi();
    if(d.ev.length<MAX_EV)d.ev.push([4,rt()]);
    if(!_keyDownTimes[e.code])_keyDownTimes[e.code]=rt();
},{passive:true});

document.addEventListener("keyup",function(e){
    if(d.ev.length<MAX_EV)d.ev.push([5,rt()]);
    var now=rt();
    var downT=_keyDownTimes[e.code];
    if(downT&&d.k.length<MAX_K){
        var dwell=now-downT;
        var flight=_lastKeyUp?downT-_lastKeyUp:0;
        // [dwell, flight]
        d.k.push([dwell,flight]);
    }
    _lastKeyUp=now;
    delete _keyDownTimes[e.code];
},{passive:true});

// ── Scroll tracking ──
var _lastScrollT=0;
window.addEventListener("scroll",function(){
    fi();
    var now=rt();
    if(d.ev.length<MAX_EV)d.ev.push([6,now]);
    if(d.s.length>=MAX_S){d.s.shift();}
    var dy=window.scrollY-(_lastScrollT?d.s[d.s.length-1]?d.s[d.s.length-1][0]:0:0);
    d.s.push([window.scrollY,dy,now]);
    _lastScrollT=now;
},{passive:true});

// ── Touch tracking ──
function handleTouch(e,code){
    fi();
    if(d.ev.length<MAX_EV)d.ev.push([code,rt()]);
    for(var i=0;i<e.changedTouches.length;i++){
        if(d.tc.length>=MAX_TC)d.tc.shift();
        var t=e.changedTouches[i];
        // [x, y, pressure, radiusX, radiusY, time]
        d.tc.push([t.clientX,t.clientY,t.force||0,t.radiusX||0,t.radiusY||0,rt()]);
    }
}
document.addEventListener("touchstart",function(e){handleTouch(e,7);},{passive:true});
document.addEventListener("touchmove",function(e){handleTouch(e,8);},{passive:true});
document.addEventListener("touchend",function(e){handleTouch(e,9);},{passive:true});

// ── Sensor tracking ──
d.meta.hasTouchScreen="ontouchstart" in window||navigator.maxTouchPoints>0;
d.meta.hasMotionSensors=false;

if(window.DeviceMotionEvent){
    try{
        if(typeof DeviceMotionEvent.requestPermission==="function"){
            // iOS 13+ requires permission
            d.meta.sensorPermissionRequired=true;
        }
    }catch(e){}

    window.addEventListener("devicemotion",function(e){
        d.meta.hasMotionSensors=true;
        var a=e.accelerationIncludingGravity;
        if(a&&d.ac.length<MAX_SN){
            d.ac.push([a.x||0,a.y||0,a.z||0,rt()]);
        }
        var r=e.rotationRate;
        if(r&&d.gy.length<MAX_SN){
            d.gy.push([r.alpha||0,r.beta||0,r.gamma||0,rt()]);
        }
    },{passive:true});
}

if(window.DeviceOrientationEvent){
    window.addEventListener("deviceorientation",function(e){
        if(d.or.length<MAX_SN){
            d.or.push([e.alpha||0,e.beta||0,e.gamma||0,rt()]);
        }
    },{passive:true});
}

// ── HMAC + Submit ──
async function hmacSign(key,message){
    var enc=new TextEncoder();
    var cryptoKey=await crypto.subtle.importKey("raw",enc.encode(key),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
    var sig=await crypto.subtle.sign("HMAC",cryptoKey,enc.encode(message));
    return Array.from(new Uint8Array(sig)).map(function(b){return b.toString(16).padStart(2,"0");}).join("");
}

async function submit(){
    if(_sent)return null;
    _sent=true;

    d.dur=rt();

    var body=JSON.stringify({cid:_cid,d:d,ts:Date.now()});
    var sig=await hmacSign(_nonce,body);

    try{
        var res=await fetch(_ep,{
            method:"POST",
            headers:{"Content-Type":"application/json","X-Signature":sig},
            body:body
        });
        if(!res.ok)throw new Error("Status: "+res.status);
        var result=await res.json();
        if(window.__interactionResult)window.__interactionResult(result);
        return result;
    }catch(e){
        _sent=false;
        throw e;
    }
}

// ── Auto-submit logic ──
function hasEnoughData(){
    var elapsed=rt();
    if(elapsed<MIN_TIME)return false;

    // Need at least SOME interaction data
    var hasInput=d.m.length>=10||d.tc.length>=5||d.k.length>=3||d.s.length>=3;
    return hasInput;
}

var _checkInterval=setInterval(function(){
    if(hasEnoughData()&&!_sent){
        clearInterval(_checkInterval);
        submit();
    }
},500);

// Also submit after 15s regardless (timeout fallback)
setTimeout(function(){
    if(!_sent){
        clearInterval(_checkInterval);
        submit();
    }
},15000);

// Public API
window.__interactionProbe={
    verify:function(){clearInterval(_checkInterval);return submit();},
    isReady:function(){return hasEnoughData();},
    stats:function(){return{mouse:d.m.length,clicks:d.c.length,keys:d.k.length,scroll:d.s.length,touch:d.tc.length,accel:d.ac.length,gyro:d.gy.length,orient:d.or.length,events:d.ev.length,elapsed:rt()};},
    version:"1.0.0"
};

})();`;
}
