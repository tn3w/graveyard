import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createCanvas } from 'canvas';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DEG = Math.PI / 180;

function v3sub(a, b) {
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function v3cross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}

function v3dot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function v3normalize(v) {
    const len = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    if (len < 1e-10) return [0, 0, 0];
    return [v[0] / len, v[1] / len, v[2] / len];
}

function v3scale(v, s) {
    return [v[0] * s, v[1] * s, v[2] * s];
}

function v3add(a, b) {
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

function mat4Identity() {
    const m = new Float64Array(16);
    m[0] = m[5] = m[10] = m[15] = 1;
    return m;
}

function mat4Multiply(a, b) {
    const o = new Float64Array(16);
    for (let c = 0; c < 4; c++) {
        for (let r = 0; r < 4; r++) {
            o[c * 4 + r] =
                a[r] * b[c * 4] +
                a[4 + r] * b[c * 4 + 1] +
                a[8 + r] * b[c * 4 + 2] +
                a[12 + r] * b[c * 4 + 3];
        }
    }
    return o;
}

function mat4RotateY(angle) {
    const m = mat4Identity();
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    m[0] = c;
    m[8] = s;
    m[2] = -s;
    m[10] = c;
    return m;
}

function mat4Translate(x, y, z) {
    const m = mat4Identity();
    m[12] = x;
    m[13] = y;
    m[14] = z;
    return m;
}

function mat4LookAt(eye, center, up) {
    const f = v3normalize(v3sub(center, eye));
    const r = v3normalize(v3cross(f, up));
    const u = v3cross(r, f);
    const m = new Float64Array(16);

    m[0] = r[0];
    m[4] = r[1];
    m[8] = r[2];
    m[12] = -v3dot(r, eye);
    m[1] = u[0];
    m[5] = u[1];
    m[9] = u[2];
    m[13] = -v3dot(u, eye);
    m[2] = -f[0];
    m[6] = -f[1];
    m[10] = -f[2];
    m[14] = v3dot(f, eye);
    m[3] = 0;
    m[7] = 0;
    m[11] = 0;
    m[15] = 1;
    return m;
}

function mat4Perspective(fovDeg, aspect, near, far) {
    const f = 1 / Math.tan((fovDeg * DEG) / 2);
    const nf = 1 / (near - far);
    const m = new Float64Array(16);
    m[0] = f / aspect;
    m[5] = f;
    m[10] = (far + near) * nf;
    m[11] = -1;
    m[14] = 2 * far * near * nf;
    return m;
}

function transformPoint(m, p) {
    const x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12];
    const y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13];
    const z = m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14];
    const w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
    return [x, y, z, w];
}

function transformDir(m, d) {
    return [
        m[0] * d[0] + m[4] * d[1] + m[8] * d[2],
        m[1] * d[0] + m[5] * d[1] + m[9] * d[2],
        m[2] * d[0] + m[6] * d[1] + m[10] * d[2],
    ];
}

function clipToScreen(clip, size) {
    if (clip[3] <= 0) return null;
    const invW = 1 / clip[3];
    return [
        (clip[0] * invW * 0.5 + 0.5) * size,
        (1 - (clip[1] * invW * 0.5 + 0.5)) * size,
        clip[2] * invW,
        clip[3],
    ];
}

