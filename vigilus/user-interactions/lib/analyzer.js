// ============================================================================
// Human Interaction Analyzer
//
// Scores behavioral biometrics to distinguish humans from bots.
// Score: 1.0 = definitely human, 0.0 = definitely bot.
//
// Humans move in natural curves with micro-tremors, variable acceleration,
// and slight overshoots. Bots move in straight lines, teleport, and click
// pixel-perfectly at element centers.
// ============================================================================

// ── Utilities ────────────────────────────────────────────────────────────────

function mean(arr) {
    if (!arr.length) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function stddev(arr) {
    if (arr.length < 2) return 0;
    const m = mean(arr);
    return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length);
}

function cv(arr) {
    const m = mean(arr);
    return m !== 0 ? stddev(arr) / Math.abs(m) : 0;
}

function median(arr) {
    if (!arr.length) return 0;
    const s = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

function shannonEntropy(values, numBins = 20) {
    if (values.length < 2) return 0;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const bins = new Array(numBins).fill(0);
    for (const v of values) {
        const bin = Math.min(Math.floor(((v - min) / range) * numBins), numBins - 1);
        bins[bin]++;
    }
    const total = values.length;
    let entropy = 0;
    for (const count of bins) {
        if (count > 0) {
            const p = count / total;
            entropy -= p * Math.log2(p);
        }
    }
    return entropy;
}

function dist(x1, y1, x2, y2) {
    return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

// ── Mouse Movement Analysis ─────────────────────────────────────────────────
// Human motor control follows biomechanical constraints:
// - Fitts' Law governs movement time
// - Minimum jerk model produces smooth bell-shaped velocity profiles
// - Physiological tremor at 8-12 Hz creates sub-pixel wobble
// - Ballistic phase → corrective submovements near targets
// - Speed-accuracy tradeoff: fast movements are less precise

function analyzeMouse(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.3 };
    const m = data.m;

    if (!m || m.length < 5) {
        result.score = 0.2;
        result.reasons.push('Insufficient mouse data');
        return result;
    }

    let penalty = 0;

    // Parse points: [x, y, t]
    const points = m.map((p) => ({ x: p[0], y: p[1], t: p[2] }));

    // 1. Curvature analysis (Menger curvature)
    // Humans produce variable curvature; bots produce near-zero (straight)
    const curvatures = [];
    for (let i = 1; i < points.length - 1; i++) {
        const a = points[i - 1],
            b = points[i],
            c = points[i + 1];
        const ab = dist(a.x, a.y, b.x, b.y);
        const bc = dist(b.x, b.y, c.x, c.y);
        const ca = dist(c.x, c.y, a.x, a.y);
        if (ab > 0 && bc > 0 && ca > 0) {
            const cross = Math.abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x));
            curvatures.push((2 * cross) / (ab * bc * ca));
        }
    }

    if (curvatures.length >= 10) {
        const curvEntropy = shannonEntropy(curvatures, 15);
        if (curvEntropy < 1.0) {
            penalty += 0.12;
            result.reasons.push(
                `Low curvature entropy: ${curvEntropy.toFixed(2)} (straight-line movement)`
            );
        } else if (curvEntropy < 1.8) {
            penalty += 0.05;
            result.reasons.push(`Below-average curvature entropy: ${curvEntropy.toFixed(2)}`);
        }
    }

    // 2. Micro-tremor detection
    // Smooth the path with a 5-point moving average, measure residuals
    // Human hands have physiological tremor (8-12 Hz) creating ~0.3-8px wobble
    if (points.length >= 10) {
        const windowSize = 5;
        const residuals = [];
        for (let i = 2; i < points.length - 2; i++) {
            let sx = 0,
                sy = 0;
            for (let j = -2; j <= 2; j++) {
                sx += points[i + j].x;
                sy += points[i + j].y;
            }
            sx /= windowSize;
            sy /= windowSize;
            residuals.push(dist(points[i].x, points[i].y, sx, sy));
        }

        const tremorRMS = Math.sqrt(mean(residuals.map((r) => r * r)));
        if (tremorRMS < 0.05) {
            penalty += 0.1;
            result.reasons.push(`No micro-tremor: RMS=${tremorRMS.toFixed(3)}px (too smooth)`);
        } else if (tremorRMS > 20) {
            penalty += 0.06;
            result.reasons.push(
                `Excessive tremor: RMS=${tremorRMS.toFixed(1)}px (noise injection?)`
            );
        }
    }

    // 3. Velocity profile analysis
    // Humans: bell-shaped velocity profiles per movement segment
    // Bots: constant velocity or step functions
    const velocities = [];
    const intervals = [];
    for (let i = 1; i < points.length; i++) {
        const dt = points[i].t - points[i - 1].t;
        if (dt > 0) {
            const d = dist(points[i - 1].x, points[i - 1].y, points[i].x, points[i].y);
            velocities.push(d / dt);
            intervals.push(dt);
        }
    }

    if (velocities.length >= 10) {
        const velCV = cv(velocities);
        if (velCV < 0.15) {
            penalty += 0.12;
            result.reasons.push(`Constant velocity: CV=${velCV.toFixed(3)} (robotic)`);
        } else if (velCV < 0.3) {
            penalty += 0.05;
            result.reasons.push(`Low velocity variance: CV=${velCV.toFixed(3)}`);
        }
    }

    // 4. Jerk analysis (third derivative of position)
    // High jerk variance = human micro-corrections; low = robotic smoothness
    if (velocities.length >= 8) {
        const accelerations = [];
        for (let i = 1; i < velocities.length; i++) {
            const dt = intervals[i] || 16;
            accelerations.push((velocities[i] - velocities[i - 1]) / dt);
        }
        const jerks = [];
        for (let i = 1; i < accelerations.length; i++) {
            const dt = intervals[i] || 16;
            jerks.push((accelerations[i] - accelerations[i - 1]) / dt);
        }
        if (jerks.length >= 5) {
            const jerkCV = cv(jerks.map(Math.abs));
            if (jerkCV < 0.2 && mean(jerks.map(Math.abs)) > 0) {
                penalty += 0.06;
                result.reasons.push(`Low jerk variance: CV=${jerkCV.toFixed(3)} (too smooth)`);
            }
        }
    }

    // 5. Straightness index
    // Ratio of path length to direct distance over sliding windows
    // Human: 1.02-1.5 (curved paths), Bot: ~1.0 (straight lines)
    if (points.length >= 20) {
        const windowSize = 15;
        const straightnessValues = [];
        for (let i = 0; i <= points.length - windowSize; i += 5) {
            const segment = points.slice(i, i + windowSize);
            const directDist = dist(
                segment[0].x,
                segment[0].y,
                segment[segment.length - 1].x,
                segment[segment.length - 1].y
            );
            if (directDist < 5) continue; // skip near-stationary segments
            let pathLength = 0;
            for (let j = 1; j < segment.length; j++) {
                pathLength += dist(segment[j - 1].x, segment[j - 1].y, segment[j].x, segment[j].y);
            }
            straightnessValues.push(pathLength / directDist);
        }

        if (straightnessValues.length >= 3) {
            const avgStraightness = mean(straightnessValues);
            if (avgStraightness < 1.005) {
                penalty += 0.1;
                result.reasons.push(`Perfectly straight paths: idx=${avgStraightness.toFixed(4)}`);
            } else if (avgStraightness < 1.015) {
                penalty += 0.04;
                result.reasons.push(`Very straight paths: idx=${avgStraightness.toFixed(4)}`);
            }
        }
    }

    // 6. Direction change entropy
    // Angle changes between consecutive segments should be variable for humans
    const angles = [];
    for (let i = 1; i < points.length - 1; i++) {
        const dx1 = points[i].x - points[i - 1].x;
        const dy1 = points[i].y - points[i - 1].y;
        const dx2 = points[i + 1].x - points[i].x;
        const dy2 = points[i + 1].y - points[i].y;
        if (dx1 !== 0 || dy1 !== 0 || dx2 !== 0 || dy2 !== 0) {
            const angle = Math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2);
            angles.push(angle);
        }
    }

    if (angles.length >= 15) {
        const angleEntropy = shannonEntropy(angles, 24);
        if (angleEntropy < 1.2) {
            penalty += 0.08;
            result.reasons.push(
                `Low direction entropy: ${angleEntropy.toFixed(2)} (mechanical movement)`
            );
        }
    }

    // 7. Timing regularity
    // Human mouse event intervals vary due to attention/hardware; bots are uniform
    if (intervals.length >= 10) {
        const intervalCV = cv(intervals);
        // Only suspicious if intervals are SLOW (fast 60Hz intervals naturally look uniform)
        const avgInterval = mean(intervals);
        if (intervalCV < 0.1 && avgInterval > 50) {
            penalty += 0.08;
            result.reasons.push(
                `Uniform timing: CV=${intervalCV.toFixed(3)}, avg=${avgInterval.toFixed(0)}ms`
            );
        }

        // Check for machine-precise intervals (mode analysis)
        const rounded = intervals.filter((i) => i > 30).map((i) => Math.round(i / 5) * 5);
        const counts = {};
        for (const r of rounded) counts[r] = (counts[r] || 0) + 1;
        const maxCount = Math.max(...Object.values(counts));
        const modeRatio = maxCount / rounded.length;
        if (modeRatio > 0.7 && rounded.length >= 10 && mean(intervals) > 80) {
            penalty += 0.1;
            result.reasons.push(
                `Machine-precise intervals: ${(modeRatio * 100).toFixed(0)}% identical`
            );
        }
    }

    // 8. Teleportation detection
    // Large displacement in very short time = synthetic
    let teleports = 0;
    for (let i = 1; i < points.length; i++) {
        const d = dist(points[i - 1].x, points[i - 1].y, points[i].x, points[i].y);
        const dt = points[i].t - points[i - 1].t;
        if (d > 300 && dt < 10) teleports++;
    }
    if (teleports > 0) {
        penalty += Math.min(0.15, teleports * 0.08);
        result.reasons.push(`Mouse teleportation: ${teleports} jumps`);
    }

    // 9. Origin clustering
    // Bots often start at (0,0); real users never position cursor at exact origin
    const originPoints = points.filter((p) => p.x < 2 && p.y < 2).length;
    if (originPoints >= 2) {
        penalty += 0.08;
        result.reasons.push(`${originPoints} points at origin (0,0)`);
    }

    // 10. Bezier-like smooth acceleration (too-perfect curves)
    // Human acceleration is irregular; synthetic bezier curves have constant jerk
    if (points.length >= 20) {
        let smoothSegments = 0;
        let totalSegments = 0;
        for (let i = 3; i < points.length; i++) {
            const ddx1 = points[i - 1].x - points[i - 2].x - (points[i - 2].x - points[i - 3].x);
            const ddy1 = points[i - 1].y - points[i - 2].y - (points[i - 2].y - points[i - 3].y);
            const ddx2 = points[i].x - points[i - 1].x - (points[i - 1].x - points[i - 2].x);
            const ddy2 = points[i].y - points[i - 1].y - (points[i - 1].y - points[i - 2].y);
            const accDiff = Math.sqrt((ddx2 - ddx1) ** 2 + (ddy2 - ddy1) ** 2);
            if (accDiff < 1.5) smoothSegments++;
            totalSegments++;
        }
        if (totalSegments >= 15) {
            const smoothRatio = smoothSegments / totalSegments;
            if (smoothRatio > 0.85) {
                penalty += 0.1;
                result.reasons.push(
                    `Bezier-like curve: ${(smoothRatio * 100).toFixed(0)}% constant acceleration`
                );
            }
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Click Landing Analysis ──────────────────────────────────────────────────
// Humans almost never click the exact geometric center of an element.
// Measuring offset from center across clicks reveals automation.
// Human offsets: ~5-30% of element dimension, normally distributed.
// Bot offsets: <2% (pixel-perfect center clicks).

function analyzeClicks(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.15 };
    const c = data.c;

    if (!c || c.length < 2) {
        if (c && c.length === 0 && data.dur > 5000) {
            result.score = 0.05;
            result.reasons.push('No clicks in extended session');
        }
        return result;
    }

    let penalty = 0;

    // Parse clicks: [offsetX, offsetY, dwell, targetW, targetH]
    const offsets = [];
    const dwells = [];

    for (const click of c) {
        const [ox, oy, dwell, tw, th] = click;
        // Normalized offset from center (0 = center, 1 = edge)
        if (tw > 0 && th > 0) {
            const normOff = Math.sqrt((ox / (tw / 2)) ** 2 + (oy / (th / 2)) ** 2);
            offsets.push(normOff);
        }
        if (dwell >= 0) dwells.push(dwell);
    }

    // 1. Center offset analysis
    if (offsets.length >= 3) {
        const avgOffset = mean(offsets);
        const offsetStd = stddev(offsets);
        const centerClicks = offsets.filter((o) => o < 0.05).length;
        const centerRatio = centerClicks / offsets.length;

        // Humans rarely click exact center (< 5% of element radius)
        if (centerRatio > 0.7) {
            penalty += 0.12;
            result.reasons.push(`${(centerRatio * 100).toFixed(0)}% center clicks (pixel-perfect)`);
        } else if (centerRatio > 0.5) {
            penalty += 0.06;
            result.reasons.push(`${(centerRatio * 100).toFixed(0)}% center clicks (suspicious)`);
        }

        // Very low variance in offsets = automation
        if (offsetStd < 0.02 && offsets.length >= 5) {
            penalty += 0.08;
            result.reasons.push(`Click offset variance too low: std=${offsetStd.toFixed(4)}`);
        }
    }

    // 2. Click dwell time (mousedown → mouseup)
    // Human: 60-250ms with variance. Bot: <10ms or perfectly consistent
    if (dwells.length >= 3) {
        const avgDwell = mean(dwells);
        const dwellCV = cv(dwells);

        if (avgDwell < 10) {
            penalty += 0.08;
            result.reasons.push(`Impossibly fast clicks: avg=${avgDwell.toFixed(0)}ms`);
        } else if (dwellCV < 0.05 && dwells.length >= 5) {
            penalty += 0.06;
            result.reasons.push(`Perfectly uniform click duration: CV=${dwellCV.toFixed(3)}`);
        }

        // Zero dwell = instant click (synthetic event dispatch)
        const zeroDwells = dwells.filter((d) => d === 0).length;
        if (zeroDwells > 0) {
            penalty += 0.08;
            result.reasons.push(`${zeroDwells} zero-duration clicks (dispatched events)`);
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Keystroke Dynamics Analysis ──────────────────────────────────────────────
// Dwell time (key hold) and flight time (gap between keys) form a unique
// rhythm. Even for new users, perfectly even or impossibly fast timing
// signals automation.

function analyzeKeystrokes(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.15 };
    const k = data.k;

    if (!k || k.length < 3) return result;

    let penalty = 0;

    // Parse keystrokes: [dwell, flight]
    const dwells = k.map((e) => e[0]).filter((d) => d > 0);
    const flights = k.map((e) => e[1]).filter((f) => f >= 0);

    // 1. Dwell time analysis
    // Human: 50-200ms typical, variable by finger and key position
    if (dwells.length >= 3) {
        const dwellCV = cv(dwells);
        const avgDwell = mean(dwells);

        if (avgDwell < 5) {
            penalty += 0.1;
            result.reasons.push(`Key dwell impossibly short: avg=${avgDwell.toFixed(1)}ms`);
        } else if (dwellCV < 0.08) {
            penalty += 0.08;
            result.reasons.push(`Uniform key dwell: CV=${dwellCV.toFixed(3)} (robotic)`);
        }

        // All dwells exactly the same = synthetic
        const uniqueDwells = new Set(dwells.map((d) => Math.round(d))).size;
        if (uniqueDwells === 1 && dwells.length >= 5) {
            penalty += 0.1;
            result.reasons.push('All key dwells identical');
        }
    }

    // 2. Flight time analysis
    // Human: variable, 30-500ms typically. Bot: < 10ms or perfectly uniform
    if (flights.length >= 3) {
        const flightCV = cv(flights);
        const avgFlight = mean(flights);

        // Impossibly fast typing (< 15ms between keys)
        const tooFast = flights.filter((f) => f > 0 && f < 15).length;
        if (tooFast > flights.length * 0.3) {
            penalty += 0.1;
            result.reasons.push(`${tooFast} impossibly fast key transitions (<15ms)`);
        }

        if (flightCV < 0.08 && flights.length >= 5) {
            penalty += 0.08;
            result.reasons.push(`Uniform flight time: CV=${flightCV.toFixed(3)}`);
        }
    }

    // 3. Rhythm entropy
    // Combine dwell + flight into a timing sequence and measure entropy
    const timings = [];
    for (let i = 0; i < Math.min(dwells.length, flights.length); i++) {
        timings.push(dwells[i], flights[i]);
    }
    if (timings.length >= 10) {
        const rhythmEntropy = shannonEntropy(timings, 15);
        if (rhythmEntropy < 1.5) {
            penalty += 0.06;
            result.reasons.push(
                `Low rhythm entropy: ${rhythmEntropy.toFixed(2)} (mechanical typing)`
            );
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Scroll Behavior Analysis ────────────────────────────────────────────────
// Humans scroll in variable bursts, pause to read, and frequently scroll
// back up. Bots scroll linearly at constant velocity or not at all.

function analyzeScroll(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.1 };
    const s = data.s;

    if (!s || s.length < 3) return result;

    let penalty = 0;

    // Parse scroll: [scrollY, deltaY, t]
    const positions = s.map((e) => e[0]);
    const deltas = s.map((e) => e[1]);
    const times = s.map((e) => e[2]);

    // 1. Scroll velocity variance
    // Human: highly variable (bursts + pauses). Bot: constant
    const velocities = [];
    for (let i = 1; i < s.length; i++) {
        const dt = times[i] - times[i - 1];
        if (dt > 0) velocities.push(Math.abs(deltas[i]) / dt);
    }

    if (velocities.length >= 5) {
        const velCV = cv(velocities);
        if (velCV < 0.15) {
            penalty += 0.06;
            result.reasons.push(`Constant scroll velocity: CV=${velCV.toFixed(3)}`);
        }
    }

    // 2. Direction reversals
    // Humans frequently reverse scroll direction (reading back). Bots: one direction
    let reversals = 0;
    for (let i = 1; i < deltas.length; i++) {
        if (deltas[i] * deltas[i - 1] < 0) reversals++;
    }
    const reversalRate = deltas.length > 1 ? reversals / (deltas.length - 1) : 0;
    if (reversalRate === 0 && deltas.length >= 10) {
        penalty += 0.04;
        result.reasons.push('No scroll direction reversals');
    }

    // 3. Pause detection
    // Humans pause to read content between scroll bursts (gaps > 300ms)
    let pauses = 0;
    for (let i = 1; i < times.length; i++) {
        if (times[i] - times[i - 1] > 300) pauses++;
    }
    if (pauses === 0 && times.length >= 10) {
        penalty += 0.04;
        result.reasons.push('No scroll pauses (continuous scrolling)');
    }

    // 4. Scroll delta distribution
    // Human: variable scroll amounts. Bot: fixed increments
    if (deltas.length >= 5) {
        const absDelta = deltas.map(Math.abs).filter((d) => d > 0);
        const deltaCV = cv(absDelta);
        if (deltaCV < 0.05 && absDelta.length >= 5) {
            penalty += 0.05;
            result.reasons.push(`Uniform scroll deltas: CV=${deltaCV.toFixed(3)}`);
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Touch Analysis ──────────────────────────────────────────────────────────
// Real fingers produce variable pressure and blob-shaped contact areas.
// Automated touch events report perfect point coordinates with no variation.

function analyzeTouch(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.1 };
    const tc = data.tc;

    if (!tc || tc.length < 5) return result;

    let penalty = 0;

    // Parse touch: [x, y, pressure, radiusX, radiusY, t]
    const pressures = tc.map((e) => e[2]).filter((p) => p > 0);
    const radiiX = tc.map((e) => e[3]).filter((r) => r > 0);
    const radiiY = tc.map((e) => e[4]).filter((r) => r > 0);

    // 1. Pressure variance
    // Real: changes during gesture (0.01-1.0 range with variance)
    // Fake: constant or 0
    if (pressures.length >= 5) {
        const pressCV = cv(pressures);
        if (pressCV < 0.01) {
            penalty += 0.06;
            result.reasons.push(
                `No pressure variation: CV=${pressCV.toFixed(4)} (synthetic touch)`
            );
        }
    } else if (tc.length >= 10) {
        // Many touch events but no pressure data = likely synthetic
        penalty += 0.04;
        result.reasons.push('Touch events without pressure data');
    }

    // 2. Contact area variation
    // Real fingers: contact area (radiusX/Y) changes as finger rolls
    if (radiiX.length >= 5) {
        const rxCV = cv(radiiX);
        const ryCV = cv(radiiY);
        if (rxCV < 0.01 && ryCV < 0.01) {
            penalty += 0.05;
            result.reasons.push('Zero contact area variation (point-touch)');
        }
    }

    // 3. Touch trajectory wobble
    // Real swipes have sub-pixel wobble and slight arc
    // Group consecutive touches into gestures (gaps > 100ms = new gesture)
    const gestures = [];
    let current = [tc[0]];
    for (let i = 1; i < tc.length; i++) {
        if (tc[i][5] - tc[i - 1][5] > 100) {
            if (current.length >= 3) gestures.push(current);
            current = [];
        }
        current.push(tc[i]);
    }
    if (current.length >= 3) gestures.push(current);

    for (const gesture of gestures) {
        if (gesture.length < 5) continue;

        // Compute perpendicular deviation from straight line
        const start = gesture[0],
            end = gesture[gesture.length - 1];
        const lineLen = dist(start[0], start[1], end[0], end[1]);
        if (lineLen < 10) continue;

        const deviations = [];
        for (let i = 1; i < gesture.length - 1; i++) {
            const p = gesture[i];
            // Distance from point to line (start → end)
            const cross = Math.abs(
                (end[0] - start[0]) * (start[1] - p[1]) - (start[0] - p[0]) * (end[1] - start[1])
            );
            deviations.push(cross / lineLen);
        }

        const wobbleRMS = Math.sqrt(mean(deviations.map((d) => d * d)));
        if (wobbleRMS < 0.3 && gesture.length >= 8) {
            penalty += 0.04;
            result.reasons.push(`Geometrically perfect swipe: wobble=${wobbleRMS.toFixed(2)}px`);
        }

        // 4. End deceleration
        // Real swipes decelerate at the end; synthetic stop abruptly or stay constant
        if (gesture.length >= 6) {
            const midVelocities = [];
            const endVelocities = [];
            const midEnd = Math.floor(gesture.length * 0.6);

            for (let i = 1; i < gesture.length; i++) {
                const d = dist(gesture[i - 1][0], gesture[i - 1][1], gesture[i][0], gesture[i][1]);
                const dt = gesture[i][5] - gesture[i - 1][5];
                if (dt > 0) {
                    const v = d / dt;
                    if (i < midEnd) midVelocities.push(v);
                    else endVelocities.push(v);
                }
            }

            if (midVelocities.length >= 2 && endVelocities.length >= 2) {
                const midAvg = mean(midVelocities);
                const endAvg = mean(endVelocities);
                // If end velocity >= mid velocity, there's no natural deceleration
                if (midAvg > 0 && endAvg >= midAvg * 0.95) {
                    penalty += 0.03;
                    result.reasons.push('No end-of-swipe deceleration');
                }
            }
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Sensor Analysis (Accelerometer + Gyroscope) ─────────────────────────────
// A human holding a phone introduces constant micro-tremor and postural drift.
// A device on a desk or in automation shows a flat or static sensor stream.
// Real tilting during scrolling/tapping introduces natural orientation changes.

function analyzeSensors(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.1 };
    const ac = data.ac;
    const gy = data.gy;
    const or = data.or;

    // If no sensor data and we're on a device that should have it
    const hasTouchScreen = data.meta?.hasTouchScreen;
    const hasMotionSensors = data.meta?.hasMotionSensors;

    if (hasTouchScreen && !hasMotionSensors) {
        // Touch device without motion sensors = could be emulated
        result.score = 0.03;
        result.reasons.push('Touch device without motion sensors');
        return result;
    }

    if (!ac || ac.length < 5) return result;

    let penalty = 0;

    // Parse accelerometer: [x, y, z, t]
    const acX = ac.map((e) => e[0]);
    const acY = ac.map((e) => e[1]);
    const acZ = ac.map((e) => e[2]);

    // 1. Accelerometer noise floor
    // Real device at rest: stddev ~0.01-0.5 on each axis (micro-vibrations)
    // Emulated: exactly 0 or perfectly static
    const noiseX = stddev(acX);
    const noiseY = stddev(acY);
    const noiseZ = stddev(acZ);
    const totalNoise = noiseX + noiseY + noiseZ;

    if (totalNoise < 0.001) {
        penalty += 0.08;
        result.reasons.push('Zero accelerometer noise (emulated or static)');
    } else if (totalNoise < 0.01) {
        penalty += 0.04;
        result.reasons.push(`Very low accelerometer noise: ${totalNoise.toFixed(4)}`);
    }

    // 2. All-zero check
    const allZero = ac.every((e) => e[0] === 0 && e[1] === 0 && e[2] === 0);
    if (allZero) {
        penalty += 0.08;
        result.reasons.push('All accelerometer readings zero (emulated)');
    }

    // 3. Gyroscope micro-tremor (if available)
    if (gy && gy.length >= 5) {
        const gyAlpha = gy.map((e) => e[0]);
        const gyBeta = gy.map((e) => e[1]);
        const gyGamma = gy.map((e) => e[2]);
        const gyNoise = stddev(gyAlpha) + stddev(gyBeta) + stddev(gyGamma);

        if (gyNoise < 0.0001 && gy.length >= 10) {
            penalty += 0.05;
            result.reasons.push('Zero gyroscope variation (no hand tremor)');
        }
    }

    // 4. Orientation drift
    // Real device: slight orientation drift over time from natural hand movement
    if (or && or.length >= 5) {
        const first = or[0];
        const last = or[or.length - 1];
        const totalDrift =
            Math.abs(last[0] - first[0]) +
            Math.abs(last[1] - first[1]) +
            Math.abs(last[2] - first[2]);
        const duration = (last[3] - first[3]) / 1000; // seconds

        if (totalDrift < 0.01 && duration > 3) {
            penalty += 0.04;
            result.reasons.push('Zero orientation drift (perfectly static device)');
        }
    }

    // 5. Cross-axis correlation
    // Real accelerometer noise is partially correlated between axes
    // Fake random noise is uncorrelated
    if (ac.length >= 20) {
        // Simple correlation check: if noise on X but zero on Y/Z, it's suspicious
        if (noiseX > 0.1 && noiseY < 0.001 && noiseZ < 0.001) {
            penalty += 0.03;
            result.reasons.push('Single-axis accelerometer noise (fabricated)');
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Event Ordering Analysis ─────────────────────────────────────────────────
// Browser events fire in specific sequences. Violations indicate synthetic
// event dispatch. Expected: mousemove → mousedown → mouseup → click.
// Event codes: 0=mousemove 1=mousedown 2=mouseup 3=click 4=keydown
//              5=keyup 6=scroll 7=touchstart 8=touchmove 9=touchend

function analyzeEventOrder(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.05 };
    const ev = data.ev;

    if (!ev || ev.length < 5) return result;

    let penalty = 0;

    // 1. Click without preceding mousedown→mouseup sequence
    let orphanClicks = 0;
    for (let i = 0; i < ev.length; i++) {
        if (ev[i][0] === 3) {
            // click
            // Look back for mousedown(1) then mouseup(2)
            let foundDown = false,
                foundUp = false;
            for (let j = i - 1; j >= Math.max(0, i - 10); j--) {
                if (ev[j][0] === 2) foundUp = true;
                if (ev[j][0] === 1 && foundUp) {
                    foundDown = true;
                    break;
                }
                if (ev[j][0] === 1 && !foundUp) break; // down without up
            }
            if (!foundDown || !foundUp) orphanClicks++;
        }
    }
    if (orphanClicks > 0) {
        penalty += Math.min(0.04, orphanClicks * 0.02);
        result.reasons.push(`${orphanClicks} clicks without mousedown→mouseup sequence`);
    }

    // 2. Keyup without preceding keydown
    let orphanKeyups = 0;
    const pendingKeys = new Set();
    for (const [type] of ev) {
        if (type === 4) pendingKeys.add(type); // simplified: track keydowns
        if (type === 5) {
            if (pendingKeys.size === 0) orphanKeyups++;
            else pendingKeys.clear();
        }
    }
    if (orphanKeyups > 2) {
        penalty += 0.02;
        result.reasons.push(`${orphanKeyups} keyup events without keydown`);
    }

    // 3. Impossible timing: mousedown and mouseup at same timestamp
    for (let i = 1; i < ev.length; i++) {
        if (ev[i - 1][0] === 1 && ev[i][0] === 2 && ev[i][1] === ev[i - 1][1]) {
            penalty += 0.03;
            result.reasons.push('Zero-time mousedown→mouseup (dispatched event)');
            break;
        }
    }

    // 4. Touch events without touchstart
    let touchMovesWithoutStart = 0;
    let inTouch = false;
    for (const [type] of ev) {
        if (type === 7) inTouch = true; // touchstart
        if (type === 8 && !inTouch) touchMovesWithoutStart++; // touchmove without start
        if (type === 9) inTouch = false; // touchend
    }
    if (touchMovesWithoutStart > 0) {
        penalty += 0.02;
        result.reasons.push(`${touchMovesWithoutStart} touchmove events without touchstart`);
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Engagement Analysis ─────────────────────────────────────────────────────
// Time-to-first-interaction and overall engagement depth.

function analyzeEngagement(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.05 };

    let penalty = 0;
    const ttfi = data.ttfi || 0;
    const dur = data.dur || 0;

    // 1. Time to first interaction
    // Humans need at least ~200ms to start interacting after page load
    // Instant interaction = pre-scripted
    if (ttfi > 0 && ttfi < 50) {
        penalty += 0.03;
        result.reasons.push(`Impossibly fast first interaction: ${ttfi}ms`);
    }

    // 2. Very short session with lots of events
    if (dur > 0 && dur < 500) {
        const totalEvents = (data.m?.length || 0) + (data.c?.length || 0) + (data.k?.length || 0);
        if (totalEvents > 50) {
            penalty += 0.03;
            result.reasons.push(`${totalEvents} events in ${dur}ms (burst automation)`);
        }
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Pre-click Deceleration Analysis ─────────────────────────────────────────
// Humans decelerate before clicking (Fitts' Law). Bots maintain constant
// velocity up to the click point.
// This is analyzed by correlating mouse positions with click timestamps.

function analyzePreClickBehavior(data) {
    const result = { score: 0, reasons: [], maxPenalty: 0.1 };
    const m = data.m;
    const c = data.c;

    if (!m || m.length < 10 || !c || c.length < 1) return result;

    let penalty = 0;
    let noDecelCount = 0;
    let totalAnalyzed = 0;

    // For each click, look at mouse movement in the 500ms before it
    for (const click of c) {
        // click: [offsetX, offsetY, dwell, targetW, targetH, clickTime]
        const clickTime = click[5];
        if (clickTime === undefined) continue;

        // Get mouse points in the 500ms window before this click
        const preClickPoints = m.filter((p) => {
            const dt = clickTime - p[2];
            return dt > 0 && dt < 500;
        });

        if (preClickPoints.length < 4) continue;
        totalAnalyzed++;

        // Compute velocities approaching the click
        const vels = [];
        for (let i = 1; i < preClickPoints.length; i++) {
            const dt = preClickPoints[i][2] - preClickPoints[i - 1][2];
            if (dt > 0) {
                const d = dist(
                    preClickPoints[i - 1][0],
                    preClickPoints[i - 1][1],
                    preClickPoints[i][0],
                    preClickPoints[i][1]
                );
                vels.push(d / dt);
            }
        }

        if (vels.length < 3) continue;

        // Check for deceleration: last third should be slower than first third
        const firstThird = vels.slice(0, Math.ceil(vels.length / 3));
        const lastThird = vels.slice(-Math.ceil(vels.length / 3));

        const avgFirst = mean(firstThird);
        const avgLast = mean(lastThird);

        // If not decelerating (last >= first), flag it
        if (avgFirst > 0.5 && avgLast >= avgFirst * 0.9) {
            noDecelCount++;
        }
    }

    if (totalAnalyzed >= 2 && noDecelCount === totalAnalyzed) {
        penalty += 0.08;
        result.reasons.push(`No pre-click deceleration in ${noDecelCount}/${totalAnalyzed} clicks`);
    } else if (totalAnalyzed >= 3 && noDecelCount > totalAnalyzed * 0.7) {
        penalty += 0.04;
        result.reasons.push(
            `Minimal pre-click deceleration: ${noDecelCount}/${totalAnalyzed} clicks`
        );
    }

    result.score = Math.min(penalty, result.maxPenalty);
    return result;
}

// ── Main Analyzer ───────────────────────────────────────────────────────────

export function analyze(data) {
    const categories = {};

    categories.mouse = analyzeMouse(data);
    categories.clicks = analyzeClicks(data);
    categories.preClick = analyzePreClickBehavior(data);
    categories.keystrokes = analyzeKeystrokes(data);
    categories.scroll = analyzeScroll(data);
    categories.touch = analyzeTouch(data);
    categories.sensors = analyzeSensors(data);
    categories.eventOrder = analyzeEventOrder(data);
    categories.engagement = analyzeEngagement(data);

    // Total penalty is sum of all category scores (each capped at maxPenalty)
    let totalPenalty = 0;
    const allReasons = [];

    for (const [name, cat] of Object.entries(categories)) {
        totalPenalty += cat.score;
        for (const reason of cat.reasons) {
            allReasons.push(`[${name}] ${reason}`);
        }
    }

    // Final score: 1.0 = human, 0.0 = bot
    const score = Math.max(0, Math.min(1, 1.0 - totalPenalty));

    return {
        score: Math.round(score * 1000) / 1000,
        penalty: Math.round(totalPenalty * 1000) / 1000,
        reasons: allReasons,
        categories: Object.fromEntries(
            Object.entries(categories).map(([k, v]) => [
                k,
                {
                    penalty: Math.round(v.score * 1000) / 1000,
                    maxPenalty: v.maxPenalty,
                    reasons: v.reasons,
                },
            ])
        ),
    };
}
