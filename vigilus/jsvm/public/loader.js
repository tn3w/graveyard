let _module = null;

const HEADER_MAGIC = 0x564d4243;
const HEADER_SIZE = 8;
const IV_SIZE = 16;

async function initModule(wasmUrl) {
    if (_module) return _module;

    const script = document.createElement('script');
    script.src = wasmUrl.replace('.wasm', '.js');

    await new Promise((resolve, reject) => {
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });

    _module = await QJSModule({
        locateFile: (path) => {
            if (path.endsWith('.wasm')) return wasmUrl;
            return path;
        },
    });

    return _module;
}

async function deriveKey(keyMaterial) {
    if (keyMaterial instanceof Uint8Array) {
        return crypto.subtle.importKey('raw', keyMaterial, 'AES-CTR', false, ['decrypt']);
    }

    const raw = new Uint8Array(keyMaterial.match(/.{2}/g).map((h) => parseInt(h, 16)));
    return crypto.subtle.importKey('raw', raw, 'AES-CTR', false, ['decrypt']);
}

async function decryptBundle(bundle, keyMaterial) {
    const buf = bundle.buffer;
    const off = bundle.byteOffset;
    const view = new DataView(buf, off, bundle.byteLength);
    const magic = view.getUint32(0);
    if (magic !== HEADER_MAGIC) {
        throw new Error('Invalid bundle');
    }

    const encLen = view.getUint32(4);
    const iv = bundle.slice(HEADER_SIZE, HEADER_SIZE + IV_SIZE);
    const encrypted = bundle.slice(HEADER_SIZE + IV_SIZE, HEADER_SIZE + IV_SIZE + encLen);

    const key = await deriveKey(keyMaterial);
    const counter = new Uint8Array(16);
    counter.set(iv);

    const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-CTR', counter, length: 128 },
        key,
        encrypted
    );

    return new Uint8Array(decrypted);
}

async function _exec(wasmUrl, bundleBytes, keyMaterial) {
    const mod = await initModule(wasmUrl);
    const rc = mod._vm_init();
    if (rc !== 0) return null;

    const bytecode = await decryptBundle(bundleBytes, keyMaterial);

    const ptr = mod._malloc(bytecode.length);
    mod.HEAPU8.set(bytecode, ptr);

    const resultPtr = mod._vm_exec_bytecode(ptr, bytecode.length);
    mod._free(ptr);

    if (!resultPtr) {
        mod._vm_destroy();
        return null;
    }

    const result = mod.UTF8ToString(resultPtr);
    mod._vm_free(resultPtr);
    mod._vm_destroy();
    return result;
}

export async function solve() {
    const initRes = await fetch('/vm/init', { method: 'POST' });
    const cfg = await initRes.json();

    const bundleRes = await fetch(cfg.bundleUrl);
    const bundle = new Uint8Array(await bundleRes.arrayBuffer());

    const bundleKeyMaterial = cfg.key;
    const raw = await _exec(cfg.wasmUrl, bundle, bundleKeyMaterial);

    if (!raw) return { ok: false };

    if (raw.startsWith('{')) {
        try {
            const err = JSON.parse(raw);
            if (err.e) return { ok: false, error: err.e };
        } catch {}
        return { ok: false };
    }

    const verifyRes = await fetch('/vm/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            cid: cfg.challengeId,
            payload: raw,
        }),
    });
    const v = await verifyRes.json();

    if (!v.ok) return { ok: false };

    return { ok: true, token: v.token };
}