function loadMesh(gltfPath) {
    const gltf = JSON.parse(readFileSync(gltfPath, 'utf-8'));
    const binPath = join(dirname(gltfPath), gltf.buffers[0].uri);
    const bin = readFileSync(binPath);

    const primitive = gltf.meshes[0].primitives[0];
    const posAccessor = gltf.accessors[primitive.attributes.POSITION];
    const normAccessor = gltf.accessors[primitive.attributes.NORMAL];
    const idxAccessor = gltf.accessors[primitive.indices];

    const readAccessor = (accessor, Ctor, components) => {
        const bv = gltf.bufferViews[accessor.bufferView];
        const byteOffset = (bv.byteOffset || 0) + (accessor.byteOffset || 0);
        const stride = bv.byteStride || components * Ctor.BYTES_PER_ELEMENT;
        const count = accessor.count;

        if (stride === components * Ctor.BYTES_PER_ELEMENT) {
            return new Ctor(bin.buffer, bin.byteOffset + byteOffset, count * components);
        }

        const out = new Ctor(count * components);
        for (let i = 0; i < count; i++) {
            const srcOff = byteOffset + i * stride;
            for (let c = 0; c < components; c++) {
                out[i * components + c] = new Ctor(
                    bin.buffer,
                    bin.byteOffset + srcOff + c * Ctor.BYTES_PER_ELEMENT,
                    1
                )[0];
            }
        }
        return out;
    };

    const positions = readAccessor(posAccessor, Float32Array, 3);
    const normals = readAccessor(normAccessor, Float32Array, 3);
    const indices = readAccessor(idxAccessor, Uint32Array, 1);
    const vertexCount = posAccessor.count;
    const triangleCount = idxAccessor.count / 3;

    let minX = Infinity,
        minY = Infinity,
        minZ = Infinity;
    let maxX = -Infinity,
        maxY = -Infinity,
        maxZ = -Infinity;

    for (let i = 0; i < vertexCount; i++) {
        const x = positions[i * 3];
        const y = positions[i * 3 + 1];
        const z = positions[i * 3 + 2];
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
        if (z < minZ) minZ = z;
        if (z > maxZ) maxZ = z;
    }

    const centerX = (minX + maxX) / 2;
    const centerY = minY;
    const centerZ = (minZ + maxZ) / 2;
    const extentX = (maxX - minX) / 2;
    const extentY = maxY - minY;
    const extentZ = (maxZ - minZ) / 2;
    const maxExtent = Math.max(extentX, extentY, extentZ);
    const scale = 1 / maxExtent;

    for (let i = 0; i < vertexCount; i++) {
        positions[i * 3] = (positions[i * 3] - centerX) * scale;
        positions[i * 3 + 1] = (positions[i * 3 + 1] - centerY) * scale;
        positions[i * 3 + 2] = (positions[i * 3 + 2] - centerZ) * scale;
    }

    return {
        positions,
        normals,
        indices,
        vertexCount,
        triangleCount,
        height: extentY * scale,
    };
}

function sampleMeshSurface(mesh, count, rng) {
    const { positions, normals, indices, triangleCount } = mesh;
    const areas = new Float64Array(triangleCount);
    let totalArea = 0;

    for (let t = 0; t < triangleCount; t++) {
        const i0 = indices[t * 3] * 3;
        const i1 = indices[t * 3 + 1] * 3;
        const i2 = indices[t * 3 + 2] * 3;

        const ax = positions[i1] - positions[i0];
        const ay = positions[i1 + 1] - positions[i0 + 1];
        const az = positions[i1 + 2] - positions[i0 + 2];
        const bx = positions[i2] - positions[i0];
        const by = positions[i2 + 1] - positions[i0 + 1];
        const bz = positions[i2 + 2] - positions[i0 + 2];

        const cx = ay * bz - az * by;
        const cy = az * bx - ax * bz;
        const cz = ax * by - ay * bx;
        areas[t] = Math.sqrt(cx * cx + cy * cy + cz * cz) * 0.5;
        totalArea += areas[t];
    }

    const cdf = new Float64Array(triangleCount);
    cdf[0] = areas[0] / totalArea;
    for (let t = 1; t < triangleCount; t++) {
        cdf[t] = cdf[t - 1] + areas[t] / totalArea;
    }

    const points = new Float32Array(count * 3);
    const pointNormals = new Float32Array(count * 3);

    for (let s = 0; s < count; s++) {
        const r = rng();
        let triIdx = 0;
        let lo = 0,
            hi = triangleCount - 1;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (cdf[mid] < r) lo = mid + 1;
            else hi = mid;
        }
        triIdx = lo;

        let u = rng(),
            v = rng();
        if (u + v > 1) {
            u = 1 - u;
            v = 1 - v;
        }
        const w = 1 - u - v;

        const i0 = indices[triIdx * 3] * 3;
        const i1 = indices[triIdx * 3 + 1] * 3;
        const i2 = indices[triIdx * 3 + 2] * 3;

        for (let c = 0; c < 3; c++) {
            points[s * 3 + c] =
                positions[i0 + c] * w + positions[i1 + c] * u + positions[i2 + c] * v;
            pointNormals[s * 3 + c] =
                normals[i0 + c] * w + normals[i1 + c] * u + normals[i2 + c] * v;
        }
    }

    return { points, normals: pointNormals, count };
}

