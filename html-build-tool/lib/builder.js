import { readFile, writeFile, mkdir } from 'fs/promises';
import { join, basename, dirname } from 'path';
import { minify as minifyHtml } from 'html-minifier-terser';
import { minify as minifyJs } from 'terser';
import { minify as minifyCss } from 'csso';
import { glob } from 'glob';
import { createHash } from 'crypto';
import { get as httpsGet } from 'https';
import { get as httpGet } from 'http';
import { watch } from 'fs';

const htmlMinifyOptions = {
    collapseWhitespace: true,
    removeComments: true,
    minifyCSS: true,
    minifyJS: true,
    removeAttributeQuotes: true,
    removeRedundantAttributes: true,
    removeScriptTypeAttributes: true,
    removeStyleLinkTypeAttributes: true,
    useShortDoctype: true,
};

const jsMinifyOptions = {
    compress: {
        passes: 2,
        inline: 3,
        unsafe: true,
        unsafe_comps: true,
        unsafe_math: true,
        unsafe_proto: true,
        unsafe_regexp: true,
        unsafe_undefined: true,
    },
    mangle: true,
    format: { comments: false },
};

async function generateSri(content) {
    const hash = createHash('sha512').update(content).digest('base64');
    return `sha512-${hash}`;
}

async function fetchUrl(url) {
    return new Promise((resolve, reject) => {
        const get = url.startsWith('https://') ? httpsGet : httpGet;
        get(url, (res) => {
            if (res.statusCode !== 200) {
                reject(new Error(`Failed to fetch ${url}: ${res.statusCode}`));
                return;
            }
            let data = '';
            res.on('data', (chunk) => (data += chunk));
            res.on('end', () => resolve(data));
        }).on('error', reject);
    });
}

async function readAndMinifyCss(paths) {
    const contents = await Promise.all(paths.map((path) => readFile(path, 'utf8')));
    const combined = contents.join('\n');
    return minifyCss(combined).css;
}

async function readAndMinifyJs(paths) {
    const contents = await Promise.all(paths.map((path) => readFile(path, 'utf8')));
    const combined = contents.join(';\n');
    const cleaned = cleanMultilineStrings(combined);
    const result = await minifyJs(cleaned, jsMinifyOptions);
    return result.code;
}

