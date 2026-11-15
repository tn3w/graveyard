const fs = require('fs');
const path = require('path');
const cssnano = require('cssnano');
const postcss = require('postcss');
const UglifyJS = require('uglify-js');
const prettier = require('prettier');

const distDir = path.resolve(__dirname, 'dist');
if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir);
}

const packageJson = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'package.json'), 'utf8'));
const version = packageJson.version;

const currentYear = new Date().getFullYear();
const licenseHeader = `/*!
 * HighlightIt v${version}
 * https://github.com/TN3W/highlight-it
 * (c) ${currentYear} TN3W
 * Released under the Apache 2.0 License
 */\n`;

async function processCssFile(filePath, variableName) {
    const css = fs.readFileSync(filePath, 'utf8');

    const result = await postcss([
        cssnano({
            preset: [
                'default',
                {
                    discardComments: { removeAll: true },
                    normalizeWhitespace: true,
                },
            ],
        }),
    ]).process(css, { from: filePath });

    return `const ${variableName} = "${result.css.replace(/"/g, '\\"').replace(/\n/g, '')}";`;
}

function processJsFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');

    return content
        .replace(
            /import\s+(?:(?:[^{}\s,]+\s*,?\s*)?(?:{[^{}]*})?\s+from\s+)?['"][^'"]+['"];?\n?/g,
            ''
        )
        .replace(/export default HighlightIt;?\n?/g, '');
}

function extractLocalImports(filePath, basePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const imports = [];

    const importRegex =
        /import\s+(?:([^{}\s,]+)\s*,?\s*)?(?:{([^{}]*)})?\s+from\s+['"](\.[^'"]+)['"];?/g;
    let match;

    while ((match = importRegex.exec(content)) !== null) {
        const defaultImport = match[1] ? match[1].trim() : null;
        const namedImports = match[2] ? match[2].trim().split(/\s*,\s*/) : [];
        const importPath = match[3];

        const resolvedPath = path.resolve(path.dirname(filePath), importPath);

        let actualPath = resolvedPath;
        if (!path.extname(resolvedPath)) {
            const extensions = ['.js', '.mjs', '.cjs'];
            for (const ext of extensions) {
                const testPath = resolvedPath + ext;
                if (fs.existsSync(testPath)) {
                    actualPath = testPath;
                    break;
                }
            }
        }

        if (!fs.existsSync(actualPath)) {
            actualPath = resolvedPath + '.js';
            if (!fs.existsSync(actualPath)) {
                console.warn(`Warning: Could not resolve import path: ${importPath}`);
                continue;
            }
        }

        const relativePath = path.relative(basePath, actualPath);

        imports.push({
            defaultImport,
            namedImports,
            importPath,
            actualPath,
            relativePath,
        });
    }

    return imports;
}

function processLocalImport(importInfo, processedPaths = new Set()) {
    if (processedPaths.has(importInfo.actualPath)) {
        return ``;
    }

    processedPaths.add(importInfo.actualPath);

    const content = fs.readFileSync(importInfo.actualPath, 'utf8');

    const nestedImports = extractLocalImports(
        importInfo.actualPath,
        path.dirname(importInfo.actualPath)
    );
    let nestedImportCode = '';

    for (const nestedImport of nestedImports) {
        nestedImportCode += processLocalImport(nestedImport, processedPaths);
    }

    let processedContent = content
        .replace(
            /import\s+(?:(?:[^{}\s,]+\s*,?\s*)?(?:{[^{}]*})?\s+from\s+)?['"][^'"]+['"];?\n?/g,
            ''
        )
        .replace(/export\s+default\s+([^;]+);?/g, '')
        .replace(/export\s+const\s+([^=]+)=/g, 'const $1=')
        .replace(/export\s+function\s+([^(]+)/g, 'function $1')
        .replace(/export\s+class\s+([^\s]+)/g, 'class $1')
        .replace(/export\s+\{[^}]*\};?\n?/g, '');

    let output = `// Begin bundled module: ${importInfo.relativePath}\n${nestedImportCode}${processedContent}\n// End bundled module: ${importInfo.relativePath}\n`;

    return output;
}