function createRng(seed) {
    let s = seed | 0;
    return () => {
        s = (s + 0x6d2b79f5) | 0;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

export class CaptchaEngine {
    constructor(options = {}) {
        this.size = options.size || 300;
        this.splatCount = options.splatCount || 2000;
        this.splatWorldRadius = options.splatWorldRadius || 0.08;
        this.choiceCount = options.choiceCount || 6;
        this.fov = options.fov || 45;
        this.cameraDistance = options.cameraDistance || 3.2;
        this.cameraElevation = options.cameraElevation || 0.35;

        const gltfPath = options.gltfPath || join(__dirname, 'scene.gltf');
        this.mesh = loadMesh(gltfPath);

        this.lightDir = v3normalize([0.5, 0.8, 0.6]);
        this.shadowDir = v3normalize([-0.4, -1, -0.3]);
        this.ambientStrength = 0.3;
        this.baseColor = [200, 175, 145];
    }

    buildMatrices(angleDeg) {
        const angleRad = angleDeg * DEG;
        const modelCenter = [0, this.mesh.height / 2, 0];
        const model = mat4Multiply(mat4Translate(0, 0, 0), mat4RotateY(angleRad));

        const eyeY = modelCenter[1] + this.cameraDistance * Math.sin(this.cameraElevation);
        const eyeHoriz = this.cameraDistance * Math.cos(this.cameraElevation);
        const eye = [0, eyeY, eyeHoriz];
        const target = [0, modelCenter[1] * 0.85, 0];

        const view = mat4LookAt(eye, target, [0, 1, 0]);
        const proj = mat4Perspective(this.fov, 1, 0.1, 100);

        const vp = mat4Multiply(proj, view);
        const mvp = mat4Multiply(vp, model);
        return { model, view, proj, vp, mvp, eye, target };
    }

    renderReference(angleDeg) {
        const { size, mesh } = this;
        const canvas = createCanvas(size, size);
        const ctx = canvas.getContext('2d');
        const { model, mvp, vp, eye } = this.buildMatrices(angleDeg);

        const bgTop = ctx.createLinearGradient(0, 0, 0, size);
        bgTop.addColorStop(0, '#e8e4e0');
        bgTop.addColorStop(0.7, '#d4d0cc');
        bgTop.addColorStop(1, '#c0bcb8');
        ctx.fillStyle = bgTop;
        ctx.fillRect(0, 0, size, size);

        const { positions, normals, indices, triangleCount } = mesh;
        const worldLight = this.lightDir;
        const viewDir = v3normalize(v3sub(eye, [0, 0, 0]));

        const triangles = [];
        const shadows = [];

        for (let t = 0; t < triangleCount; t++) {
            const idx = [indices[t * 3], indices[t * 3 + 1], indices[t * 3 + 2]];

            const worldPos = idx.map((i) => {
                const p = [positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]];
                const tp = transformPoint(model, p);
                return [tp[0], tp[1], tp[2]];
            });

            const edge1 = v3sub(worldPos[1], worldPos[0]);
            const edge2 = v3sub(worldPos[2], worldPos[0]);
            const faceNormal = v3normalize(v3cross(edge1, edge2));

            const triCenter = v3scale(v3add(v3add(worldPos[0], worldPos[1]), worldPos[2]), 1 / 3);
            const toCamera = v3normalize(v3sub(eye, triCenter));

            if (v3dot(faceNormal, toCamera) < 0) {
                faceNormal[0] *= -1;
                faceNormal[1] *= -1;
                faceNormal[2] *= -1;
            }

            const screenVerts = worldPos.map((wp) => {
                const clip = transformPoint(vp, wp);
                return clipToScreen(clip, size);
            });

            if (screenVerts.some((s) => s === null)) continue;

            const diff = Math.max(0, v3dot(faceNormal, worldLight));
            const brightness = this.ambientStrength + (1 - this.ambientStrength) * diff;
            const [br, bg, bb] = this.baseColor;
            const color = [
                Math.min(255, Math.round(br * brightness)),
                Math.min(255, Math.round(bg * brightness)),
                Math.min(255, Math.round(bb * brightness)),
            ];

            const avgZ = (screenVerts[0][2] + screenVerts[1][2] + screenVerts[2][2]) / 3;
            triangles.push({ verts: screenVerts, color, depth: avgZ });

            const floorY = 0;
            const shadowVerts = worldPos.map((wp) => {
                if (this.shadowDir[1] >= 0) return null;
                const t = (floorY - wp[1]) / this.shadowDir[1];
                if (t < 0) return null;
                const sp = [wp[0] + this.shadowDir[0] * t, floorY, wp[2] + this.shadowDir[2] * t];
                const clip = transformPoint(vp, sp);
                return clipToScreen(clip, size);
            });

            if (shadowVerts.every((s) => s !== null)) {
                shadows.push({ verts: shadowVerts, depth: avgZ + 100 });
            }
        }

        shadows.sort((a, b) => b.depth - a.depth);
        ctx.fillStyle = 'rgba(60, 55, 50, 0.2)';
        for (const shadow of shadows) {
            ctx.beginPath();
            ctx.moveTo(shadow.verts[0][0], shadow.verts[0][1]);
            ctx.lineTo(shadow.verts[1][0], shadow.verts[1][1]);
            ctx.lineTo(shadow.verts[2][0], shadow.verts[2][1]);
            ctx.closePath();
            ctx.fill();
        }

        triangles.sort((a, b) => b.depth - a.depth);
        for (const tri of triangles) {
            const [r, g, b] = tri.color;
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.beginPath();
            ctx.moveTo(tri.verts[0][0], tri.verts[0][1]);
            ctx.lineTo(tri.verts[1][0], tri.verts[1][1]);
            ctx.lineTo(tri.verts[2][0], tri.verts[2][1]);
            ctx.closePath();
            ctx.fill();
        }

        const smallSize = Math.round(size * 0.45);
        const small = createCanvas(smallSize, smallSize);
        const sctx = small.getContext('2d');
        sctx.drawImage(canvas, 0, 0, smallSize, smallSize);

        ctx.clearRect(0, 0, size, size);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'low';
        ctx.drawImage(small, 0, 0, size, size);

        const imageData = ctx.getImageData(0, 0, size, size);
        const refPixels = imageData.data;
        const noiseRng = createRng((angleDeg * 997) | 0);
        for (let i = 0; i < refPixels.length; i += 4) {
            const n = (noiseRng() - 0.5) * 35;
            refPixels[i] = Math.min(255, Math.max(0, refPixels[i] + n));
            refPixels[i + 1] = Math.min(255, Math.max(0, refPixels[i + 1] + n));
            refPixels[i + 2] = Math.min(255, Math.max(0, refPixels[i + 2] + n));
        }
        ctx.putImageData(imageData, 0, 0);

        return canvas.toBuffer('image/png');
    }

    renderSplat(angleDeg, seed) {
        const { size } = this;
        const canvas = createCanvas(size, size);
        const ctx = canvas.getContext('2d');
        const rng = createRng(seed);

        const samples = sampleMeshSurface(this.mesh, this.splatCount, rng);

        ctx.fillStyle = '#1a1c2e';
        ctx.fillRect(0, 0, size, size);

        const bgSphereCount = 55;
        const cellSize = size / Math.ceil(Math.sqrt(bgSphereCount));
        for (let i = 0; i < bgSphereCount; i++) {
            const col = i % Math.ceil(Math.sqrt(bgSphereCount));
            const row = Math.floor(i / Math.ceil(Math.sqrt(bgSphereCount)));
            const sx = (col + 0.3 + rng() * 0.4) * cellSize;
            const sy = (row + 0.3 + rng() * 0.4) * cellSize;
            const sr = 18 + rng() * 30;
            const warmth = rng();
            const alpha = 0.1 + rng() * 0.2;

            const coreR = Math.round(200 + warmth * 55);
            const coreG = Math.round(205 + warmth * 40);
            const coreB = Math.round(215 + warmth * 25);

            const grad = ctx.createRadialGradient(
                sx - sr * 0.25,
                sy - sr * 0.25,
                sr * 0.05,
                sx,
                sy,
                sr
            );
            grad.addColorStop(0, `rgba(${coreR},${coreG},${coreB},${alpha})`);
            grad.addColorStop(
                0.5,
                `rgba(${coreR - 40},${coreG - 35},` + `${coreB - 30},${alpha * 0.5})`
            );
            grad.addColorStop(1, `rgba(${coreR - 80},${coreG - 70},` + `${coreB - 60},0)`);

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(sx, sy, sr, 0, Math.PI * 2);
            ctx.fill();
        }

        const { mvp } = this.buildMatrices(angleDeg);
        const focalLen = size / (2 * Math.tan((this.fov * DEG) / 2));

        const projected = [];
        for (let i = 0; i < samples.count; i++) {
            const p = [samples.points[i * 3], samples.points[i * 3 + 1], samples.points[i * 3 + 2]];

            const clip = transformPoint(mvp, p);
            if (clip[3] <= 0.01) continue;

            const screen = clipToScreen(clip, size);
            if (!screen) continue;

            const screenRadius = Math.max(4, (this.splatWorldRadius * focalLen) / clip[3]);

            projected.push({
                x: screen[0],
                y: screen[1],
                depth: screen[2],
                radius: screenRadius,
            });
        }

        projected.sort((a, b) => b.depth - a.depth);

        for (const splat of projected) {
            const { x, y, radius } = splat;
            const alpha = 0.2 + rng() * 0.2;

            const grad = ctx.createRadialGradient(
                x - radius * 0.25,
                y - radius * 0.25,
                radius * 0.05,
                x,
                y,
                radius
            );
            grad.addColorStop(0, `rgba(255,255,255,${alpha + 0.15})`);
            grad.addColorStop(0.35, `rgba(235,240,245,${alpha})`);
            grad.addColorStop(0.7, `rgba(200,210,220,${alpha * 0.4})`);
            grad.addColorStop(1, 'rgba(180,190,200,0)');

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
        }

        const decoyCount = 25 + Math.floor(rng() * 20);
        for (let i = 0; i < decoyCount; i++) {
            const dx = rng() * size;
            const dy = rng() * size;
            const dr = 4 + rng() * 10;
            const da = 0.08 + rng() * 0.18;

            const grad = ctx.createRadialGradient(
                dx - dr * 0.25,
                dy - dr * 0.25,
                dr * 0.05,
                dx,
                dy,
                dr
            );
            grad.addColorStop(0, `rgba(250,252,255,${da + 0.1})`);
            grad.addColorStop(0.5, `rgba(220,225,235,${da * 0.5})`);
            grad.addColorStop(1, 'rgba(200,210,220,0)');

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(dx, dy, dr, 0, Math.PI * 2);
            ctx.fill();
        }

        const imgData = ctx.getImageData(0, 0, size, size);
        const px = imgData.data;
        const noiseRng = createRng(seed + 3571);
        for (let i = 0; i < px.length; i += 4) {
            const n = (noiseRng() - 0.5) * 22;
            px[i] = Math.min(255, Math.max(0, px[i] + n));
            px[i + 1] = Math.min(255, Math.max(0, px[i + 1] + n));
            px[i + 2] = Math.min(255, Math.max(0, px[i + 2] + n));
        }
        ctx.putImageData(imgData, 0, 0);

        return canvas.toBuffer('image/png');
    }

    generate(seed) {
        seed = seed ?? Date.now() ^ (Math.random() * 0xffffffff);
        const rng = createRng(seed);
        const stepSize = 360 / this.choiceCount;

        const correctIdx = Math.floor(rng() * this.choiceCount);
        const baseAngle = Math.floor(rng() * 360);

        const angles = [];
        for (let i = 0; i < this.choiceCount; i++) {
            angles.push((baseAngle + i * stepSize) % 360);
        }

        const correctAngle = angles[correctIdx];
        const reference = this.renderReference(correctAngle);

        const choices = angles.map((angle, i) => ({
            image: this.renderSplat(angle, seed + i * 7919),
            angle,
            correct: i === correctIdx,
        }));

        return {
            reference,
            choices,
            correctIndex: correctIdx,
            correctAngle,
            seed,
        };
    }
}
