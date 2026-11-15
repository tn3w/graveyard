#!/usr/bin/env node

import { formatProject } from '../lib/formatter.js';

async function main() {
    try {
        await formatProject();
    } catch (error) {
        console.error('Error formatting project:', error.message);
        process.exit(1);
    }
}

main();
