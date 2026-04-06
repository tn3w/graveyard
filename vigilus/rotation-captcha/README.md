# Rotation Captcha

Server-side 3D rotation-matching captcha. A reference image shows a low-poly model at a specific Y-axis rotation; challenge images render the same model as overlapping translucent spheres on a noisy background. The user picks the challenge image whose rotation matches the reference.

## Quick Start

```bash
npm install
npm start          # generates output/ PNGs
open preview.html  # view results in browser
```

## How It Works

### Challenge Flow

```
                          ┌──────────────────┐
                          │   CaptchaEngine  │
                          └────────┬─────────┘
                                   │
                    generate(seed) │
                                   │
         ┌─────────────────────────┼──────────────────────────┐
         │                         │                          │
         ▼                         ▼                          ▼
  ┌──────────────┐    ┌────────────────────┐    ┌────────────────────┐
  │   Pick seed  │    │ Choose N angles    │    │ Sample mesh surface│
  │   + angles   │    │ evenly around 360° │    │ (2000 points)      │
  └──────┬───────┘    └────────┬───────────┘    └─────────┬──────────┘
         │                     │                          │
         ▼                     ▼                          ▼
  ┌──────────────┐    ┌────────────────────┐    ┌────────────────────┐
  │ Reference    │    │ For each angle:    │    │ Project points     │
  │ renderRef()  │    │ renderSplat()      │    │ through MVP matrix │
  │ at correct   │    │ at that angle      │    │ → screen coords    │
  │ angle        │    │                    │    │                    │
  └──────┬───────┘    └────────┬───────────┘    └────────────────────┘
         │                     │
         ▼                     ▼
  ┌──────────────┐    ┌────────────────────┐
  │ Degraded PNG │    │ 6 sphere-style PNGs│
  │ (blurred +   │    │ (1 correct match)  │
  │  noisy)      │    │                    │
  └──────────────┘    └────────────────────┘
```

### Two Render Pipelines

```
┌─────────────────────────────────────────────────────────────────┐
│ Reference (renderReference)                                     │
│                                                                 │
│  GLTF mesh ──► model/view/proj ──► painter's algorithm          │
│                 matrices            (back-to-front triangles)   │
│                    │                        │                   │
│                    ▼                        ▼                   │
│              floor shadows          Lambertian shading          │
│              (projected onto        per-face normal             │
│               y=0 plane)                                        │
│                    │                        │                   │
│                    └──────────┬─────────────┘                   │
│                               ▼                                 │
│                      downscale to 45%                           │
│                      upscale back (blur)                        │
│                      + pixel noise ±35                          │
│                               │                                 │
│                               ▼                                 │
│                        degraded PNG                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Challenge (renderSplat)                                         │
│                                                                 │
│  dark base ──► grid-spaced background spheres                   │
│                (55 white/warm translucent, radial gradients)    │
│                        │                                        │
│                        ▼                                        │
│  mesh surface ──► project 2000 points ──► sort by depth         │
│  samples              through MVP                               │
│                        │                                        │
│                        ▼                                        │
│               draw as white translucent spheres                 │
│               (radial gradient: white center → transparent)     │
│                        │                                        │
│                        ▼                                        │
│               scatter 25-45 decoy spheres                       │
│               + pixel noise ±22                                 │
│                        │                                        │
│                        ▼                                        │
│                   challenge PNG                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Anti-Bot Layers

```
   Bot attempts image analysis
              │
              ▼
   ┌──────────────────────────┐
   │ Edge detection?          │──► Decoy spheres + noise break edges
   │ Template matching?       │──► Background spheres mimic model
   │ Silhouette extraction?   │──► Translucent overlap = soft form
   │ Color segmentation?      │──► Both layers use same white tones
   │ Reference comparison?    │──► Reference is degraded + noisy
   └──────────────────────────┘
              │
              ▼
   Human sees 3D shape via gestalt perception
   Bot sees indistinguishable sphere clusters
