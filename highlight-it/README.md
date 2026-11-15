<p align="center">
	<a href="https://github.com/librecap/librecap">
		<picture>
			<source height="260" media="(prefers-color-scheme: dark)" srcset="https://github.com/tn3w/highlight-it/releases/download/v0.1.4-img/highlight-dark.png">
			<source height="260" media="(prefers-color-scheme: light)" srcset="https://github.com/tn3w/highlight-it/releases/download/v0.1.4-img/highlight-light.png">
			<img height="260" alt="HighlightIt Logo" src="https://github.com/tn3w/highlight-it/releases/download/v0.1.4-img/highlight-light.png">
		</picture>
	</a>
</p>

<h1 align="center">Highlight-It</h1>
<p align="center">A lightweight syntax highlighting library with themes, line numbers, and copy functionality.</p>

Example:

```html
<code class="highlight-it">
def greet(name):
	"""Return a personalized greeting."""
	return f"Hello, {name}!"

# Example usage
if __name__ == "__main__":
	print(greet("World"))
</code>
```

Add highlight-it using this script:

```html
<script src="https://cdn.jsdelivr.net/npm/highlight-it@0.2.7/dist/highlight-it-min.js"></script>
<script>
	window.addEventListener('load', () => {
		HighlightIt.init();
	});
</script>
```

## Slim Version

The slim version is a lightweight alternative that excludes highlight.js from the bundle. This provides several benefits:

- Significantly reduced file size for faster page loads
- Freedom to use your preferred version of highlight.js
- Ability to share a single highlight.js instance across multiple features
- Better control over highlight.js configuration and customization
- Reduced redundancy when highlight.js is already part of your project

To use the slim version, you'll need to include highlight.js separately before loading highlight-it.

```html
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@latest/build/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/highlight-it@latest/dist/highlight-it.slim.js"></script>
<script>
	window.addEventListener('load', () => {
		HighlightIt.init();
	});
</script>
```

## Themes and Styling

