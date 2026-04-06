import { execFileSync } from 'child_process';
import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname, basename } from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __dirname = dirname(fileURLToPath(import.meta.url));
const QJS_DIR = resolve(__dirname, '..', 'quickjs');

function buildQjscIfNeeded() {
    const qjscPath = resolve(QJS_DIR, 'qjsc');
    try {
        execFileSync(qjscPath, ['--help'], {
            stdio: 'pipe',
            timeout: 5000,
        });
        return qjscPath;
    } catch (e) {
        if (e.status !== undefined) return qjscPath;
        console.log('Building qjsc...');
        execFileSync('make', ['qjsc'], {
            cwd: QJS_DIR,
            stdio: 'inherit',
            timeout: 120000,
        });
        return qjscPath;
    }
}

function injectAntiDebugTraps(source) {
    return source;
}

function compileToBytecodeCEmbed(qjscPath, sourceFile) {
    const tmpC = resolve(__dirname, '.tmp_bc.c');

    try {
        execFileSync(qjscPath, ['-c', '-s', '-N', 'bytecode_payload', '-o', tmpC, sourceFile], {
            stdio: 'pipe',
            timeout: 30000,
        });

        const cSource = readFileSync(tmpC, 'utf-8');

        const match = cSource.match(/\{([^}]+)\};\s*$/m);
        if (!match) {
            throw new Error('Failed to parse C bytecode array');
        }

        const bytes = match[1]
            .split(',')
            .map((s) => Number(s.trim()))
            .filter((n) => !isNaN(n));

        return Buffer.from(bytes);
    } finally {
        try {
            require('fs').unlinkSync(tmpC);
        } catch {}
    }
}

function compileWithQjs(qjsPath, source) {
    const result = execFileSync(
        qjsPath,
        [
            '--std',
            '-e',
            `
        import * as std from 'std';
        var src = std.loadFile('${source.replace(/'/g, "\\'")}');
        var bc = std.evalScript(src, {
            compile_only: true,
            backtrace_barrier: true,
        });
        var buf = std.writeBytecode(bc);
        std.out.write(buf, 0, buf.byteLength);
        std.out.flush();
        `,
        ],
        {
            stdio: ['pipe', 'pipe', 'pipe'],
            timeout: 30000,
            encoding: 'buffer',
        }
    );

    return result;
}

function buildBundle(bytecode, encryptionKey) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-ctr', encryptionKey, iv);
    const encrypted = Buffer.concat([cipher.update(bytecode), cipher.final()]);

    const header = Buffer.alloc(8);
    header.writeUInt32BE(0x564d4243, 0);
    header.writeUInt32BE(encrypted.length, 4);

    return Buffer.concat([header, iv, encrypted]);
}

function main() {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.error('Usage: node compile.js <input.js> ' + '[--out file] [--key hex] [--inline]');
        process.exit(1);
    }

    let inputFile = null;
    let outputFile = null;
    let keyHex = null;
    let inline = false;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--out') {
            outputFile = args[++i];
        } else if (args[i] === '--key') {
            keyHex = args[++i];
        } else if (args[i] === '--inline') {
            inline = true;
        } else {
            inputFile = args[i];
        }
    }

    if (!inputFile) {
        console.error('No input file specified');
        process.exit(1);
    }

    const source = readFileSync(resolve(inputFile), 'utf-8');

    const instrumented = injectAntiDebugTraps(source);

    const tmpFile = resolve(__dirname, '.tmp_instrumented.js');
    writeFileSync(tmpFile, instrumented);

    const qjscPath = buildQjscIfNeeded();
    let bytecode;

    try {
        bytecode = compileToBytecodeCEmbed(qjscPath, tmpFile);
    } catch {
        const qjsPath = resolve(QJS_DIR, 'qjs');
        try {
            execFileSync('make', ['qjs'], {
                cwd: QJS_DIR,
                stdio: 'inherit',
                timeout: 120000,
            });
        } catch {}
        bytecode = compileWithQjs(qjsPath, tmpFile);
    } finally {
        try {
            const fs = require('fs');
            fs.unlinkSync(tmpFile);
        } catch {}
    }

    const encKey = keyHex ? Buffer.from(keyHex, 'hex') : crypto.randomBytes(32);

    const bundle = buildBundle(bytecode, encKey);

    if (inline) {
        console.log(bundle.toString('base64'));
        if (!keyHex) {
            console.error('Key: ' + encKey.toString('hex'));
        }
        return;
    }

    const outPath = outputFile || resolve(dirname(inputFile), basename(inputFile, '.js') + '.vmbc');
    writeFileSync(outPath, bundle);
    console.log(`Bytecode: ${bytecode.length} bytes`);
    console.log(`Bundle:   ${bundle.length} bytes`);
    console.log(`Output:   ${outPath}`);
    if (!keyHex) {
        console.log(`Key:      ${encKey.toString('hex')}`);
    }
}

main();
