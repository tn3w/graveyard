# HTML Build Tool

Build tool for minifying and inlining HTML templates with Subresource Integrity (SRI).

## Usage

Run directly with npx (no installation required):

```bash
npx html-build-tool
```

With options:

```bash
npx html-build-tool --input templates --output public --verbose
npx html-build-tool --watch  # Watch mode for development
```

Or install globally:

```bash
npm install -g html-build-tool
html-build-tool
```

## Options

- `-i, --input <dir>` - Input directory (default: `templates`)
- `-o, --output <dir>` - Output directory (default: `build`)
- `-w, --watch` - Watch mode - rebuild on file changes
- `-v, --verbose` - Show detailed build information

## What it does

- Minifies HTML, CSS, and JavaScript
- Inlines local CSS and JS files
- Generates SRI hashes for all resources (inline and remote)
- Adds integrity attributes to remote resources
- Shows compression statistics in verbose mode
- Watch mode for automatic rebuilds

## Requirements

- Node.js >= 18.0.0
- Your project should have HTML files and any referenced CSS/JS files

## Example

Try the included example:

```bash
# Clone or download this repository
cd html-build-tool

# Build the example
npx html-build-tool --input example/templates --output example --verbose

# View the built file
cat example/index.html

# Or open it in a browser
open example/index.html  # macOS
xdg-open example/index.html  # Linux
start example/index.html  # Windows
```

The example demonstrates:

- HTML minification
- CSS and JavaScript inlining with SRI hashes
- Compression statistics
- Interactive functionality preserved after build
