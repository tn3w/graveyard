const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

const HASH = new Uint32Array(8);
const W = new Int32Array(64);
let PAD = new Uint8Array(192);
let PAD_VIEW = new DataView(PAD.buffer);

const REPORT_INTERVAL = 5;

function rotr(x, n) {
    return (x >>> n) | (x << (32 - n));
}

function sha256(input, inputLength) {
    const padLength = (inputLength + 9 + 63) & ~63;

    if (padLength > PAD.length) {
        PAD = new Uint8Array(padLength + 64);
        PAD_VIEW = new DataView(PAD.buffer);
    }

    for (let i = 0; i < inputLength; i++) {
        PAD[i] = input[i];
    }
    PAD[inputLength] = 0x80;
    PAD.fill(0, inputLength + 1, padLength);
    PAD_VIEW.setUint32(padLength - 4, inputLength * 8, false);

    let h0 = 0x6a09e667,
        h1 = 0xbb67ae85;
    let h2 = 0x3c6ef372,
        h3 = 0xa54ff53a;
    let h4 = 0x510e527f,
        h5 = 0x9b05688c;
    let h6 = 0x1f83d9ab,
        h7 = 0x5be0cd19;

    for (let off = 0; off < padLength; off += 64) {
        for (let i = 0; i < 16; i++) {
            W[i] = PAD_VIEW.getInt32(off + i * 4, false);
        }

        for (let i = 16; i < 64; i++) {
            const s0 = rotr(W[i - 15], 7) ^ rotr(W[i - 15], 18) ^ (W[i - 15] >>> 3);
            const s1 = rotr(W[i - 2], 17) ^ rotr(W[i - 2], 19) ^ (W[i - 2] >>> 10);
            W[i] = (W[i - 16] + s0 + W[i - 7] + s1) | 0;
        }

        let a = h0,
            b = h1,
            c = h2,
            d = h3;
        let e = h4,
            f = h5,
            g = h6,
            h = h7;

        for (let i = 0; i < 64; i++) {
            const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            const ch = (e & f) ^ (~e & g);
            const t1 = (h + S1 + ch + K[i] + W[i]) | 0;
            const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            const maj = (a & b) ^ (a & c) ^ (b & c);
            const t2 = (S0 + maj) | 0;

            h = g;
            g = f;
            f = e;
            e = (d + t1) | 0;
            d = c;
            c = b;
            b = a;
            a = (t1 + t2) | 0;
        }

        h0 = (h0 + a) | 0;
        h1 = (h1 + b) | 0;
        h2 = (h2 + c) | 0;
        h3 = (h3 + d) | 0;
        h4 = (h4 + e) | 0;
        h5 = (h5 + f) | 0;
        h6 = (h6 + g) | 0;
        h7 = (h7 + h) | 0;
    }

    HASH[0] = h0;
    HASH[1] = h1;
    HASH[2] = h2;
    HASH[3] = h3;
    HASH[4] = h4;
    HASH[5] = h5;
    HASH[6] = h6;
    HASH[7] = h7;
}

function hasLeadingZeros(difficulty) {
    for (const word of HASH) {
        if (difficulty <= 0) return true;
        const zeros = Math.clz32(word);
        if (zeros < 32) return zeros >= difficulty;
        difficulty -= 32;
    }
    return difficulty <= 0;
}

function digestTo(target, offset) {
    for (let i = 0; i < 8; i++) {
        const word = HASH[i];
        target[offset++] = (word >>> 24) & 0xff;
        target[offset++] = (word >>> 16) & 0xff;
        target[offset++] = (word >>> 8) & 0xff;
        target[offset++] = word & 0xff;
    }
}

function writeLE32(buffer, offset, value) {
    buffer[offset] = value & 0xff;
    buffer[offset + 1] = (value >>> 8) & 0xff;
    buffer[offset + 2] = (value >>> 16) & 0xff;
    buffer[offset + 3] = (value >>> 24) & 0xff;
}

const SCRATCH = new Uint8Array(128);
let BALLOON = null;

function balloon(input, inputLen, spaceCost, timeCost, delta) {
    if (!BALLOON || BALLOON.length < spaceCost * 32) {
        BALLOON = new Uint8Array(spaceCost * 32);
    }

    let cnt = 0;

    writeLE32(SCRATCH, 0, cnt++);
    SCRATCH.set(input.subarray(0, inputLen), 4);
    sha256(SCRATCH, 4 + inputLen);
    digestTo(BALLOON, 0);

    for (let i = 1; i < spaceCost; i++) {
        writeLE32(SCRATCH, 0, cnt++);
        SCRATCH.set(BALLOON.subarray((i - 1) * 32, i * 32), 4);
        sha256(SCRATCH, 36);
        digestTo(BALLOON, i * 32);
    }

    for (let t = 0; t < timeCost; t++) {
        for (let i = 0; i < spaceCost; i++) {
            const prev = ((i || spaceCost) - 1) * 32;
            const curr = i * 32;

            writeLE32(SCRATCH, 0, cnt++);
            SCRATCH.set(BALLOON.subarray(prev, prev + 32), 4);
            SCRATCH.set(BALLOON.subarray(curr, curr + 32), 36);
            sha256(SCRATCH, 68);
            digestTo(BALLOON, curr);

            for (let j = 0; j < delta; j++) {
                writeLE32(SCRATCH, 0, cnt++);
                writeLE32(SCRATCH, 4, t);
                writeLE32(SCRATCH, 8, i);
                writeLE32(SCRATCH, 12, j);
                sha256(SCRATCH, 16);
                const otherOffset = (HASH[0] % spaceCost) * 32;

                writeLE32(SCRATCH, 0, cnt++);
                SCRATCH.set(BALLOON.subarray(curr, curr + 32), 4);
                SCRATCH.set(BALLOON.subarray(otherOffset, otherOffset + 32), 36);
                sha256(SCRATCH, 68);
                digestTo(BALLOON, curr);
            }
        }
    }
}

function writeNonce(buffer, offset, nonce) {
    const digits = nonce.toString();
    for (let i = 0; i < digits.length; i++) {
        buffer[offset + i] = digits.charCodeAt(i);
    }
    return offset + digits.length;
}

function mine(prefix, difficulty, spaceCost, timeCost, delta, workerId, workerCount) {
    const prefixBytes = new TextEncoder().encode(prefix);
    const inputBuffer = new Uint8Array(prefixBytes.length + 20);
    inputBuffer.set(prefixBytes);

    let nonce = workerId;
    let unreported = 0;

    while (true) {
        const inputLength = writeNonce(inputBuffer, prefixBytes.length, nonce);

        balloon(inputBuffer, inputLength, spaceCost, timeCost, delta);

        if (hasLeadingZeros(difficulty)) {
            self.postMessage({
                type: 'solution',
                nonce,
                hashes: unreported,
            });
            return;
        }

        nonce += workerCount;
        unreported++;

        if (unreported >= REPORT_INTERVAL) {
            self.postMessage({
                type: 'progress',
                hashes: unreported,
            });
            unreported = 0;
        }
    }
}

self.onmessage = ({ data }) => {
    mine(
        data.prefix,
        data.difficulty,
        data.spaceCost,
        data.timeCost,
        data.delta,
        data.workerId,
        data.workerCount
    );
};
