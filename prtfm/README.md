# prtfm

A Prettier formatter tool for projects that temporarily sets up and runs Prettier without permanently modifying your project configuration.

## Installation

```bash
npm install -g prtfm
```

## Usage

Run in your project directory:

```bash
prtfm
```

Using npx

```bash
npx prtfm
```

This will:

1. Temporarily add Prettier to your devDependencies
2. Create a `.prettierrc` configuration
3. Copy your `.gitignore` to `.prettierignore` (or create a default one)
4. Run `npm install` and format your files
5. Clean up all temporary changes

## What it formats

By default, formats these file types:

- HTML
- CSS
- JavaScript
- JSON
- Markdown

## License

Apache-2.0
