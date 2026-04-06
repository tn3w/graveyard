import { mkdirSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { CaptchaEngine } from './engine.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const outDir = join(__dirname, 'output');
mkdirSync(outDir, { recursive: true });

const engine = new CaptchaEngine();

console.log('Generating captcha set...');
const start = performance.now();
const captcha = engine.generate();
const elapsed = (performance.now() - start).toFixed(1);

writeFileSync(join(outDir, 'reference.png'), captcha.reference);

for (let i = 0; i < captcha.choices.length; i++) {
    const choice = captcha.choices[i];
    const label = choice.correct ? `choice_${i}_CORRECT` : `choice_${i}`;
    writeFileSync(join(outDir, `${label}.png`), choice.image);
}

console.log(`Done in ${elapsed}ms`);
console.log(`  Correct: choice ${captcha.correctIndex}`);
console.log(`  Angle: ${captcha.correctAngle.toFixed(1)}°`);
console.log(`  Output: ${outDir}/`);
