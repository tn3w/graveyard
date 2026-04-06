const UNICODE_CHARS = '\u0394\u2117\u221E\uFB01\uFB02';

async function sha256(data) {
    const buffer = typeof data === 'string' ? new TextEncoder().encode(data) : data;
    const hash = await crypto.subtle.digest('SHA-256', buffer);
    return Array.from(new Uint8Array(hash))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
}

function hexToBytes(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
    }
    return bytes;
}

// --- Stage Solvers ---

async function solveCanvasText(params) {
    const { width, height, seed } = params;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, `#${seed.slice(0, 6)}`);
    gradient.addColorStop(1, `#${seed.slice(6, 12)}`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    ctx.font = '14px Arial';
    ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = '#069';
    ctx.fillText(`${seed.slice(0, 16)}${UNICODE_CHARS}`, 2, 15);

    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText(`${seed.slice(16, 32)}${UNICODE_CHARS}`, 4, 17);

    const arcAngle = (parseInt(seed.slice(0, 8), 16) % 628) / 100;
    ctx.beginPath();
    ctx.arc(140, 50, 25, 0, arcAngle);
    ctx.strokeStyle = '#f60';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(10, 70);
    ctx.bezierCurveTo(
        parseInt(seed.slice(8, 10), 16),
        parseInt(seed.slice(10, 12), 16) % height,
        width - parseInt(seed.slice(12, 14), 16),
        parseInt(seed.slice(14, 16), 16) % height,
        270,
        70
    );
    ctx.stroke();

    const imageData = ctx.getImageData(0, 0, width, height);
    return sha256(imageData.data.buffer);
}

async function solveAudio(params) {
    const { frequency, sampleRate, sliceStart, sliceEnd, seed } = params;
    const AudioCtx = window.OfflineAudioContext || window.webkitOfflineAudioContext;

    if (!AudioCtx) {
        return sha256(`no-audio:${seed}`);
    }

    const ctx = new AudioCtx(1, sampleRate, sampleRate);
    const osc = ctx.createOscillator();
    const comp = ctx.createDynamicsCompressor();

    osc.frequency.value = frequency;
    osc.type = 'triangle';
    comp.threshold.value = -50;
    comp.knee.value = 40;
    comp.ratio.value = 12;
    comp.attack.value = 0;
    comp.release.value = 0.25;

    osc.connect(comp);
    comp.connect(ctx.destination);
    osc.start(0);

    const rendered = await ctx.startRendering();
    const slice = rendered.getChannelData(0).slice(sliceStart, sliceEnd);
    return sha256(slice.buffer);
}

async function solveCanvasGeometry(params) {
    const { width, height, seed } = params;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = `#${seed.slice(0, 6)}`;
    ctx.fillRect(0, 0, width, height);

    const numShapes = 3 + (parseInt(seed.slice(0, 2), 16) % 5);
    for (let i = 0; i < numShapes; i++) {
        const off = (i * 8) % (seed.length - 8);
        const cx = parseInt(seed.slice(off, off + 2), 16) % width;
        const cy = parseInt(seed.slice(off + 2, off + 4), 16) % height;
        const r = 10 + (parseInt(seed.slice(off + 4, off + 6), 16) % 30);
        const endAngle = (parseInt(seed.slice(off + 6, off + 8), 16) % 628) / 100;

        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, endAngle);
        ctx.fillStyle = `rgba(${parseInt(seed.slice(off, off + 2), 16)}, ${parseInt(seed.slice(off + 2, off + 4), 16)}, ${parseInt(seed.slice(off + 4, off + 6), 16)}, 0.6)`;
        ctx.fill();
        ctx.strokeStyle = `#${seed.slice(off, off + 6)}`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    ctx.font = '12px monospace';
    ctx.fillStyle = '#fff';
    ctx.fillText(seed.slice(0, 20), 5, height - 10);

    const imageData = ctx.getImageData(0, 0, width, height);
    return sha256(imageData.data.buffer);
}

// Deterministic pixel pattern — must produce the exact same hash as the
// server's computePixelVerifyHash(). No canvas rendering involved; pure
// integer math over the seed bytes.
async function solvePixelVerify(params) {
    const { width, height, seed } = params;
    const seedBytes = hexToBytes(seed);
    const si = seedBytes.length;
    const data = new Uint8Array(width * height * 4);

    for (let i = 0; i < width * height; i++) {
        const x = i % width;
        const y = Math.floor(i / width);
        data[i * 4] = (seedBytes[x % si] ^ seedBytes[y % si]) & 0xff;
        data[i * 4 + 1] = (seedBytes[(x + y) % si] * 3) & 0xff;
        data[i * 4 + 2] = (seedBytes[Math.abs(x - y) % si] * 7) & 0xff;
        data[i * 4 + 3] = 255;
    }

    return sha256(data.buffer);
}

// --- Stage Dispatcher ---

async function solveStage(stage) {
    switch (stage.type) {
        case 'canvas_text':
            return solveCanvasText(stage);
        case 'audio':
            return solveAudio(stage);
        case 'canvas_geometry':
            return solveCanvasGeometry(stage);
        case 'pixel_verify':
            return solvePixelVerify(stage);
        default:
            throw new Error(`Unknown stage: ${stage.type}`);
    }
}

// --- Public API ---
// Multi-round challenge: fetches stages from server one at a time,
// solves each, and submits the hash before receiving the next stage.

export async function solveChallenge({ baseUrl = '', onProgress = null } = {}) {
    const initRes = await fetch(`${baseUrl}/challenge`, { method: 'POST' });
    if (!initRes.ok) throw new Error('Failed to start challenge');

    let { challengeId, totalStages, stage } = await initRes.json();

    for (let i = 0; i < totalStages; i++) {
        if (onProgress) onProgress(i + 1, totalStages);

        const hash = await solveStage(stage);

        const res = await fetch(`${baseUrl}/challenge/${challengeId}/solve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stageIndex: i, hash }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Stage failed');
        }

        const result = await res.json();
        if (result.complete) return result;
        stage = result.stage;
    }

    throw new Error('Challenge incomplete');
}