Highlight-It provides comprehensive theming support by integrating all themes from [highlight.js](https://github.com/highlightjs/highlight.js/tree/main/src/styles). The library intelligently bundles related theme files (e.g. `theme-dark.css` and `theme-light.css`) into a single `theme.css` file that automatically handles both light and dark modes.

### Adding Themes

Include your preferred theme by adding a stylesheet link:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight-it@latest/dist/styles/a11y.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight-it@latest/dist/styles/github.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight-it@latest/dist/styles/vs2015.min.css">
```

## Data Attributes

HighlightIt supports the following data attributes to customize the appearance and behavior of code blocks:

| Attribute          | Description                                                                     | Example                                                                         |
| ------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `data-language`    | Specifies the programming language for syntax highlighting                      | `<div class="highlight-it" data-language="javascript">const foo = 'bar';</div>` |
| `data-filename`    | Displays a filename in the header and auto-detects language from file extension | `<div class="highlight-it" data-filename="example.js">const foo = 'bar';</div>` |
| `data-theme`       | Sets the theme to 'light', 'dark', or 'auto' for the specific code block        | `<div class="highlight-it" data-theme="dark">const foo = 'bar';</div>`          |
| `data-with-lines`  | Adds line numbers to the code block                                             | `<div class="highlight-it" data-with-lines>const foo = 'bar';</div>`            |
| `data-line-start`  | Sets the starting line number for the code block and enables line numbers       | `<div class="highlight-it" data-line-start="10">const foo = 'bar';</div>`       |
| `data-with-share`  | Adds a share button to the code block and individual lines                      | `<div class="highlight-it" data-with-share>const foo = 'bar';</div>`            |
| `data-with-download` | Adds a download button to the code block                                      | `<div class="highlight-it" data-with-download>const foo = 'bar';</div>`            |
| `data-no-header`   | Removes the header (hides language label but keeps copy button as floating)     | `<div class="highlight-it" data-no-header>const foo = 'bar';</div>`             |
| `data-no-copy`     | Hides the copy button                                                           | `<div class="highlight-it" data-no-copy>const foo = 'bar';</div>`               |
| `data-with-reload` | Enables live updates - code will be rehighlighted when content changes          | `<div class="highlight-it" data-with-reload data-language="javascript"></div>`  |

## Usage Example

```html
<!-- Auto-detect language -->
<div class="highlight-it">
const greeting = 'Hello, world!';
console.log(greeting);
</div>

<!-- Basic usage with language -->
<div class="highlight-it" data-language="javascript">
const greeting = 'Hello, world!';
console.log(greeting);
</div>

<!-- With filename and line numbers -->
<div class="highlight-it" data-filename="app.js" data-with-lines>
function calculateTotal(items) {
    return items
        .map((item) => item.price)
        .reduce((total, price) => total + price, 0);
}
</div>

<!-- With filename and line numbers starting from line 10 -->
<div class="highlight-it" data-filename="app.js" data-line-start="10">
function calculateTotal(items) {
	return items
		.map((item) => item.price)
		.reduce((total, price) => total + price, 0);
}
</div>

<!-- With share button -->
<div class="highlight-it" data-language="javascript" data-with-share>
const greeting = 'Hello, world!';
console.log(greeting);
</div>

<!-- With download button -->
<div class="highlight-it" data-language="javascript" data-with-download>
const greeting = 'Hello, world!';
console.log(greeting);
</div>

<!-- With download button and specific filename -->
<div class="highlight-it" data-language="javascript" data-with-download data-filename="app.js">
const greeting = 'Hello, world!';
console.log(greeting);
</div>

<!-- Dark theme without header -->
<div class="highlight-it" data-language="css" data-theme="dark" data-no-header>
.container {
	display: flex;
	justify-content: center;
}
</div>

<!-- With live updates for streaming code -->
<div class="highlight-it" data-language="python" data-with-reload>
	# This code will be automatically rehighlighted as content changes
</div>
```

## Initialization

To initialize HighlightIt with custom options:

```javascript
// Default configuration
HighlightIt.init()

// Custom configuration
HighlightIt.init({
	selector: '.custom-code', // Custom CSS selector
	autoDetect: true, // Auto-detect language if not specified
	addCopyButton: true, // Add copy button to code blocks
	showLanguage: true, // Show language label in header
	addHeader: true, // Add header section to code blocks
	addLines: false, // Add line numbers to code blocks
	addShare: true, // Add share button to code blocks
	addDownload: true, // Add download button to code blocks
	theme: 'auto', // Global theme (light, dark, auto)
	debounceTime: 40 // Debounce time in ms for live updates (lower values = more responsive)
})
```

## Live Updates

The `data-with-reload` attribute enables automatic rehighlighting when code content changes, which is particularly useful for apps that stream in code responses. This feature ensures that code syntax highlighting is applied in real-time as code is being added to the DOM.

### Implementation Example

```javascript
// Create an empty code block with live updates enabled
const codeBlock = document.createElement('div')
codeBlock.className = 'highlight-it'

// Add it to your container
document.querySelector('.container').appendChild(codeBlock)

// Add it to HighlightIt
HighlightIt.highlight(codeBlock, {
	withReload: true,
	language: 'javascript',
	addHeader: true,
	addCopyButton: true,
	addLines: false,
	addShare: false,
	addDownload: false,
	filename: 'app.js'
})

// HighlightIt will automatically rehighlight the code
function onAiResponseChunk(codeChunk) {
	codeBlock.textContent += codeChunk
	// No need to manually rehighlight - it happens automatically!
}
```

### Benefits

- Real-time syntax highlighting as code streams in
- No need to manually call highlighting functions after content updates
- Ensures users see properly highlighted code even during streaming
- Works with all other HighlightIt features (themes, line numbers, etc.)
- Debounced to optimize performance during rapid updates


## Development

1. Clone the repository

```bash
git clone https://github.com/tn3w/highlight-it.git
```

2. Install dependencies

```bash
npm install
```

3. Build the project

```bash
npm run build
```

Open `demo.html` in your browser to see the library in action.

## License

Copyright 2025 TN3W

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.