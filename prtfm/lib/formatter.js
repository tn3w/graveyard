import fs from 'fs/promises';
import { execSync } from 'child_process';

const PRETTIER_BASE = [
    '--single-quote',
    '--print-width=100',
    '--tab-width=4',
    '--trailing-comma=es5',
    '--bracket-spacing',
    '--html-whitespace-sensitivity=css',
    '--end-of-line=lf',
].join(' ');

const PRETTIER_YAML = PRETTIER_BASE.replace('--tab-width=4', '--tab-width=2');

async function fileExists(filePath) {
    try {
        await fs.access(filePath);
        return true;
    } catch {
        return false;
    }
}

export async function formatProject() {
    const prettierignoreExisted = await fileExists('.prettierignore');

    if (!(await fileExists('.prettierignore'))) {
        const ignoreContent = (await fileExists('.gitignore'))
            ? await fs.readFile('.gitignore', 'utf-8')
            : 'node_modules\n';
        await fs.writeFile('.prettierignore', ignoreContent);
    }

    try {
        execSync(`npx --yes prettier --write ${PRETTIER_BASE} "**/*.{html,css,js,json,md}"`, {
            stdio: 'inherit',
        });
        execSync(`npx --yes prettier --write ${PRETTIER_YAML} "**/*.{yml,yaml}"`, {
            stdio: 'inherit',
        });
    } finally {
        if (!prettierignoreExisted) {
            await fs.unlink('.prettierignore');
        }
    }
}