```

| Layer              | Purpose                                        |
| ------------------ | ---------------------------------------------- |
| Background spheres | Grid-spaced, white/warm tones — mimics model   |
| Model spheres      | Variable opacity (0.2–0.4) — blends with scene |
| Decoy spheres      | 25–45 random white spheres outside the model   |
| Pixel noise        | ±22 grain on choices, ±35 on reference         |
| Reference blur     | 45% downscale → upscale — hides fine detail    |

## Architecture

```
captcha/
├── engine.js        3D pipeline, mesh loading, both renderers
├── generate.js      CLI — writes PNGs to output/
├── preview.html     Browser preview of generated set
├── scene.gltf       Low-poly cat model (732 triangles)
├── scene.bin        Vertex/index binary data
└── output/          Generated captcha images
```

### engine.js Internals

```
CaptchaEngine
│
├── constructor()
│   ├── loadMesh(gltf)          Parse GLTF, normalize to unit box
│   └── set camera/light params
│
├── buildMatrices(angleDeg)     Model × View × Projection
│
├── renderReference(angle)      Painter's algorithm + degrade
│   ├── transform triangles
│   ├── compute face normals + Lambertian lighting
│   ├── project shadows onto floor
│   ├── sort + draw back-to-front
│   └── blur + noise post-process
│
├── renderSplat(angle, seed)    Sphere-based challenge image
│   ├── sampleMeshSurface()     Weighted random triangle sampling
│   ├── draw background spheres (grid-jittered)
│   ├── project + sort surface points
│   ├── draw model spheres (radial gradients)
│   ├── scatter decoy spheres
│   └── pixel noise post-process
│
└── generate(seed)              Full captcha set
    ├── pick N evenly-spaced angles
    ├── renderReference(correctAngle)
    └── renderSplat(angle, seed) × N
```

## API

```javascript
import { CaptchaEngine } from './engine.js';

const engine = new CaptchaEngine({
    size: 300, // image dimensions (square)
    splatCount: 2000, // surface sample points
    splatWorldRadius: 0.08, // sphere size in world units
    choiceCount: 6, // number of challenge images
    fov: 45, // camera field of view
    cameraDistance: 3.2, // orbit radius
    cameraElevation: 0.35, // camera pitch (radians)
});

const captcha = engine.generate(seed);

// captcha.reference      — PNG Buffer (degraded reference)
// captcha.choices[]      — { image: Buffer, angle, correct }
// captcha.correctIndex   — index of matching choice
// captcha.correctAngle   — Y-axis rotation in degrees
// captcha.seed           — reproducible seed
```

### Individual Renders

```javascript
const refPng = engine.renderReference(angleDeg);
const splatPng = engine.renderSplat(angleDeg, seed);
```

## Integration

```javascript
import { CaptchaEngine } from './engine.js';

const engine = new CaptchaEngine();

app.post('/captcha', (req, res) => {
    const captcha = engine.generate();
    sessions.set(req.sessionId, captcha.correctIndex);

    res.json({
        reference: captcha.reference.toString('base64'),
        choices: captcha.choices.map((c) => ({
            image: c.image.toString('base64'),
        })),
    });
});

app.post('/captcha/verify', (req, res) => {
    const expected = sessions.get(req.sessionId);
    const passed = req.body.choice === expected;
    res.json({ passed });
});
```

## 3D Pipeline

### Coordinate System

```
        Y (up)
        │
        │   model rotates
        │   around Y axis
        │       ↻
        ┼───────── X
       ╱
      ╱
     Z (toward camera)
```

### Mesh Processing

```
Raw GLTF vertices ──► compute bounding box
                      ──► center at origin (XZ)
                      ──► base at Y=0
                      ──► normalize to unit scale
                              │
                              ▼
                      949 vertices, 732 triangles
                      height: ~1.0 (normalized)
```

### Surface Sampling

```
For each sample point:
  1. Build triangle CDF weighted by area
  2. Binary search for triangle (O(log n))
  3. Random barycentric coords (u, v)
     if u + v > 1: mirror to stay inside
  4. Interpolate position + normal
```

## Model

[Low Poly Cat](https://skfb.ly/OqVx) by volkanongun — [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/)
