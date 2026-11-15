#!/usr/bin/env node
import { build } from '../lib/builder.js';
import { parseArgs } from 'util';

const { values } = parseArgs({
    options: {
        input: { type: 'string', short: 'i', default: 'templates' },
        output: { type: 'string', short: 'o', default: 'dist' },
        watch: { type: 'boolean', short: 'w', default: false },
        verbose: { type: 'boolean', short: 'v', default: false },
    },
});

build(values).catch(console.error);