function extractCssImports(filePath, visitedFiles = new Set()) {
    if (visitedFiles.has(filePath)) {
        return [];
    }
    visitedFiles.add(filePath);

    const content = fs.readFileSync(filePath, 'utf8');
    const directCssImports = [];

    const cssImportRegex = /import\s+['"]\.\/([^'"]+\.css)['"];?\n?/g;
    let match;
    while ((match = cssImportRegex.exec(content))) {
        directCssImports.push(match[1]);
    }

    return directCssImports;
}

function extractCssRules(cssContent) {
    const cleanCss = cssContent.replace(/\/\*![\s\S]*?\*\//g, '').trim();

    const baseStyleRegex = /(?:pre\s+code\.hljs|code\.hljs)[\s\S]*?}/g;
    const baseStyles = [];
    let baseMatch;
    while ((baseMatch = baseStyleRegex.exec(cleanCss)) !== null) {
        baseStyles.push(baseMatch[0]);
    }

    const ruleProperties = {};

    const hljsRegex = /\.hljs\s*{([^{}]*)}/g;
    let match;
    while ((match = hljsRegex.exec(cleanCss)) !== null) {
        const props = match[1].trim();
        if (props) {
            ruleProperties['hljs'] = props;
        }
    }

    const otherRuleRegex =
        /\.hljs-([a-zA-Z0-9_-]+)(?:\s+[a-zA-Z0-9_.*>+[\]=~^$:,"\]]+)*\s*{([^{}]*)}/g;
    while ((match = otherRuleRegex.exec(cleanCss)) !== null) {
        const className = match[0].substring(0, match[0].indexOf('{')).trim();
        const props = match[1] ? match[1].trim() : '';
        if (props) {
            ruleProperties[className] = props;
        }
    }

    return { baseStyles, ruleProperties };
}

function extractPropertiesFromCSS(css, propertiesObj) {
    const cleanCSS = css
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/\s+/g, ' ')
        .trim();

    const ruleRegex = /\.hljs(?:-[a-zA-Z0-9_-]+)?(?:\s+[^{]*)?{([^}]*)}/g;
    let match;

    while ((match = ruleRegex.exec(cleanCSS)) !== null) {
        const selector = match[0].substring(0, match[0].indexOf('{')).trim();
        const properties = match[1].trim();

        if (properties) {
            propertiesObj[selector] = properties;
        }
    }

    return propertiesObj;
}

function removeBackgroundAndColorProps(cssString) {
    if (!cssString) return '';

    return cssString
        .split(';')
        .filter((prop) => {
            const propLower = prop.toLowerCase().trim();
            return !/^background(?!-image)(?!-position)(?!-repeat)(?!-size)(?!-attachment)(?!-origin)(?!-clip).*?\s*:/i.test(
                propLower
            );
        })
        .join(';');
}

function buildContainerCSS(containerSelector, properties) {
    let containerProps = '';
    if (properties['.hljs']) {
        containerProps = properties['.hljs']
            .split(';')
            .filter((prop) => prop.trim())
            .map((prop) => `  ${prop.trim()};`)
            .join('\n');

        containerProps = removeBackgroundAndColorProps(containerProps)
            .split(';')
            .filter((prop) => prop.trim())
            .map((prop) => `  ${prop.trim()};`)
            .join('\n');
    }

    if (containerSelector === ':root') {
        let css = '';

        if (containerProps) {
            css += `${containerSelector} {\n${containerProps}\n}\n\n`;
        }

        for (const selector in properties) {
            if (selector !== '.hljs' && properties[selector]) {
                const filteredProps = removeBackgroundAndColorProps(properties[selector]);

                const propLines = filteredProps
                    .split(';')
                    .filter((prop) => prop.trim())
                    .map((prop) => `  ${prop.trim()};`)
                    .join('\n');

                if (propLines) {
                    css += `${selector} {\n${propLines}\n}\n\n`;
                }
            }
        }

        return css;
    } else {
        let css = `${containerSelector} {\n`;

        if (containerProps) {
            css += `${containerProps}\n`;
        }

        for (const selector in properties) {
            if (selector !== '.hljs' && properties[selector]) {
                const className = selector.replace(/^\./, '');

                const propLines = properties[selector]
                    .split(';')
                    .filter((prop) => prop.trim())
                    .map((prop) => `    ${prop.trim()};`)
                    .join('\n');

                if (propLines) {
                    css += `  .${className} {\n${propLines}\n  }\n\n`;
                }
            }
        }

        css += '}\n';
        return css;
    }
}

async function processCssThemes(stylesDir) {
    const cssFiles = fs
        .readdirSync(stylesDir)
        .filter((file) => file.endsWith('.css') && !file.endsWith('.min.css'));

    const themeGroups = new Map();
    const standaloneFiles = new Set();

    cssFiles.forEach((file) => {
        const baseName = file
            .replace(/-light(-[^.]+)?\.css$/, '')
            .replace(/-dark(-[^.]+)?\.css$/, '')
            .replace(/\.css$/, '');

        if (!themeGroups.has(baseName)) themeGroups.set(baseName, []);
        themeGroups.get(baseName).push(file);
    });

    for (const [, files] of themeGroups) {
        if (files.length === 1 && (files[0].includes('-light') || files[0].includes('-dark'))) {
            standaloneFiles.add(files[0]);
        }
    }

    for (const [baseName, relatedFiles] of themeGroups) {
        const hasVariants = relatedFiles.some((f) => f.includes('-light-') || f.includes('-dark-'));

        if (
            relatedFiles.length === 1 &&
            (standaloneFiles.has(relatedFiles[0]) ||
                (!hasVariants &&
                    !relatedFiles[0].includes('-light') &&
                    !relatedFiles[0].includes('-dark')))
        ) {
            continue;
        }

        const readFile = (file) => fs.readFileSync(path.join(stylesDir, file), 'utf8');
        const extractLicense = (content) => content.match(/\/\*![\s\S]*?\*\//g) || [];
        const writeThemeFile = async (filename, content, licenseHeaders) => {
            try {
                try {
                    const prettierConfig = await prettier.resolveConfig(process.cwd());
                    const formatted = await prettier.format(content, {
                        ...prettierConfig,
                        parser: 'css',
                        printWidth: 100,
                        tabWidth: 2,
                        semi: true,
                        singleQuote: true,
                    });
                    fs.writeFileSync(path.join(stylesDir, filename), formatted);
                } catch (error) {
                    console.warn(`Warning: Error formatting CSS ${filename}:`, error.message);
                    fs.writeFileSync(path.join(stylesDir, filename), content);
                }

                try {
                    const minified = await postcss([cssnano()]).process(
                        content.replace(/\/\*![\s\S]*?\*\//g, ''),
                        { from: path.join(stylesDir, filename) }
                    );
                    fs.writeFileSync(
                        path.join(stylesDir, filename.replace('.css', '.min.css')),
                        licenseHeaders + minified.css
                    );
                } catch (minifyErr) {
                    console.warn(`Warning: Error minifying CSS ${filename}:`, minifyErr.message);
                }
            } catch (error) {
                console.warn(`Warning: Error processing CSS ${filename}:`, error.message);
            }
        };

        const licenseHeaders = new Set();
        let lightFile = null;
        let darkFile = null;

        const explicitLightFile = relatedFiles.find(
            (f) => f.includes('-light') && !f.includes('-light-')
        );
        const explicitDarkFile = relatedFiles.find(
            (f) => f.includes('-dark') && !f.includes('-dark-')
        );
        const baseFile = relatedFiles.find((f) => f === `${baseName}.css`);

        const variantFiles = relatedFiles.filter(
            (f) =>
                f.match(new RegExp(`^${baseName}-[^.]+\\.css$`)) &&
                !f.includes('-light-') &&
                !f.includes('-dark-') &&
                !f.includes('-light') &&
                !f.includes('-dark')
        );

        if (explicitLightFile && explicitDarkFile) {
            lightFile = explicitLightFile;
            darkFile = explicitDarkFile;
        } else if (explicitDarkFile && baseFile) {
            lightFile = baseFile;
            darkFile = explicitDarkFile;
        } else if (explicitLightFile && baseFile) {
            lightFile = explicitLightFile;
            darkFile = baseFile;
        } else if (explicitLightFile) {
            lightFile = darkFile = explicitLightFile;
        } else if (explicitDarkFile) {
            lightFile = darkFile = explicitDarkFile;
        } else if (baseFile && !variantFiles.length) {
            lightFile = darkFile = baseFile;
        } else if (baseFile && variantFiles.length) {
            lightFile = darkFile = baseFile;
        }

        if (lightFile && darkFile) {
            const lightContent = readFile(lightFile);
            const darkContent = readFile(darkFile);

            const allLicenseHeaders = new Set();

            extractLicense(lightContent).forEach((match) => {
                allLicenseHeaders.add(match);
                licenseHeaders.add(match);
            });

            extractLicense(darkContent).forEach((match) => {
                allLicenseHeaders.add(match);
                licenseHeaders.add(match);
            });

            const { baseStyles: lightBaseStyles } = extractCssRules(lightContent);
            const { baseStyles: darkBaseStyles } = extractCssRules(darkContent);

            const lightProps = {};
            const darkProps = {};

            extractPropertiesFromCSS(lightContent, lightProps);
            extractPropertiesFromCSS(darkContent, darkProps);

            const combinedBaseStyles = [...new Set([...lightBaseStyles, ...darkBaseStyles])];
            const combinedLicenseHeaders =
                Array.from(allLicenseHeaders).join('\n\n') + (allLicenseHeaders.size ? '\n\n' : '');

            let combinedContent = combinedLicenseHeaders + combinedBaseStyles.join('\n\n') + '\n\n';
            combinedContent += buildContainerCSS(':root', darkProps) + '\n';
            combinedContent += buildContainerCSS('.highlightit-theme-light', lightProps) + '\n';
            combinedContent +=
                '@media (prefers-color-scheme: light) {\n' +
                buildContainerCSS('  :root.highlightit-theme-auto', lightProps)
                    .split('\n')
                    .map((line) => '  ' + line)
                    .join('\n') +
                '}\n\n';

            const containerSelectors = {
                light:
                    '.highlightit-container[data-theme="light"],\n' +
                    '.highlightit-container pre[data-theme="light"],\n' +
                    '.highlightit-container code[data-theme="light"]',
                dark:
                    '.highlightit-container[data-theme="dark"],\n' +
                    '.highlightit-container pre[data-theme="dark"],\n' +
                    '.highlightit-container code[data-theme="dark"]',
            };

            combinedContent += buildContainerCSS(containerSelectors.light, lightProps) + '\n';
            combinedContent += buildContainerCSS(containerSelectors.dark, darkProps);

            const outputFilename = `${baseName}.css`;
            await writeThemeFile(outputFilename, combinedContent, combinedLicenseHeaders);
        }

        if (hasVariants) {
            const variants = new Map();
            const processedFiles = new Set();

            relatedFiles.forEach((file) => {
                let variant = null,
                    isLight = false,
                    isDark = false;

                if (file.match(/-light-([^.]+)\.css$/)) {
                    variant = file.match(/-light-([^.]+)\.css$/)[1];
                    isLight = true;
                } else if (file.match(/-dark-([^.]+)\.css$/)) {
                    variant = file.match(/-dark-([^.]+)\.css$/)[1];
                    isDark = true;
                } else if (
                    file.match(new RegExp(`^${baseName}-([^.]+)\\.css$`)) &&
                    !file.includes('-light') &&
                    !file.includes('-dark')
                ) {
                    variant = file.match(new RegExp(`^${baseName}-([^.]+)\\.css$`))[1];
                    if (variant === 'dimmed') isDark = true;
                }

                if (variant) {
                    if (!variants.has(variant)) {
                        variants.set(variant, { light: null, dark: null, base: null });
                    }

                    if (isLight) variants.get(variant).light = file;
                    else if (isDark) variants.get(variant).dark = file;
                    else variants.get(variant).base = file;

                    if (
                        file.includes('-light-') ||
                        file.includes('-dark-') ||
                        (file.match(new RegExp(`^${baseName}-[^.]+\\.css$`)) &&
                            !file.match(new RegExp(`^${baseName}\\.css$`)))
                    ) {
                        processedFiles.add(file);
                    }
                }
            });

            for (const [variant, files] of variants.entries()) {
                let variantLightFile = files.light || lightFile;
                let variantDarkFile = files.dark || darkFile;

                if (files.base) {
                    if (variant === 'dimmed') {
                        variantDarkFile = files.base;
                        if (!variantLightFile && lightFile) variantLightFile = lightFile;
                    } else {
                        if (!variantLightFile) variantLightFile = files.base;
                        if (!variantDarkFile) variantDarkFile = files.base;
                    }
                }

                if (!variantLightFile || !variantDarkFile) {
                    console.warn(`Could not find required files for variant: ${variant}, skipping`);
                    continue;
                }

                const variantLicenseHeaders = new Set();
                const variantLightContent = readFile(variantLightFile);
                const variantDarkContent = readFile(variantDarkFile);

                extractLicense(variantLightContent).forEach((match) => {
                    variantLicenseHeaders.add(match);
                });

                extractLicense(variantDarkContent).forEach((match) => {
                    variantLicenseHeaders.add(match);
                });

                if (files.base) {
                    extractLicense(readFile(files.base)).forEach((match) => {
                        variantLicenseHeaders.add(match);
                    });
                }

                const { baseStyles: variantLightBaseStyles } = extractCssRules(variantLightContent);
                const { baseStyles: variantDarkBaseStyles } = extractCssRules(variantDarkContent);

                const variantLightProps = {};
                const variantDarkProps = {};

                extractPropertiesFromCSS(variantLightContent, variantLightProps);
                extractPropertiesFromCSS(variantDarkContent, variantDarkProps);

                const combinedBaseStyles = [
                    ...new Set([...variantLightBaseStyles, ...variantDarkBaseStyles]),
                ];
                const variantCombinedLicenseHeaders =
                    Array.from(variantLicenseHeaders).join('\n\n') +
                    (variantLicenseHeaders.size ? '\n\n' : '');

                let variantCombined =
                    variantCombinedLicenseHeaders + combinedBaseStyles.join('\n\n') + '\n\n';
                variantCombined += buildContainerCSS(':root', variantDarkProps) + '\n';
                variantCombined +=
                    buildContainerCSS('.highlightit-theme-light', variantLightProps) + '\n';
                variantCombined +=
                    '@media (prefers-color-scheme: light) {\n' +
                    buildContainerCSS('  :root.highlightit-theme-auto', variantLightProps)
                        .split('\n')
                        .map((line) => '  ' + line)
                        .join('\n') +
                    '}\n\n';

                const containerSelectors = {
                    light:
                        '.highlightit-container[data-theme="light"],\n' +
                        '.highlightit-container pre[data-theme="light"],\n' +
                        '.highlightit-container code[data-theme="light"]',
                    dark:
                        '.highlightit-container[data-theme="dark"],\n' +
                        '.highlightit-container pre[data-theme="dark"],\n' +
                        '.highlightit-container code[data-theme="dark"]',
                };

                variantCombined +=
                    buildContainerCSS(containerSelectors.light, variantLightProps) + '\n';
                variantCombined += buildContainerCSS(containerSelectors.dark, variantDarkProps);

                const variantFilename = `${baseName}-${variant}.css`;
                await writeThemeFile(
                    variantFilename,
                    variantCombined,
                    variantCombinedLicenseHeaders
                );
            }

            if (lightFile && lightFile !== `${baseName}.css`) processedFiles.add(lightFile);
            if (darkFile && darkFile !== `${baseName}.css`) processedFiles.add(darkFile);

            processedFiles.forEach((file) => {
                if (file === `${baseName}.css`) {
                    return;
                }

                const filePath = path.join(stylesDir, file);
                const minFilePath = filePath.replace('.css', '.min.css');

                if (fs.existsSync(filePath)) {
                    fs.unlinkSync(filePath);
                }

                if (fs.existsSync(minFilePath)) {
                    fs.unlinkSync(minFilePath);
                }
            });
        }

        relatedFiles.forEach((file) => {
            if (standaloneFiles.has(file)) {
                return;
            }

            const isLightOrDarkFile = file.includes('-light') || file.includes('-dark');
            const isBaseFile = file === `${baseName}.css`;
            const isVariantFile =
                file.match(new RegExp(`^${baseName}-[^.]+\\.css$`)) && !isLightOrDarkFile;

            if (isLightOrDarkFile || (!isBaseFile && !isVariantFile)) {
                const filePath = path.join(stylesDir, file);
                const minFilePath = filePath.replace('.css', '.min.css');

                if (fs.existsSync(filePath)) {
                    fs.unlinkSync(filePath);
                }

                if (fs.existsSync(minFilePath)) {
                    fs.unlinkSync(minFilePath);
                }
            }
        });
    }

    fs.readdirSync(stylesDir)
        .filter(
            (file) =>
                !standaloneFiles.has(file) &&
                (file.includes('-light') || file.includes('-dark')) &&
                file.endsWith('.css')
        )
        .forEach((file) => {
            const filePath = path.join(stylesDir, file);
            const minFilePath = filePath.replace('.css', '.min.css');
            if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
            if (fs.existsSync(minFilePath)) fs.unlinkSync(minFilePath);
        });
}

async function build() {
    console.log('Building highlight-it.js and highlight-it-min.js...');

    const tempDir = path.resolve(__dirname, 'temp');
    if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir);
    }

    const tempPackageJson = {
        name: 'highlight-it-temp',
        dependencies: {
            'highlight.js': 'latest',
        },
    };

    fs.writeFileSync(
        path.resolve(tempDir, 'package.json'),
        JSON.stringify(tempPackageJson, null, 2)
    );

    console.log('Installing latest highlight.js...');
    const { execSync } = require('child_process');

    try {
        execSync('npm install --no-audit --no-fund', { cwd: tempDir, stdio: 'inherit' });
    } catch (error) {
        console.error('Failed to install highlight.js:', error);
        return;
    }

    const hljsPackageJson = JSON.parse(
        fs.readFileSync(path.resolve(tempDir, 'node_modules/highlight.js/package.json'), 'utf8')
    );
    const hljsVersion = hljsPackageJson.version;
    console.log(`Using highlight.js version ${hljsVersion}`);

    const highlightJsLicense = `/*!
 * highlight.js v${hljsVersion}
 * Copyright (c) 2006, Ivan Sagalaev
 * Licensed under the BSD 3-Clause License
 * https://github.com/highlightjs/highlight.js/blob/main/LICENSE
 */\n`;

    const stylesDir = path.resolve(distDir, 'styles');
    if (!fs.existsSync(stylesDir)) {
        fs.mkdirSync(stylesDir);
    }

    const hljsStylesPath = path.resolve(tempDir, 'node_modules/highlight.js/styles');
    console.log('Processing highlight.js styles...');

    const allStyleFiles = fs.readdirSync(hljsStylesPath);

    allStyleFiles
        .filter((file) => file.endsWith('.css'))
        .forEach((styleFile) => {
            const sourcePath = path.resolve(hljsStylesPath, styleFile);
            const destPath = path.resolve(stylesDir, styleFile);
            fs.copyFileSync(sourcePath, destPath);
        });

    await processCssThemes(stylesDir);

    console.log(`Copied ${allStyleFiles.length} highlight.js style files to dist/styles`);

    const hljsMainPath = path.resolve(tempDir, 'node_modules/highlight.js/lib/index.js');

    console.log('Reading highlight.js module...');

    const { rollup } = require('rollup');
    const nodeResolve = require('@rollup/plugin-node-resolve');
    const commonjs = require('@rollup/plugin-commonjs');

    try {
        execSync(
            'npm install --no-save --no-audit --no-fund --no-package-lock rollup @rollup/plugin-node-resolve @rollup/plugin-commonjs',
            {
                cwd: tempDir,
                stdio: 'inherit',
            }
        );

        console.log('Bundling highlight.js...');
        const bundle = await rollup({
            input: hljsMainPath,
            plugins: [nodeResolve(), commonjs()],
        });

        const { output } = await bundle.generate({
            format: 'iife',
            name: 'hljs',
        });

        const hljsCode = output[0].code;
        const indexJsPath = path.resolve(__dirname, 'src/index.js');
        const basePath = path.resolve(__dirname, 'src');

        console.log('Processing local imports...');
        const localImports = extractLocalImports(indexJsPath, basePath);
        const processedPaths = new Set();
        const localImportCode = localImports
            .map((importInfo) => processLocalImport(importInfo, processedPaths))
            .join('\n');

        console.log(`Found ${localImports.length} local imports to bundle`);

        const [cssImports, indexJsContent] = await Promise.all([
            Promise.resolve(extractCssImports(indexJsPath)),
            Promise.resolve(processJsFile(indexJsPath)),
        ]);

        const cssVariablePromises = cssImports.map(async (cssFile) => {
            const cssPath = path.resolve(__dirname, 'src', cssFile);
            const varName = `${path.basename(cssFile, '.css').toUpperCase()}_CSS`;
            return processCssFile(cssPath, varName);
        });

        const cssVariables = await Promise.all(cssVariablePromises);

        const injectCssFunc = `
function injectCSS(css) {
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
}`;

        const combinedCode = [
            '(function(global) {',
            ...cssVariables,
            injectCssFunc,
            hljsCode,
            localImportCode,
            indexJsContent
                .replace(/import\s+.*?from\s+['"].*?['"];?/g, '')
                .replace(/import\s+['"].*?['"];?/g, ''),
            'global.HighlightIt = HighlightIt;',
            'if (typeof window !== "undefined") {',
            '  window.HighlightIt = HighlightIt;',
            '  injectCSS(STYLES_CSS);',
            '}',
            '})(typeof window !== "undefined" ? window : this);',
        ].join('\n\n');

        const slimCode = [
            '(function(global) {',
            ...cssVariables,
            injectCssFunc,
            localImportCode,
            indexJsContent
                .replace(/import\s+.*?from\s+['"].*?['"];?/g, '')
                .replace(/import\s+['"].*?['"];?/g, ''),
            'global.HighlightIt = HighlightIt;',
            'if (typeof window !== "undefined") {',
            '  window.HighlightIt = HighlightIt;',
            '  injectCSS(STYLES_CSS);',
            '}',
            '})(typeof window !== "undefined" ? window : this);',
        ].join('\n\n');

        let formattedCode = combinedCode;
        let formattedSlimCode = slimCode;
        try {
            const prettierConfig = await prettier.resolveConfig(process.cwd());
            formattedCode = await prettier.format(combinedCode, {
                ...prettierConfig,
                parser: 'babel',
                printWidth: 100,
                tabWidth: 2,
                semi: true,
                singleQuote: true,
                trailingComma: 'es5',
            });
            formattedSlimCode = await prettier.format(slimCode, {
                ...prettierConfig,
                parser: 'babel',
                printWidth: 100,
                tabWidth: 2,
                semi: true,
                singleQuote: true,
                trailingComma: 'es5',
            });
        } catch (error) {
            console.warn('Warning: Could not format code with prettier:', error.message);
        }

        const unminifiedWithHeader = licenseHeader + highlightJsLicense + formattedCode;
        fs.writeFileSync(path.resolve(distDir, 'highlight-it.js'), unminifiedWithHeader);

        const unminifiedSlimWithHeader = licenseHeader + formattedSlimCode;
        fs.writeFileSync(path.resolve(distDir, 'highlight-it.slim.js'), unminifiedSlimWithHeader);

        console.log('Minifying JavaScript...');

        const minified = UglifyJS.minify(combinedCode, {
            compress: {
                toplevel: true,
                unsafe: false,
                unsafe_math: false,
                unsafe_proto: false,
                unsafe_regexp: false,
                unsafe_Function: false,
                drop_console: true,
                pure_getters: true,
                passes: 2,
                global_defs: {
                    DEBUG: false,
                },
                dead_code: true,
                drop_debugger: true,
                keep_fargs: false,
                keep_infinity: true,
                reduce_vars: true,
                unused: true,
                hoist_funs: false,
                hoist_vars: false,
                inline: false,
                join_vars: true,
                sequences: true,
                conditionals: true,
                booleans: true,
                if_return: true,
                collapse_vars: true,
                reduce_funcs: false,
                merge_vars: true,
                negate_iife: false,
            },
            mangle: {
                toplevel: true,
                eval: true,
                keep_fnames: false,
                properties: {
                    regex: /^_/,
                    keep_quoted: false,
                    debug: false,
                },
                keep_fargs: false,
            },
            output: {
                comments: /^!/,
                beautify: false,
                ascii_only: true,
                wrap_iife: true,
            },
        });

        const minifiedSlim = UglifyJS.minify(slimCode, {
            compress: {
                toplevel: true,
                unsafe: false,
                unsafe_math: false,
                unsafe_proto: false,
                unsafe_regexp: false,
                unsafe_Function: false,
                drop_console: false,
                pure_getters: true,
                passes: 2,
                global_defs: {
                    DEBUG: false,
                },
                dead_code: true,
                drop_debugger: true,
                keep_fargs: false,
                keep_infinity: true,
                reduce_vars: true,
                unused: true,
                hoist_funs: false,
                hoist_vars: false,
                inline: false,
                join_vars: true,
                sequences: true,
                conditionals: true,
                booleans: true,
                if_return: true,
                collapse_vars: true,
                reduce_funcs: false,
                merge_vars: true,
                negate_iife: false,
            },
            mangle: {
                toplevel: true,
                eval: true,
                keep_fnames: false,
                properties: {
                    regex: /^_/,
                    keep_quoted: false,
                    debug: false,
                },
                keep_fargs: false,
            },
            output: {
                comments: /^!/,
                beautify: false,
                ascii_only: true,
                wrap_iife: true,
            },
        });

        if (minified.error) {
            console.error('Error minifying JavaScript:', minified.error);
            return;
        }

        if (minifiedSlim.error) {
            console.error('Error minifying slim JavaScript:', minifiedSlim.error);
            return;
        }

        fs.writeFileSync(
            path.resolve(distDir, 'highlight-it-min.js'),
            licenseHeader + highlightJsLicense + minified.code
        );

        fs.writeFileSync(
            path.resolve(distDir, 'highlight-it-min.slim.js'),
            licenseHeader + minifiedSlim.code
        );

        fs.rmSync(tempDir, { recursive: true, force: true });

        console.log('Build complete!');
    } catch (error) {
        console.error('Error building highlight-it:', error);
        throw error;
    }
}

build()
    .then(() => {
        const { execSync } = require('child_process');
        const files = [
            'highlight-it.slim.js',
            'highlight-it-min.slim.js',
            'highlight-it.js',
            'highlight-it-min.js',
        ];

        files.forEach((file) => {
            try {
                const filePath = path.resolve(distDir, file);
                const hash = execSync(
                    `openssl dgst -sha512 -binary "${filePath}" | openssl base64 -A`
                ).toString();
                console.log(`\nSRI hash for ${file}:`);
                console.log(`sha512-${hash}`);
            } catch (err) {
                console.warn(`Warning: Could not generate SRI hash for ${file}:`, err.message);
            }
        });
    })
    .catch((err) => {
        console.error('Build failed:', err);
        process.exit(1);
    });