function cleanMultilineStrings(code) {
    return code.replace(/(['"`])(\s*\n[\s\S]*?)\1/g, (_, quote, content) => {
        const cleaned = content
            .split('\n')
            .map((line) => line.trim())
            .filter((line) => line.length > 0)
            .join(' ');
        return `${quote}${cleaned}${quote}`;
    });
}

function extractPaths(html, tag, attr) {
    const regex = new RegExp(`<${tag}[^>]*${attr}=["']([^"']+)["'][^>]*>`, 'gi');
    const paths = [];
    let match;

    while ((match = regex.exec(html)) !== null) {
        paths.push(match[1]);
    }

    return paths;
}

function extractInlineStyles(html) {
    const styleRegex = /<style[^>]*>([\s\S]*?)<\/style>/gi;
    const styles = [];
    let match;

    while ((match = styleRegex.exec(html)) !== null) {
        styles.push(match[1]);
    }

    return styles;
}

function extractInlineScripts(html) {
    const scriptRegex = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
    const scripts = [];
    let match;

    while ((match = scriptRegex.exec(html)) !== null) {
        scripts.push(match[1]);
    }

    return scripts;
}

async function processTemplate(templatePath, options = {}) {
    const { outputDir = 'dist', verbose = false } = options;

    try {
        const html = await readFile(templatePath, 'utf8');
        const templateName = basename(templatePath);
        let totalOriginalSize = Buffer.byteLength(html, 'utf8');

        const allCssLinks = extractPaths(html, 'link', 'href').filter((path) =>
            path.endsWith('.css')
        );
        const allJsLinks = extractPaths(html, 'script', 'src').filter((path) =>
            path.endsWith('.js')
        );
        const localCssLinks = allCssLinks.filter(
            (path) => !path.startsWith('http://') && !path.startsWith('https://')
        );
        const localJsLinks = allJsLinks.filter(
            (path) => !path.startsWith('http://') && !path.startsWith('https://')
        );
        const remoteCssLinks = allCssLinks.filter(
            (path) => path.startsWith('http://') || path.startsWith('https://')
        );
        const remoteJsLinks = allJsLinks.filter(
            (path) => path.startsWith('http://') || path.startsWith('https://')
        );
        const inlineStyles = extractInlineStyles(html);
        const inlineScripts = extractInlineScripts(html);

        let processedHtml = html;
        let cssReplaced = false;
        let jsReplaced = false;

        if (localCssLinks.length > 0) {
            const cssPaths = localCssLinks.map((link) => link.replace(/^\//, ''));
            if (verbose) {
                for (const path of cssPaths) {
                    const content = await readFile(path, 'utf8');
                    totalOriginalSize += Buffer.byteLength(content, 'utf8');
                }
            }
            const minifiedCss = await readAndMinifyCss(cssPaths);
            const cssSri = await generateSri(minifiedCss);

            const localCssPattern = localCssLinks
                .map((link) => link.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                .join('|');
            const cssRegex = new RegExp(`<link[^>]*href=["'](${localCssPattern})["'][^>]*>`, 'gi');
            const replacement = `<style integrity="${cssSri}">${minifiedCss}</style>`;

            processedHtml = processedHtml.replace(cssRegex, () => {
                if (cssReplaced) return '';
                cssReplaced = true;
                return replacement;
            });
        }

        if (localJsLinks.length > 0) {
            const jsPaths = localJsLinks.map((link) => link.replace(/^\//, ''));
            if (verbose) {
                for (const path of jsPaths) {
                    const content = await readFile(path, 'utf8');
                    totalOriginalSize += Buffer.byteLength(content, 'utf8');
                }
            }
            const minifiedJs = await readAndMinifyJs(jsPaths);
            const jsSri = await generateSri(minifiedJs);

            const localJsPattern = localJsLinks
                .map((link) => link.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                .join('|');
            const jsRegex = new RegExp(
                `<script[^>]*src=["'](${localJsPattern})["'][^>]*><\\/script>`,
                'gi'
            );
            const replacement = `<script integrity="${jsSri}">${minifiedJs}</script>`;

            processedHtml = processedHtml.replace(jsRegex, () => {
                if (jsReplaced) return '';
                jsReplaced = true;
                return replacement;
            });
        }

        for (const url of remoteCssLinks) {
            const content = await fetchUrl(url);
            const sri = await generateSri(content);
            const escapedUrl = url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`<link([^>]*href=["']${escapedUrl}["'][^>]*?)(/?)>`, 'gi');
            processedHtml = processedHtml.replace(
                regex,
                `<link$1 integrity="${sri}" crossorigin="anonymous"$2>`
            );
        }

        for (const url of remoteJsLinks) {
            const content = await fetchUrl(url);
            const sri = await generateSri(content);
            const escapedUrl = url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`<script([^>]*src=["']${escapedUrl}["'][^>]*?)>`, 'gi');
            processedHtml = processedHtml.replace(
                regex,
                `<script$1 integrity="${sri}" crossorigin="anonymous">`
            );
        }

        if (inlineStyles.length > 0) {
            const minifiedCss = minifyCss(inlineStyles.join('\n')).css;
            const cssSri = await generateSri(minifiedCss);

            let styleReplaced = false;
            processedHtml = processedHtml.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, () => {
                if (styleReplaced) return '';
                styleReplaced = true;
                return `<style integrity="${cssSri}">${minifiedCss}</style>`;
            });
        }

        if (inlineScripts.length > 0) {
            const cleanedScripts = inlineScripts.map(cleanMultilineStrings);
            const minifiedJs = (await minifyJs(cleanedScripts.join(';\n'), jsMinifyOptions)).code;
            const jsSri = await generateSri(minifiedJs);

            let scriptReplaced = false;
            processedHtml = processedHtml.replace(
                /<script(?![^>]*\bsrc=)[^>]*>[\s\S]*?<\/script>/gi,
                () => {
                    if (scriptReplaced) return '';
                    scriptReplaced = true;
                    return `<script integrity="${jsSri}">${minifiedJs}</script>`;
                }
            );
        }

        const minifiedHtml = await minifyHtml(processedHtml, htmlMinifyOptions);
        const outputPath = join(outputDir, templateName);
        await mkdir(dirname(outputPath), { recursive: true });
        await writeFile(outputPath, minifiedHtml);

        if (verbose) {
            const minifiedSize = Buffer.byteLength(minifiedHtml, 'utf8');
            const savings = ((1 - minifiedSize / totalOriginalSize) * 100).toFixed(1);
            const sign = minifiedSize < totalOriginalSize ? '' : '+';
            console.log(
                `  ${templateName}: ${totalOriginalSize} → ${minifiedSize} bytes (${sign}${savings}% ${minifiedSize < totalOriginalSize ? 'smaller' : 'larger'})`
            );
        }
    } catch (error) {
        console.error(`Error processing ${templatePath}:`, error.message);
        throw error;
    }
}

export async function build(options = {}) {
    const {
        input = 'templates',
        output = 'dist',
        watch: watchMode = false,
        verbose = false,
    } = options;

    await mkdir(output, { recursive: true });

    const buildAll = async () => {
        const pattern = join(input, '**/*.html');
        const templates = await glob(pattern);

        if (templates.length === 0) {
            console.warn(`No templates found in ${input}/`);
            return;
        }

        const startTime = Date.now();
        await Promise.all(templates.map((t) => processTemplate(t, { outputDir: output, verbose })));
        const duration = Date.now() - startTime;

        console.log(`Built ${templates.length} template(s) in ${duration}ms`);
    };

    await buildAll();

    if (watchMode) {
        console.log(`Watching ${input}/ for changes...`);

        const watcher = watch(input, { recursive: true }, async (eventType, filename) => {
            if (filename && filename.endsWith('.html')) {
                console.log(`\nChange detected: ${filename}`);
                try {
                    await buildAll();
                } catch (error) {
                    console.error('Build failed:', error.message);
                }
            }
        });

        process.on('SIGINT', () => {
            console.log('\nStopping watch mode...');
            watcher.close();
            process.exit(0);
        });
    }
}
