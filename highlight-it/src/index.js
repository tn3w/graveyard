/**
 * HighlightIt - A lightweight syntax highlighting library with themes, line numbers, and copy functionality.
 * Uses highlight.js for code highlighting
 */

import './styles.css';
import polyfills from './polyfills';
import cache from './cache';

import hljs from 'highlight.js';

const BASE62_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

/**
 * HighlightIt class for syntax highlighting
 */
class HighlightIt {
    /**
     * Initialize HighlightIt by finding and highlighting all matching elements
     * @param {Object} options - Configuration options
     * @param {string} [options.selector='.highlight-it'] - CSS selector for elements to highlight
     * @param {boolean} [options.autoDetect=true] - Whether to auto-detect language if not specified
     * @param {boolean} [options.addCopyButton=true] - Whether to add a copy button to code blocks
     * @param {boolean} [options.showLanguage=true] - Whether to show the language label
     * @param {boolean} [options.addHeader=true] - Whether to add the header section to code blocks
     * @param {boolean} [options.addLines=false] - Whether to add line numbers to code blocks
     * @param {boolean} [options.addShare=false] - Whether to add share button to code blocks
     * @param {boolean} [options.addDownload=false] - Whether to add download button to code blocks
     * @param {string} [options.theme='auto'] - Theme to use ('light', 'dark', or 'auto')
     * @param {number} [options.debounceTime=50] - Debounce time in ms for live updates (lower values = more responsive)
     */
    static init(options = {}) {
        const {
            selector = '.highlight-it',
            autoDetect = true,
            addCopyButton = true,
            showLanguage = true,
            addHeader = true,
            addLines = false,
            addShare = false,
            addDownload = false,
            theme = 'auto',
            debounceTime = 50,
        } = options;

        polyfills.init();

        this.debounceTime = debounceTime;
        this.applyGlobalTheme(theme);

        this.isTouchDevice = polyfills.supports.touch;

        if (this.isTouchDevice) {
            polyfills.classList.add(document.documentElement, 'highlightit-touch-device');
        }

        const elements = document.querySelectorAll(`${selector}:not(.highlightit-original)`);

        const chunkSize = 50;
        const processChunk = (startIndex) => {
            const endIndex = Math.min(startIndex + chunkSize, elements.length);
            for (let i = startIndex; i < endIndex; i++) {
                this.processElement(
                    elements[i],
                    autoDetect,
                    addCopyButton,
                    showLanguage,
                    addHeader,
                    addLines,
                    addShare,
                    addDownload
                );
            }
            if (endIndex < elements.length) {
                polyfills.requestAnimationFrame(() => processChunk(endIndex));
            } else {
                if (window.location.hash) {
                    this.scrollToAnchor();
                }
            }
        };

        processChunk(0);
        this._initialized = true;

        this.initSharing();
    }

    /**
     * Generate a hash using SHA-256 and convert to a 12-character base62 string
     * @param {string} input - The string to hash
     * @returns {Promise<string>} - A 12-character base62 hash
     */
    static async generateHash(input) {
        try {
            if (!window.crypto || !window.crypto.subtle) {
                return polyfills.simpleHash(input);
            }

            const TextEncoderClass = window.TextEncoder || polyfills.TextEncoder;
            if (!TextEncoderClass) {
                return polyfills.simpleHash(input);
            }

            const encoder = new TextEncoderClass();
            const data = encoder.encode(input);

            const hashBuffer = await crypto.subtle.digest('SHA-256', data);

            const hashArray = Array.from(new Uint8Array(hashBuffer));

            if (typeof BigInt === 'undefined' && polyfills.BigIntPolyfill) {
                return polyfills.simpleHash(input);
            }

            let base62Hash = '';
            let value = 0n;

            for (let i = 0; i < hashArray.length; i++) {
                value = (value << 8n) | BigInt(hashArray[i]);
            }

            while (value > 0 || base62Hash.length < 12) {
                const remainder = Number(value % 62n);
                base62Hash = BASE62_CHARS[remainder] + base62Hash;
                value = value / 62n;

                if (value === 0n && base62Hash.length < 12) {
                    base62Hash = '0' + base62Hash;
                }
            }

            return base62Hash.slice(-12).padStart(12, '0');
        } catch (err) {
            console.warn('Error generating hash:', err);
            return polyfills.simpleHash(input);
        }
    }

    /**
     * Create a share button for code blocks
     * @param {string} code - The code to generate hash from if no id exists
     * @param {HTMLElement} container - The container element (to extract id)
     * @returns {HTMLElement} - The share button element
     */
    static async createShareButton(code, container) {
        const shareButton = document.createElement('button');
        shareButton.className = 'highlightit-button highlightit-share';
        shareButton.setAttribute('aria-label', 'Copy link to this code');
        shareButton.innerHTML = cache.svgIcons.share;

        const originalId = container.getAttribute('data-original-id');
        const containerId = container.id;
        let blockId = originalId || containerId;

        if (!blockId) {
            blockId = await this.generateHash(code);
            container.id = blockId;
        }

        const clickListener = async () => {
            const currentId = container.getAttribute('data-original-id') || container.id;
            const url = new URL(window.location.href);
            url.hash = currentId;

            const success = await polyfills.copyToClipboard(url.toString());

            if (success) {
                shareButton.classList.add('copied');
                shareButton.innerHTML = cache.svgIcons.check;

                setTimeout(() => {
                    shareButton.classList.remove('copied');
                    shareButton.innerHTML = cache.svgIcons.share;
                }, 2000);
            }
        };

        shareButton.addEventListener('click', clickListener);
        shareButton.onclickBackup = clickListener;
        shareButton._currentBlockId = blockId;

        return shareButton;
    }

    /**
     * Update block ID when code changes for blocks with live updates
     * @param {HTMLElement} container - The container element
     * @param {string} newCode - The new code content
     * @returns {Promise<string>} - The updated block ID
     */
    static async updateBlockId(container, newCode) {
        const originalId = container.getAttribute('data-original-id');

        if (originalId) {
            const originalElement = document.querySelector(
                `.highlightit-original[id="${originalId}"]`
            );

            if (originalElement) {
                if (originalElement.id !== originalId) {
                    originalElement.id = originalId;
                }

                if (container.id === originalId) {
                    container.id = '';
                }

                container.setAttribute('data-original-id', originalId);
            } else {
                if (!container.id || container.id !== originalId) {
                    container.id = originalId;
                }
            }

            return originalId;
        } else if (container.id) {
            return container.id;
        } else {
            try {
                const newId = await this.generateHash(newCode);
                container.id = newId;
                return newId;
            } catch (err) {
                console.error('Error generating hash:', err);
                const fallbackId = 'highlightit-' + Math.random().toString(36).substring(2, 15);
                container.id = fallbackId;
                return fallbackId;
            }
        }
    }

    /**
     * Scroll to the element specified in the URL hash
     * @param {number} [attempts=0] - Number of attempts made so far
     */
    static scrollToAnchor(attempts = 0) {
        const fullHash = window.location.hash.substring(1);
        if (!fullHash) return;

        const hashParts = fullHash.split('_');
        const hash = hashParts[0];
        const lineNumber = hashParts.length > 1 ? parseInt(hashParts[1], 10) : null;

        const target = document.getElementById(hash);
        if (target) {
            if (target.classList.contains('highlightit-original')) {
                const uniqueId = target.getAttribute('data-highlightit-id');
                let visibleTarget = null;

                if (uniqueId) {
                    visibleTarget = document.querySelector(`[data-linked-original="${uniqueId}"]`);
                }

                if (visibleTarget) {
                    setTimeout(() => {
                        this.scrollToHighlightedElement(visibleTarget, lineNumber);
                    }, 100);
                    return;
                }
            }

            setTimeout(() => {
                this.scrollToHighlightedElement(target, lineNumber);
            }, 100);
        } else if (attempts < 10) {
            setTimeout(
                () => {
                    this.scrollToAnchor(attempts + 1);
                },
                300 * (attempts + 1)
            );
        }
    }

    /**
     * Scroll to a highlighted element and optionally to a specific line
     * @param {HTMLElement} element - The element to scroll to
     * @param {number|null} lineNumber - The line number to highlight, if any
     * @private
     */
    static scrollToHighlightedElement(element, lineNumber) {
        if (lineNumber !== null) {
            const container = element.closest('.highlightit-container');
            if (container) {
                const lineNumbers = container.querySelectorAll('.highlightit-line-number');
                for (let i = 0; i < lineNumbers.length; i++) {
                    const ln = lineNumbers[i];
                    if (ln.textContent.trim() === String(lineNumber)) {
                        const lineContainer =
                            ln.closest('.highlightit-line-number-container') || ln;

                        this.createFullWidthHighlight(lineContainer, container);

                        lineContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });

                        return;
                    }
                }
            }
        }

        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        element.classList.add('highlightit-anchor-highlight');
        setTimeout(() => {
            element.classList.remove('highlightit-anchor-highlight');
        }, 2000);
    }

    /**
     * Create a full-width highlight that spans both line numbers and code
     * @param {HTMLElement} lineContainer - The line container element
     * @param {HTMLElement} codeContainer - The code container element
     * @private
     */
    static createFullWidthHighlight(lineContainer, codeContainer) {
        lineContainer.classList.add('highlightit-line-highlight');

        const rect = polyfills.getBoundingClientRect(lineContainer);
        const containerRect = polyfills.getBoundingClientRect(codeContainer);

        const overlay = document.createElement('div');
        overlay.className = 'highlightit-line-highlight-overlay';

        overlay.style.top = `${rect.top - containerRect.top}px`;
        overlay.style.height = `${rect.height}px`;
        overlay.style.width = '100%';
        overlay.style.left = '0';

        codeContainer.appendChild(overlay);

        setTimeout(() => {
            lineContainer.classList.remove('highlightit-line-highlight');
            if (overlay && overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        }, 2500);
    }

    /**
     * Process an element for highlighting, handling both single and nested element structures
     * @param {HTMLElement} element - The element to process
     * @param {boolean} autoDetect - Whether to auto-detect language
     * @param {boolean} addCopyButton - Whether to add a copy button
     * @param {boolean} showLanguage - Whether to show the language label
     * @param {boolean} addHeader - Whether to add header section
     * @param {boolean} addLines - Whether to add line numbers
     * @param {boolean} addShare - Whether to add share button
     * @param {boolean} addDownload - Whether to add download button
     * @private
     */
    static processElement(
        element,
        autoDetect,
        addCopyButton,
        showLanguage,
        addHeader,
        addLines,
        addShare,
        addDownload
    ) {
        let codeElement;
        let preElement;
        let originalElement = null;
        const withLiveUpdates = element.dataset.withReload !== undefined;

        if (element.textContent !== null && element.textContent !== undefined) {
            element.textContent = element.textContent.trim();
        }

        if (element.dataset.lineStart !== undefined) {
            element.dataset.withLines = '';
            addLines = true;
        }

        if (
            element.tagName.toLowerCase() === 'code' &&
            element.parentElement.tagName.toLowerCase() === 'pre'
        ) {
            codeElement = element;
            preElement = element.parentElement;

            if (withLiveUpdates) {
                const uniqueId = 'highlightit-id-' + Math.random().toString(36).substr(2, 9);

                originalElement = document.createElement('pre');
                const originalCodeElement = document.createElement('code');

                originalCodeElement.textContent = element.textContent || '';

                originalElement.classList.add('highlightit-original');

                if (preElement.id) {
                    originalElement.id = preElement.id;
                    preElement.setAttribute('data-original-id', preElement.id);
                    preElement.id = '';
                }

                originalElement.setAttribute('data-highlightit-id', uniqueId);
                originalElement.classList.add('highlightit-visually-hidden');

                if (element.dataset.language) {
                    originalCodeElement.dataset.language = element.dataset.language;
                }

                if (element.dataset.lineStart !== undefined) {
                    originalCodeElement.dataset.lineStart = element.dataset.lineStart;
                }

                if (element.dataset.withShare !== undefined) {
                    originalCodeElement.dataset.withShare = element.dataset.withShare;
                }

                if (element.dataset.withDownload !== undefined) {
                    originalCodeElement.dataset.withDownload = element.dataset.withDownload;
                }

                if (element.dataset.filename !== undefined) {
                    originalCodeElement.dataset.filename = element.dataset.filename;
                }

                originalElement.appendChild(originalCodeElement);

                preElement.dataset.linkedOriginal = uniqueId;

                preElement.classList.add('highlightit-streaming-target');

                preElement.parentNode.insertBefore(originalElement, preElement);
            }
        } else {
            const content = element.textContent || '';

            if (withLiveUpdates) {
                const uniqueId = 'highlightit-id-' + Math.random().toString(36).substr(2, 9);

                originalElement = document.createElement('pre');
                const originalCodeElement = document.createElement('code');

                originalCodeElement.textContent = content;
                originalElement.appendChild(originalCodeElement);

                originalElement.classList.add('highlightit-original');

                if (element.id) {
                    originalElement.id = element.id;
                    element.setAttribute('data-original-id', element.id);
                    element.id = '';
                }

                originalElement.setAttribute('data-highlightit-id', uniqueId);
                originalElement.classList.add('highlightit-visually-hidden');

                if (element.dataset.language) {
                    originalCodeElement.dataset.language = element.dataset.language;
                }

                if (element.dataset.lineStart !== undefined) {
                    originalCodeElement.dataset.lineStart = element.dataset.lineStart;
                }

                if (element.dataset.withShare !== undefined) {
                    originalCodeElement.dataset.withShare = element.dataset.withShare;
                }

                if (element.dataset.withDownload !== undefined) {
                    originalCodeElement.dataset.withDownload = element.dataset.withDownload;
                }

                if (element.dataset.filename !== undefined) {
                    originalCodeElement.dataset.filename = element.dataset.filename;
                }

                element.parentNode.insertBefore(originalElement, element);

                element.setAttribute('data-linked-original', uniqueId);
            }

            const container = document.createElement('div');

            if (element.className.includes('highlight-it')) {
                container.className = 'highlight-it highlightit-container';
            } else {
                container.className = element.className;
            }

            if (element.id && !withLiveUpdates) {
                container.id = element.id;
            }

            preElement = document.createElement('pre');
            codeElement = document.createElement('code');

            codeElement.textContent = content.trim();

            for (const key in element.dataset) {
                container.dataset[key] = element.dataset[key];

                if (key === 'language') {
                    codeElement.dataset.language = element.dataset[key];
                    codeElement.className = `language-${element.dataset[key]}`;
                }

                if (key === 'withLines') {
                    container.classList.add('highlightit-with-lines');
                }

                if (key === 'withDownload') {
                    container.classList.add('highlightit-with-download');
                }

                if (key === 'noHeader') {
                    container.classList.add('highlightit-no-header');
                }

                if (key === 'lineStart') {
                    codeElement.dataset.lineStart = element.dataset[key];
                }
            }

            preElement.appendChild(codeElement);
            container.appendChild(preElement);

            element.parentNode.replaceChild(container, element);
            element = codeElement;
        }

        if (addLines || element.dataset.withLines !== undefined) {
            const container = this.createCodeContainer(element);
            container.classList.add('highlightit-with-lines');
        }

        if (addDownload || element.dataset.withDownload !== undefined) {
            const container = this.createCodeContainer(element);
            container.classList.add('highlightit-with-download');
        }

        this.highlightElement(
            element,
            autoDetect,
            addCopyButton,
            showLanguage,
            addHeader,
            addLines,
            addShare,
            addDownload
        );
    }

    /**
     * Apply global theme to the document root
     * @param {string} theme - Theme to apply ('light', 'dark', or 'auto')
     * @private
     */
    static applyGlobalTheme(theme) {
        document.documentElement.classList.remove(
            'highlightit-theme-light',
            'highlightit-theme-dark',
            'highlightit-theme-auto'
        );

        if (['light', 'dark', 'auto'].includes(theme)) {
            document.documentElement.classList.add(`highlightit-theme-${theme}`);
        } else {
            document.documentElement.classList.add('highlightit-theme-auto');
        }
    }

    /**
     * Highlight a single element
     * @param {HTMLElement} element - The code element to highlight
     * @param {boolean} autoDetect - Whether to auto-detect language
     * @param {boolean} addCopyButton - Whether to add a copy button
     * @param {boolean} showLanguage - Whether to show the language label
     * @param {boolean} addHeader - Whether to add header section
     * @param {boolean} addLines - Whether to add line numbers
     * @param {boolean} addShare - Whether to add share button
     * @param {boolean} addDownload - Whether to add download button
     * @private
     *
     * The element can have various data attributes:
     * - data-language: The programming language for syntax highlighting
     * - data-filename: Filename to display (also used to detect language)
     * - data-theme: Override global theme for this element ('light', 'dark', 'auto')
     * - data-with-lines: Add line numbers to the code block
     * - data-line-start: Set the starting line number (default is 1, can be positive or negative)
     * - data-no-header: Hide the header (language label and copy button)
     * - data-no-copy: Hide the copy button
     * - data-with-reload: Enable live updates - code will be rehighlighted automatically when content changes
     * - data-with-share: Add a share button that copies the URL with the element ID as the fragment
     * - data-with-download: Add a download button that downloads the code as a file
     * - data-filename: Used for the download feature to set the filename for downloaded code
     */
    static highlightElement(
        element,
        autoDetect,
        addCopyButton,
        showLanguage,
        addHeader,
        addLines,
        addShare,
        addDownload
    ) {
        const container = this.createCodeContainer(element);

        const code = (element.textContent || '').trim();

        let language = null;
        let displayLabel = null;
        let filename = null;

        const elementDataset = element.dataset;
        const containerDataset = container.dataset;

        const noHeader =
            !addHeader ||
            elementDataset.noHeader !== undefined ||
            containerDataset.noHeader !== undefined;
        const withLines =
            addLines ||
            elementDataset.withLines !== undefined ||
            containerDataset.withLines !== undefined;
        const withLiveUpdates =
            elementDataset.withReload !== undefined || containerDataset.withReload !== undefined;
        const noCopy = elementDataset.noCopy !== undefined || containerDataset.noCopy !== undefined;
        const withShare =
            addShare ||
            elementDataset.withShare !== undefined ||
            containerDataset.withShare !== undefined;
        const withDownload =
            addDownload ||
            elementDataset.withDownload !== undefined ||
            containerDataset.withDownload !== undefined;

        const shouldAddCopyButton = addCopyButton && !noCopy;

        if (elementDataset.language) {
            language = elementDataset.language;
            displayLabel = language;
        } else if (containerDataset.language) {
            language = containerDataset.language;
            displayLabel = language;
        }

        if (elementDataset.filename) {
            filename = elementDataset.filename;
            language = this.getLanguageFromFilename(filename);
            displayLabel = filename;
        } else if (containerDataset.filename) {
            filename = containerDataset.filename;
            language = this.getLanguageFromFilename(filename);
            displayLabel = filename;
        }

        if (elementDataset.theme) {
            const elementTheme = elementDataset.theme.toLowerCase();
            if (['light', 'dark', 'auto'].includes(elementTheme)) {
                container.classList.add(`highlightit-theme-${elementTheme}`);
            }
        } else if (containerDataset.theme) {
            const elementTheme = containerDataset.theme.toLowerCase();
            if (['light', 'dark', 'auto'].includes(elementTheme)) {
                container.classList.add(`highlightit-theme-${elementTheme}`);
            }
        }

        if (withShare && !withLiveUpdates) {
            const originalId = container.getAttribute('data-original-id');
            const hasId = originalId || container.id;

            if (!hasId) {
                this.generateHash(code).then((blockId) => {
                    container.id = blockId;
                });
            }
        }

        if (
            (showLanguage || shouldAddCopyButton || withShare || withDownload) &&
            addHeader &&
            !noHeader
        ) {
            const header = this.createCodeHeader(
                displayLabel,
                code,
                shouldAddCopyButton,
                showLanguage,
                withShare,
                withDownload,
                container
            );
            container.prepend(header);
        } else if (noHeader) {
            container.classList.add('highlightit-no-header');
            if (shouldAddCopyButton || withShare || withDownload) {
                const floatingBtns = this.createFloatingButtons(
                    code,
                    withShare,
                    withDownload,
                    container
                );
                container.appendChild(floatingBtns);
            }
        }

        if (withLines) {
            container.classList.add('highlightit-with-lines');
        }

        if (withLiveUpdates) {
            this.setupLiveUpdates(element, container, autoDetect, showLanguage, withShare);
        }

        if (!language && autoDetect) {
            const result = this.autoDetectLanguage(code);
            language = result.language || 'unknown';

            element.innerHTML = result.value;
            element.classList.add(`language-${language}`);

            if (withLines) {
                this.addLineNumbers(element, code);
            }

            if (showLanguage && !noHeader) {
                const header = container.querySelector('.highlightit-header');
                if (header) {
                    const languageLabel = header.querySelector('.highlightit-language');
                    if (languageLabel) {
                        languageLabel.textContent = language;
                    } else if (language) {
                        const newLanguageLabel = document.createElement('span');
                        newLanguageLabel.className = 'highlightit-language';
                        newLanguageLabel.textContent = language;
                        header.insertBefore(newLanguageLabel, header.firstChild);
                    }
                }
            }

            return;
        }

        if (language) {
            try {
                let result;
                try {
                    result = hljs.highlight(code, { language });
                } catch (e) {
                    console.error(
                        `HighlightIt: Error highlighting with language ${language}`,
                        e,
                        'This might be because highlight.js is not available. Please ensure its script is included in the page.'
                    );
                    result = { value: this.escapeHtml(code) };
                }
                element.innerHTML = result.value;
                element.classList.add(`language-${language}`);

                if (withLines) {
                    this.addLineNumbers(element, code);
                }
            } catch (error) {
                if (autoDetect) {
                    const result = this.autoDetectLanguage(code);
                    element.innerHTML = result.value;
                    element.classList.add(`language-${result.language || 'unknown'}`);

                    if (withLines) {
                        this.addLineNumbers(element, code);
                    }

                    if (showLanguage && !noHeader) {
                        const header = container.querySelector('.highlightit-header');
                        if (header) {
                            const languageLabel = header.querySelector('.highlightit-language');
                            if (languageLabel && result.language) {
                                languageLabel.textContent = result.language;
                            }
                        }
                    }
                } else {
                    console.error(
                        `HighlightIt: Error highlighting with language ${language}`,
                        error
                    );
                    element.innerHTML = this.escapeHtml(code);

                    if (withLines) {
                        this.addLineNumbers(element, code);
                    }
                }
            }
        } else {
            element.innerHTML = `${this.escapeHtml(code)}`;

            if (withLines) {
                this.addLineNumbers(element, code);
            }
        }
    }

    /**
     * Set up live updates to watch for changes to the code element
     * @param {HTMLElement} element - The code element to watch
     * @param {HTMLElement} container - The container element
     * @param {boolean} autoDetect - Whether to auto-detect language
     * @param {boolean} showLanguage - Whether to show the language label
     * @param {boolean} withShare - Whether to update block ID for sharing
     * @private
     */
    static setupLiveUpdates(element, container, autoDetect, showLanguage, withShare) {
        const MutationObserverClass = window.MutationObserver || polyfills.MutationObserver;
        if (!MutationObserverClass) {
            console.warn('HighlightIt: Live updates not supported in this browser');
            return;
        }

        const debounceTime = this.debounceTime || 30;
        let timeout = null;

        const originalElement = this.findOriginalElement(element, container);
        const elementToWatch = originalElement || element;
        const targetElement = element;

        const language =
            polyfills.dataset.get(element, 'language') ||
            (element.className.match(/language-(\w+)/) || [])[1] ||
            null;

        let detectedLanguage = null;
        if (!language && autoDetect) {
            const code = (
                elementToWatch.querySelector('code') || elementToWatch
            ).textContent.trim();
            if (code) {
                const result = this.autoDetectLanguage(code);
                detectedLanguage = result.language || null;
            }
        }

        let lastProcessedCode = '';

        const rehighlight = () => {
            const originalCode = elementToWatch.querySelector('code') || elementToWatch;
            const code = originalCode.textContent.trim();
            if (!code) return;

            if (code === lastProcessedCode) {
                return;
            }

            lastProcessedCode = code;

            if (withShare) {
                this.updateBlockId(container, code).then(() => {
                    this.updateCodeBlock(targetElement, container, language, code, showLanguage);
                });
            } else {
                if (!language && autoDetect) {
                    if (
                        !detectedLanguage ||
                        (showLanguage &&
                            !container.querySelector('.highlightit-header .highlightit-language'))
                    ) {
                        const result = this.autoDetectLanguage(code);
                        detectedLanguage = result.language || 'unknown';
                        targetElement.innerHTML = result.value;
                        polyfills.classList.add(targetElement, `language-${detectedLanguage}`);

                        if (showLanguage && detectedLanguage) {
                            const header = container.querySelector('.highlightit-header');
                            if (header) {
                                const languageLabel = header.querySelector('.highlightit-language');
                                if (languageLabel) {
                                    languageLabel.textContent = detectedLanguage;
                                } else {
                                    const newLanguageLabel = document.createElement('span');
                                    newLanguageLabel.className = 'highlightit-language';
                                    newLanguageLabel.textContent = detectedLanguage;
                                    header.insertBefore(newLanguageLabel, header.firstChild);
                                }
                            }
                        }
                    } else {
                        try {
                            const result = hljs.highlight(code, { language: detectedLanguage });
                            targetElement.innerHTML = result.value;
                        } catch (e) {
                            console.error(
                                `HighlightIt: Error highlighting with language ${detectedLanguage}`,
                                e,
                                'This might be because highlight.js is not available. Please ensure its script is included in the page.'
                            );
                            targetElement.innerHTML = this.escapeHtml(code);
                        }
                        polyfills.classList.add(targetElement, `language-${detectedLanguage}`);
                    }
                } else {
                    this.updateCodeBlock(targetElement, container, language, code, showLanguage);
                    polyfills.classList.add(targetElement, `language-${language || 'unknown'}`);
                }
            }

            if (container.classList.contains('highlightit-with-lines')) {
                const preElement = targetElement.parentElement;
                const oldLineNumbers = preElement.querySelector('.highlightit-line-numbers');
                const lineCount = code.split('\n').length;

                const oldLineCount = oldLineNumbers
                    ? oldLineNumbers.querySelectorAll('.highlightit-line-number-container')
                          .length ||
                      oldLineNumbers.querySelectorAll('.highlightit-line-number').length
                    : 0;

                let lineStart = parseInt(
                    targetElement.dataset.lineStart || preElement.dataset.lineStart || 1,
                    10
                );

                const currentBlockId = container.getAttribute('data-original-id') || container.id;
                const withShare =
                    container.dataset.withShare !== undefined ||
                    element.dataset.withShare !== undefined;

                this.updateLineNumbersForLiveUpdates(
                    oldLineNumbers,
                    lineCount,
                    oldLineCount,
                    lineStart,
                    withShare,
                    currentBlockId,
                    container
                );
            }
        };

        const observer = new MutationObserver(() => {
            if (timeout) clearTimeout(timeout);
            timeout = setTimeout(() => {
                rehighlight();
                timeout = null;
            }, debounceTime);
        });

        observer.observe(elementToWatch, {
            characterData: true,
            childList: true,
            subtree: true,
        });

        elementToWatch._highlightObserver = observer;
    }

    /**
     * Intelligently update line numbers for live updates, preserving existing DOM elements
     * @param {HTMLElement} lineNumbersWrapper - The line numbers wrapper
     * @param {number} newLineCount - The new line count
     * @param {number} oldLineCount - The old line count
     * @param {number} startLine - The starting line number
     * @param {boolean} withShare - Whether share buttons should be included
     * @param {string} blockId - The block ID for share links
     * @param {HTMLElement} container - The container element
     */
    static updateLineNumbersForLiveUpdates(
        lineNumbersWrapper,
        newLineCount,
        oldLineCount,
        startLine,
        withShare,
        blockId,
        container
    ) {
        if (newLineCount === oldLineCount) {
            const lineNumbers = lineNumbersWrapper.querySelectorAll('.highlightit-line-number');
            const lineShareButtons = lineNumbersWrapper.querySelectorAll('.highlightit-line-share');

            for (let i = 0; i < newLineCount; i++) {
                const lineNumber = startLine + i;

                if (lineNumbers[i]) {
                    lineNumbers[i].textContent = lineNumber;
                }

                if (withShare && blockId && lineShareButtons[i]) {
                    lineShareButtons[i].dataset.lineNumber = lineNumber;

                    if (lineShareButtons[i].dataset.blockId !== blockId) {
                        lineShareButtons[i].dataset.blockId = blockId;

                        const oldClickListener = lineShareButtons[i]._clickListener;
                        if (oldClickListener) {
                            lineShareButtons[i].removeEventListener('click', oldClickListener);
                        }

                        this.setupLineShareButtonHandler(lineShareButtons[i], container);
                    }
                }
            }
            return;
        }

        if (newLineCount > oldLineCount) {
            const fragment = document.createDocumentFragment();

            for (let i = oldLineCount; i < newLineCount; i++) {
                const lineNumber = startLine + i;
                const lineNumberContainer = document.createElement('div');
                lineNumberContainer.className = 'highlightit-line-number-container';

                const span = document.createElement('span');
                span.className = 'highlightit-line-number';
                span.textContent = lineNumber;

                if (withShare && blockId) {
                    span.className += ' highlightit-line-number-shareable';

                    const lineShareButton = document.createElement('button');
                    lineShareButton.className = 'highlightit-line-share';
                    lineShareButton.setAttribute('aria-label', `Copy link to line ${lineNumber}`);
                    lineShareButton.innerHTML = cache.svgIcons.link;
                    lineShareButton.dataset.lineNumber = lineNumber;
                    lineShareButton.dataset.blockId = blockId;

                    this.setupLineShareButtonHandler(lineShareButton, container);

                    lineNumberContainer.appendChild(span);
                    lineNumberContainer.appendChild(lineShareButton);
                } else {
                    lineNumberContainer.appendChild(span);
                }

                fragment.appendChild(lineNumberContainer);
            }

            lineNumbersWrapper.appendChild(fragment);
        } else if (newLineCount < oldLineCount) {
            const allLineContainers = lineNumbersWrapper.querySelectorAll(
                '.highlightit-line-number-container'
            );
            const lineNumbers = lineNumbersWrapper.querySelectorAll('.highlightit-line-number');

            for (let i = newLineCount; i < oldLineCount; i++) {
                if (allLineContainers[i]) {
                    lineNumbersWrapper.removeChild(allLineContainers[i]);
                } else if (lineNumbers[i]) {
                    lineNumbersWrapper.removeChild(lineNumbers[i]);
                }
            }

            for (let i = 0; i < newLineCount; i++) {
                const lineNumber = startLine + i;

                if (allLineContainers[i]) {
                    const span = allLineContainers[i].querySelector('.highlightit-line-number');
                    if (span) {
                        span.textContent = lineNumber;
                    }

                    if (withShare && blockId) {
                        const button =
                            allLineContainers[i].querySelector('.highlightit-line-share');
                        if (button) {
                            button.dataset.lineNumber = lineNumber;

                            if (button.dataset.blockId !== blockId) {
                                button.dataset.blockId = blockId;

                                const oldClickListener = button._clickListener;
                                if (oldClickListener) {
                                    button.removeEventListener('click', oldClickListener);
                                }

                                this.setupLineShareButtonHandler(button, container);
                            }
                        }
                    }
                } else if (lineNumbers[i]) {
                    lineNumbers[i].textContent = lineNumber;
                }
            }
        }
    }

    /**
     * Create a styled container for code block
     * @param {HTMLElement} element - The code element to wrap
     * @returns {HTMLElement} - The container element
     * @private
     */
    static createCodeContainer(element) {
        const preElement = element.parentElement;

        if (
            preElement.parentElement &&
            preElement.parentElement.classList.contains('highlightit-container')
        ) {
            return preElement.parentElement;
        }

        const container = document.createElement('div');
        container.className = 'highlightit-container';

        if (preElement.dataset && preElement.dataset.linkedOriginal) {
            container.dataset.linkedOriginal = preElement.dataset.linkedOriginal;
        } else if (preElement.hasAttribute('data-linked-original')) {
            container.setAttribute(
                'data-linked-original',
                preElement.getAttribute('data-linked-original')
            );
            preElement.removeAttribute('data-linked-original');
        }

        if (preElement.hasAttribute('data-original-id')) {
            container.setAttribute('data-original-id', preElement.getAttribute('data-original-id'));
        }

        if (!container.id) {
            if (preElement.id) {
                container.id = preElement.id;
                preElement.removeAttribute('id');
            } else if (element.id) {
                container.id = element.id;
                element.removeAttribute('id');
            }
        }

        preElement.parentNode.insertBefore(container, preElement);
        container.appendChild(preElement);

        return container;
    }

    /**
     * Create code header with language/filename label and copy button
     * @param {string} displayLabel - The text to display (language or filename)
     * @param {string} code - The code to copy
     * @param {boolean} addCopyButton - Whether to add a copy button
     * @param {boolean} showLanguage - Whether to show the language label
     * @param {boolean} addShareButton - Whether to add a share button
     * @param {boolean} addDownloadButton - Whether to add a download button
     * @param {HTMLElement} container - The container element (for share button)
     * @returns {HTMLElement} - The header element
     */
    static createCodeHeader(
        displayLabel,
        code,
        addCopyButton,
        showLanguage,
        addShareButton,
        addDownloadButton,
        container
    ) {
        const header = document.createElement('div');
        header.className = 'highlightit-header';

        if (showLanguage) {
            const languageLabel = document.createElement('span');
            languageLabel.className = 'highlightit-language';
            languageLabel.textContent = displayLabel || 'unknown';
            header.appendChild(languageLabel);
        } else {
            header.style.justifyContent = 'flex-end';
        }

        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'highlightit-buttons-container';
        buttonContainer.style.display = 'flex';
        buttonContainer.style.alignItems = 'center';

        if (addCopyButton) {
            const copyButton = this.createCopyButton(code);
            buttonContainer.appendChild(copyButton);
        }

        if (addDownloadButton) {
            const downloadButton = this.createDownloadButton(code, displayLabel, container);
            buttonContainer.appendChild(downloadButton);
        }

        if (addShareButton) {
            this.createShareButton(code, container).then((shareButton) => {
                buttonContainer.appendChild(shareButton);
            });
        }

        header.appendChild(buttonContainer);

        return header;
    }

    /**
     * Create copy button element
     * @param {string} code - The code to copy
     * @returns {HTMLElement} - The copy button element
     * @private
     */
    static createCopyButton(code) {
        const copyButton = document.createElement('button');
        copyButton.className = 'highlightit-button highlightit-copy';
        copyButton.setAttribute('aria-label', 'Copy code');
        copyButton.innerHTML = `${cache.svgIcons.copy}${cache.svgIcons.check.replace('highlightit-check-icon', 'highlightit-check-icon" style="display: none;')}`;

        const clickListener = async () => {
            const codeToCopy = code.trim();
            const success = await polyfills.copyToClipboard(codeToCopy);

            if (success) {
                polyfills.classList.add(copyButton, 'copied');

                const copyIcon = copyButton.querySelector('.highlightit-copy-icon');
                const checkIcon = copyButton.querySelector('.highlightit-check-icon');

                if (copyIcon) copyIcon.style.display = 'none';
                if (checkIcon) checkIcon.style.display = 'block';

                setTimeout(() => {
                    polyfills.classList.remove(copyButton, 'copied');

                    if (copyIcon) copyIcon.style.display = 'block';
                    if (checkIcon) checkIcon.style.display = 'none';
                }, 2000);
            } else {
                console.warn('Failed to copy code');
            }
        };

        copyButton.onclickBackup = clickListener;
        copyButton._currentCode = code.trim();
        copyButton.addEventListener('click', clickListener);

        return copyButton;
    }

    /**
     * Create download button element
     * @param {string} code - The code to download
     * @param {string} language - The language of the code (for filename extension)
     * @param {HTMLElement} container - The container element (for filename attribute)
     * @returns {HTMLElement} - The download button element
     * @private
     */
    static createDownloadButton(code, language, container) {
        const downloadButton = document.createElement('button');
        downloadButton.className = 'highlightit-button highlightit-download';
        downloadButton.setAttribute('aria-label', 'Download code');
        downloadButton.innerHTML = `${cache.svgIcons.download}${cache.svgIcons.check.replace('highlightit-check-icon', 'highlightit-check-icon" style="display: none;')}`;

        let filename = container && container.dataset && container.dataset.filename;

        if (!filename) {
            const extension = language ? this.getLanguageFileExtension(language) : 'txt';
            filename = `code.${extension}`;
        }

        const clickListener = async () => {
            const codeToDownload = code.trim();
            const success = polyfills.downloadFile(filename, codeToDownload);

            if (success) {
                polyfills.classList.add(downloadButton, 'copied');
                const downloadIcon = downloadButton.querySelector('.highlightit-download-icon');
                const checkIcon = downloadButton.querySelector('.highlightit-check-icon');

                if (downloadIcon) downloadIcon.style.display = 'none';
                if (checkIcon) checkIcon.style.display = 'block';

                setTimeout(() => {
                    polyfills.classList.remove(downloadButton, 'copied');
                    if (downloadIcon) downloadIcon.style.display = 'block';
                    if (checkIcon) checkIcon.style.display = 'none';
                }, 2000);
            } else {
                console.warn('Failed to download code');
            }
        };

        downloadButton.addEventListener('click', clickListener);
        downloadButton.onclickBackup = clickListener;
        downloadButton._code = code;

        return downloadButton;
    }

    /**
     * Create floating buttons for no-header mode
     * @param {string} code - The code to copy
     * @param {boolean} withShare - Whether to add a share button
     * @param {boolean} withDownload - Whether to add a download button
     * @param {HTMLElement} container - The container element for share functionality
     * @returns {HTMLElement} - The floating buttons container
     * @private
     */
    static createFloatingButtons(code, withShare = false, withDownload = false, container = null) {
        const buttonsContainer = document.createElement('div');
        buttonsContainer.className = 'highlightit-floating-buttons';

        const copyButton = document.createElement('button');
        copyButton.className = 'highlightit-button highlightit-floating highlightit-copy';
        copyButton.setAttribute('aria-label', 'Copy code');
        copyButton.innerHTML = cache.svgIcons.copy;

        copyButton.addEventListener('click', async () => {
            const success = await polyfills.copyToClipboard(code.trim());

            if (success) {
                polyfills.classList.add(copyButton, 'copied');
                copyButton.innerHTML = cache.svgIcons.check;

                setTimeout(() => {
                    polyfills.classList.remove(copyButton, 'copied');
                    copyButton.innerHTML = cache.svgIcons.copy;
                }, 2000);
            }
        });

        buttonsContainer.appendChild(copyButton);

        if (withDownload && container) {
            const downloadButton = document.createElement('button');
            downloadButton.className =
                'highlightit-button highlightit-floating highlightit-download';
            downloadButton.setAttribute('aria-label', 'Download code');
            downloadButton.innerHTML = `${cache.svgIcons.download}${cache.svgIcons.check.replace('highlightit-check-icon', 'highlightit-check-icon" style="display: none;')}`;

            let filename = container && container.dataset && container.dataset.filename;
            let codeLanguage =
                container.querySelector('code') &&
                (container.querySelector('code').dataset.language ||
                    (container.querySelector('code').className.match(/language-(\w+)/) || [])[1]);

            if (!filename) {
                const extension = codeLanguage
                    ? this.getLanguageFileExtension(codeLanguage)
                    : 'txt';
                filename = `code.${extension}`;
            }

            const clickListener = () => {
                const success = polyfills.downloadFile(filename, code.trim());

                if (success) {
                    polyfills.classList.add(downloadButton, 'copied');

                    const downloadIcon = downloadButton.querySelector('.highlightit-download-icon');
                    const checkIcon = downloadButton.querySelector('.highlightit-check-icon');

                    if (downloadIcon) downloadIcon.style.display = 'none';
                    if (checkIcon) checkIcon.style.display = 'block';

                    setTimeout(() => {
                        polyfills.classList.remove(downloadButton, 'copied');

                        if (downloadIcon) downloadIcon.style.display = 'block';
                        if (checkIcon) checkIcon.style.display = 'none';
                    }, 2000);
                }
            };

            downloadButton.addEventListener('click', clickListener);
            downloadButton.onclickBackup = clickListener;
            downloadButton._code = code.trim();

            buttonsContainer.appendChild(downloadButton);
        }

        if (withShare && container) {
            (async () => {
                const shareButton = await this.createShareButton(code, container);
                shareButton.className = 'highlightit-button highlightit-floating highlightit-share';

                if (this.isTouchDevice) {
                    shareButton.style.opacity = '1';
                }

                buttonsContainer.appendChild(shareButton);
            })();
        }

        return buttonsContainer;
    }

    /**
     * Get language from filename extension
     * @param {string} filename - The filename to extract extension from
     * @returns {string|null} - The language name or null if not determined
     * @private
     */
    static getLanguageFromFilename(filename) {
        const extension = filename.split('.').pop().toLowerCase();
        return cache.extensionMap.get(extension) || null;
    }

    /**
     * Auto-detect language with priority given to popular languages
     * @param {string} code - The code to detect the language of
     * @returns {Object} - The highlight.js result object with language and value properties
     * @private
     */
    static autoDetectLanguage(code) {
        try {
            if (!code || code.trim().length < 3) {
                return { value: this.escapeHtml(code), language: 'plaintext' };
            }

            const result = hljs.highlightAuto(code, Array.from(cache.popularLanguages));
            return result.language ? result : hljs.highlightAuto(code);
        } catch (e) {
            console.error(
                'HighlightIt: Error auto-detecting language',
                e,
                'This might be because highlight.js is not available. Please ensure its script is included in the page.'
            );
            return { value: this.escapeHtml(code), language: 'unknown' };
        }
    }

    /**
     * Escape HTML special characters
     * @param {string} html - The HTML string to escape
     * @returns {string} - The escaped HTML string
     * @private
     */
    static escapeHtml(html) {
        return html.replace(/[&<>"'`=/]/g, (char) => cache.htmlEscapes.get(char));
    }

    /**
     * Add line numbers to a code element
     * @param {HTMLElement} element - The code element to add line numbers to
     * @param {string} code - The original code content
     * @private
     */
    static addLineNumbers(element, code) {
        const preElement = element.parentElement;
        if (preElement.querySelector('.highlightit-line-numbers')) return;

        const container = preElement.closest('.highlightit-container');
        const withShare =
            container &&
            (container.dataset.withShare !== undefined || element.dataset.withShare !== undefined);

        const lines = code.trim().split('\n');
        const lineCount = lines.length;

        const lineNumbersWrapper = document.createElement('div');
        lineNumbersWrapper.className = 'highlightit-line-numbers';

        const startLine = parseInt(
            element.dataset.lineStart || preElement.dataset.lineStart || 1,
            10
        );

        const fragment = document.createDocumentFragment();

        let blockId = '';
        if (withShare) {
            blockId = container.getAttribute('data-original-id') || container.id;

            if (!blockId) {
                blockId = 'temp-' + Math.random().toString(36).substr(2, 9);
                container.id = blockId;

                this.generateHash(code).then((hash) => {
                    if (container.id === blockId) {
                        container.id = hash;
                    }

                    const lineNumbers = lineNumbersWrapper.querySelectorAll(
                        '.highlightit-line-number'
                    );
                    lineNumbers.forEach((lineNumber) => {
                        const lineShareBtn = lineNumber.querySelector('.highlightit-line-share');
                        if (lineShareBtn && lineShareBtn.dataset.blockId === blockId) {
                            lineShareBtn.dataset.blockId = hash;
                        }
                    });
                });
            }
        }

        for (let i = 0; i < lineCount; i++) {
            const lineNumberContainer = document.createElement('div');
            lineNumberContainer.className = 'highlightit-line-number-container';

            const span = document.createElement('span');
            span.className = 'highlightit-line-number';
            span.textContent = startLine + i;

            if (withShare && blockId) {
                const lineNumber = startLine + i;
                span.className += ' highlightit-line-number-shareable';

                const lineShareButton = document.createElement('button');
                lineShareButton.className = 'highlightit-line-share';
                lineShareButton.setAttribute('aria-label', `Copy link to line ${lineNumber}`);
                lineShareButton.innerHTML = cache.svgIcons.link;
                lineShareButton.dataset.lineNumber = lineNumber;
                lineShareButton.dataset.blockId = blockId;

                this.setupLineShareButtonHandler(lineShareButton, container);

                lineNumberContainer.appendChild(span);
                lineNumberContainer.appendChild(lineShareButton);
            } else {
                lineNumberContainer.appendChild(span);
            }

            fragment.appendChild(lineNumberContainer);
        }

        lineNumbersWrapper.appendChild(fragment);

        polyfills.classList.add(preElement, 'highlightit-has-line-numbers');
        preElement.insertBefore(lineNumbersWrapper, preElement.firstChild);
    }

    /**
     * Update code block with new content
     * @param {HTMLElement} element - The code element to rehighlight
     * @param {HTMLElement} container - The container element
     * @param {string} languageOrFilename - The language or filename to use
     * @param {string} code - The code content
     * @param {boolean} showLanguage - Whether to show the language label
     * @private
     */
    static updateCodeBlock(element, container, languageOrFilename, code, showLanguage) {
        const cleanedCode = code.trim();
        const withLines =
            container.classList.contains('highlightit-with-lines') ||
            element.dataset.lineStart !== undefined;

        let language = null;
        let displayLabel = languageOrFilename;

        if (languageOrFilename) {
            language = this.getLanguageFromFilename(languageOrFilename) || languageOrFilename;
        }

        try {
            let result;
            try {
                result = language
                    ? hljs.highlight(cleanedCode, { language })
                    : { value: this.escapeHtml(cleanedCode) };
            } catch (e) {
                console.error(
                    `HighlightIt: Error highlighting with language ${language}`,
                    e,
                    'This might be because highlight.js is not available. Please ensure its script is included in the page.'
                );
                result = { value: this.escapeHtml(cleanedCode) };
            }

            element.innerHTML = result.value;

            if (withLines) {
                const oldLineNumbers = container.querySelector('.highlightit-line-numbers');
                const oldLines = oldLineNumbers
                    ? oldLineNumbers.querySelectorAll(
                          '.highlightit-line-number-container, .highlightit-line-number'
                      )
                    : null;

                const lineCount = cleanedCode.split('\n').length;
                const oldLineCount = oldLines ? oldLines.length : 0;

                let lineStart = parseInt(
                    element.dataset.lineStart || container.dataset.lineStart || 1,
                    10
                );

                const currentBlockId = container.getAttribute('data-original-id') || container.id;
                const withShare =
                    container.dataset.withShare !== undefined ||
                    element.dataset.withShare !== undefined;

                if (oldLineNumbers) {
                    if (lineCount !== oldLineCount) {
                        if (lineCount > oldLineCount) {
                            const fragment = document.createDocumentFragment();

                            for (let i = oldLineCount; i < lineCount; i++) {
                                const lineNumber = lineStart + i;
                                const lineNumberContainer = document.createElement('div');
                                lineNumberContainer.className = 'highlightit-line-number-container';

                                const span = document.createElement('span');
                                span.className = 'highlightit-line-number';
                                span.textContent = lineNumber;

                                if (withShare && currentBlockId) {
                                    span.className += ' highlightit-line-number-shareable';

                                    const lineShareButton = document.createElement('button');
                                    lineShareButton.className = 'highlightit-line-share';
                                    lineShareButton.setAttribute(
                                        'aria-label',
                                        `Copy link to line ${lineNumber}`
                                    );
                                    lineShareButton.innerHTML = cache.svgIcons.link;
                                    lineShareButton.dataset.lineNumber = lineNumber;
                                    lineShareButton.dataset.blockId = currentBlockId;

                                    this.setupLineShareButtonHandler(lineShareButton, container);

                                    lineNumberContainer.appendChild(span);
                                    lineNumberContainer.appendChild(lineShareButton);
                                } else {
                                    lineNumberContainer.appendChild(span);
                                }

                                fragment.appendChild(lineNumberContainer);
                            }

                            oldLineNumbers.appendChild(fragment);
                        } else if (lineCount < oldLineCount) {
                            const allLineContainers = oldLineNumbers.querySelectorAll(
                                '.highlightit-line-number-container'
                            );
                            const lineNumbers = oldLineNumbers.querySelectorAll(
                                '.highlightit-line-number'
                            );

                            for (let i = lineCount; i < oldLineCount; i++) {
                                if (allLineContainers[i]) {
                                    oldLineNumbers.removeChild(allLineContainers[i]);
                                } else if (lineNumbers[i]) {
                                    oldLineNumbers.removeChild(lineNumbers[i]);
                                }
                            }
                        }
                    }

                    const allLineContainers = oldLineNumbers.querySelectorAll(
                        '.highlightit-line-number-container'
                    );
                    const lineNumbers = oldLineNumbers.querySelectorAll('.highlightit-line-number');
                    const lineShareButtons =
                        oldLineNumbers.querySelectorAll('.highlightit-line-share');

                    for (let i = 0; i < lineCount; i++) {
                        const lineNumber = lineStart + i;

                        if (allLineContainers[i]) {
                            const span = allLineContainers[i].querySelector(
                                '.highlightit-line-number'
                            );
                            if (span) {
                                span.textContent = lineNumber;
                            }

                            if (withShare && currentBlockId) {
                                const button =
                                    allLineContainers[i].querySelector('.highlightit-line-share');
                                if (button) {
                                    button.dataset.lineNumber = lineNumber;
                                    button.setAttribute(
                                        'aria-label',
                                        `Copy link to line ${lineNumber}`
                                    );

                                    if (button.dataset.blockId !== currentBlockId) {
                                        button.dataset.blockId = currentBlockId;

                                        const oldClickListener = button._clickListener;
                                        if (oldClickListener) {
                                            button.removeEventListener('click', oldClickListener);
                                        }

                                        this.setupLineShareButtonHandler(button, container);
                                    }
                                }
                            }
                        } else if (lineNumbers[i]) {
                            lineNumbers[i].textContent = lineNumber;

                            if (withShare && currentBlockId && lineShareButtons[i]) {
                                lineShareButtons[i].dataset.lineNumber = lineNumber;
                                lineShareButtons[i].setAttribute(
                                    'aria-label',
                                    `Copy link to line ${lineNumber}`
                                );

                                if (lineShareButtons[i].dataset.blockId !== currentBlockId) {
                                    lineShareButtons[i].dataset.blockId = currentBlockId;

                                    const oldClickListener = lineShareButtons[i]._clickListener;
                                    if (oldClickListener) {
                                        lineShareButtons[i].removeEventListener(
                                            'click',
                                            oldClickListener
                                        );
                                    }

                                    this.setupLineShareButtonHandler(
                                        lineShareButtons[i],
                                        container
                                    );
                                }
                            }
                        }
                    }
                } else {
                    this.addLineNumbers(element, cleanedCode);
                }
            }

            const copyButtons = container.querySelectorAll('.highlightit-copy');
            copyButtons.forEach((copyButton) => {
                const currentCode = copyButton._currentCode;

                if (currentCode !== cleanedCode) {
                    const clickListener = copyButton.onclickBackup || copyButton.onclick;

                    if (clickListener) {
                        copyButton.removeEventListener('click', clickListener);
                    }

                    const newClickListener = async () => {
                        const codeToCopy = cleanedCode;
                        const success = await polyfills.copyToClipboard(codeToCopy);

                        if (success) {
                            polyfills.classList.add(copyButton, 'copied');

                            const copyIcon = copyButton.querySelector('.highlightit-copy-icon');
                            const checkIcon = copyButton.querySelector('.highlightit-check-icon');

                            if (copyIcon) copyIcon.style.display = 'none';
                            if (checkIcon) checkIcon.style.display = 'block';

                            setTimeout(() => {
                                polyfills.classList.remove(copyButton, 'copied');

                                if (copyIcon) copyIcon.style.display = 'block';
                                if (checkIcon) checkIcon.style.display = 'none';
                            }, 2000);
                        } else {
                            console.warn('Failed to copy code');
                        }
                    };

                    copyButton.onclickBackup = newClickListener;
                    copyButton._currentCode = cleanedCode;
                    copyButton.addEventListener('click', newClickListener);
                }
            });

            const downloadButtons = container.querySelectorAll('.highlightit-download');
            downloadButtons.forEach((downloadButton) => {
                const currentCode = downloadButton._code;

                if (currentCode !== cleanedCode) {
                    const clickListener = downloadButton.onclickBackup || downloadButton.onclick;

                    if (clickListener) {
                        downloadButton.removeEventListener('click', clickListener);
                    }

                    let filename = container && container.dataset && container.dataset.filename;
                    let codeLanguage =
                        container.querySelector('code') &&
                        (container.querySelector('code').dataset.language ||
                            (container.querySelector('code').className.match(/language-(\w+)/) ||
                                [])[1]);
                    if (!filename) {
                        const extension = codeLanguage
                            ? this.getLanguageFileExtension(codeLanguage)
                            : 'txt';
                        filename = `code.${extension}`;
                    }

                    const newClickListener = () => {
                        const success = polyfills.downloadFile(filename, cleanedCode.trim());

                        if (success) {
                            polyfills.classList.add(downloadButton, 'copied');

                            const downloadIcon = downloadButton.querySelector(
                                '.highlightit-download-icon'
                            );
                            const checkIcon =
                                downloadButton.querySelector('.highlightit-check-icon');

                            if (downloadIcon) downloadIcon.style.display = 'none';
                            if (checkIcon) checkIcon.style.display = 'block';

                            setTimeout(() => {
                                polyfills.classList.remove(downloadButton, 'copied');

                                if (downloadIcon) downloadIcon.style.display = 'block';
                                if (checkIcon) checkIcon.style.display = 'none';
                            }, 2000);
                        }
                    };

                    downloadButton.onclickBackup = newClickListener;
                    downloadButton._code = cleanedCode;
                    downloadButton.addEventListener('click', newClickListener);
                }
            });

            const shareButtons = container.querySelectorAll('.highlightit-share');
            shareButtons.forEach(async (shareButton) => {
                const originalId = container.getAttribute('data-original-id');

                if (originalId) {
                    if (shareButton._currentBlockId !== originalId) {
                        shareButton._currentBlockId = originalId;
                    }
                    return;
                }

                if (container.id) {
                    if (shareButton._currentBlockId !== container.id) {
                        const clickListener = shareButton.onclickBackup || shareButton.onclick;

                        if (clickListener) {
                            shareButton.removeEventListener('click', clickListener);
                        }

                        const newClickListener = async () => {
                            const url = new URL(window.location.href);
                            url.hash = container.id;

                            const success = await polyfills.copyToClipboard(url.toString());

                            if (success) {
                                shareButton.classList.add('copied');
                                shareButton.innerHTML = cache.svgIcons.check;

                                setTimeout(() => {
                                    shareButton.classList.remove('copied');
                                    shareButton.innerHTML = cache.svgIcons.share;
                                }, 2000);
                            }
                        };

                        shareButton.onclickBackup = newClickListener;
                        shareButton._currentBlockId = container.id;
                        shareButton.addEventListener('click', newClickListener);
                    }
                    return;
                }

                const blockId = await this.generateHash(cleanedCode);
                container.id = blockId;

                if (shareButton._currentBlockId !== blockId) {
                    const clickListener = shareButton.onclickBackup || shareButton.onclick;

                    if (clickListener) {
                        shareButton.removeEventListener('click', clickListener);
                    }

                    const newClickListener = async () => {
                        const url = new URL(window.location.href);
                        url.hash = blockId;

                        const success = await polyfills.copyToClipboard(url.toString());

                        if (success) {
                            shareButton.classList.add('copied');
                            shareButton.innerHTML = cache.svgIcons.check;

                            setTimeout(() => {
                                shareButton.classList.remove('copied');
                                shareButton.innerHTML = cache.svgIcons.share;
                            }, 2000);
                        }
                    };

                    shareButton.onclickBackup = newClickListener;
                    shareButton._currentBlockId = blockId;
                    shareButton.addEventListener('click', newClickListener);
                }
            });

            const floatingBtnsContainer = container.querySelector('.highlightit-floating-buttons');
            if (floatingBtnsContainer && container.classList.contains('highlightit-no-header')) {
                const floatingCopyBtn = floatingBtnsContainer.querySelector('.highlightit-copy');
                if (floatingCopyBtn) {
                    const currentCode = floatingCopyBtn._currentCode;

                    if (currentCode !== cleanedCode) {
                        const clickListener = floatingCopyBtn.onclick;

                        if (clickListener) {
                            floatingCopyBtn.removeEventListener('click', clickListener);
                        }

                        const newClickListener = async () => {
                            const success = await polyfills.copyToClipboard(cleanedCode.trim());

                            if (success) {
                                polyfills.classList.add(floatingCopyBtn, 'copied');
                                floatingCopyBtn.innerHTML = cache.svgIcons.check;

                                setTimeout(() => {
                                    polyfills.classList.remove(floatingCopyBtn, 'copied');
                                    floatingCopyBtn.innerHTML = cache.svgIcons.copy;
                                }, 2000);
                            }
                        };

                        floatingCopyBtn._currentCode = cleanedCode;
                        floatingCopyBtn.addEventListener('click', newClickListener);
                    }
                }

                const floatingDownloadBtn =
                    floatingBtnsContainer.querySelector('.highlightit-download');
                if (floatingDownloadBtn) {
                    const currentCode = floatingDownloadBtn._code;

                    if (currentCode !== cleanedCode) {
                        const clickListener =
                            floatingDownloadBtn.onclickBackup || floatingDownloadBtn.onclick;

                        if (clickListener) {
                            floatingDownloadBtn.removeEventListener('click', clickListener);
                        }

                        let filename = container && container.dataset && container.dataset.filename;
                        let codeLanguage =
                            container.querySelector('code') &&
                            (container.querySelector('code').dataset.language ||
                                (container
                                    .querySelector('code')
                                    .className.match(/language-(\w+)/) || [])[1]);

                        if (!filename) {
                            const extension = codeLanguage
                                ? this.getLanguageFileExtension(codeLanguage)
                                : 'txt';
                            filename = `code.${extension}`;
                        }

                        const newClickListener = () => {
                            const success = polyfills.downloadFile(filename, cleanedCode.trim());

                            if (success) {
                                polyfills.classList.add(floatingDownloadBtn, 'copied');

                                const downloadIcon = floatingDownloadBtn.querySelector(
                                    '.highlightit-download-icon'
                                );
                                const checkIcon =
                                    floatingDownloadBtn.querySelector('.highlightit-check-icon');

                                if (downloadIcon) downloadIcon.style.display = 'none';
                                if (checkIcon) checkIcon.style.display = 'block';

                                setTimeout(() => {
                                    polyfills.classList.remove(floatingDownloadBtn, 'copied');

                                    if (downloadIcon) downloadIcon.style.display = 'block';
                                    if (checkIcon) checkIcon.style.display = 'none';
                                }, 2000);
                            }
                        };

                        floatingDownloadBtn.onclickBackup = newClickListener;
                        floatingDownloadBtn._code = cleanedCode;
                        floatingDownloadBtn.addEventListener('click', newClickListener);
                    }
                }

                const floatingShareBtn = floatingBtnsContainer.querySelector('.highlightit-share');
                if (floatingShareBtn) {
                    const originalId = container.getAttribute('data-original-id');

                    if (originalId) {
                        if (floatingShareBtn._currentBlockId !== originalId) {
                            floatingShareBtn._currentBlockId = originalId;
                        }
                    } else if (container.id) {
                        if (floatingShareBtn._currentBlockId !== container.id) {
                            const clickListener = floatingShareBtn.onclick;

                            if (clickListener) {
                                floatingShareBtn.removeEventListener('click', clickListener);
                            }

                            const newClickListener = async () => {
                                const url = new URL(window.location.href);
                                url.hash = container.id;

                                const success = await polyfills.copyToClipboard(url.toString());

                                if (success) {
                                    floatingShareBtn.classList.add('copied');
                                    floatingShareBtn.innerHTML = cache.svgIcons.check;

                                    setTimeout(() => {
                                        floatingShareBtn.classList.remove('copied');
                                        floatingShareBtn.innerHTML = cache.svgIcons.share;
                                    }, 2000);
                                }
                            };

                            floatingShareBtn._currentBlockId = container.id;
                            floatingShareBtn.addEventListener('click', newClickListener);
                        }
                    } else {
                        this.generateHash(cleanedCode).then((blockId) => {
                            container.id = blockId;

                            if (floatingShareBtn._currentBlockId !== blockId) {
                                const clickListener = floatingShareBtn.onclick;

                                if (clickListener) {
                                    floatingShareBtn.removeEventListener('click', clickListener);
                                }

                                const newClickListener = async () => {
                                    const url = new URL(window.location.href);
                                    url.hash = blockId;

                                    const success = await polyfills.copyToClipboard(url.toString());

                                    if (success) {
                                        floatingShareBtn.classList.add('copied');
                                        floatingShareBtn.innerHTML = cache.svgIcons.check;

                                        setTimeout(() => {
                                            floatingShareBtn.classList.remove('copied');
                                            floatingShareBtn.innerHTML = cache.svgIcons.share;
                                        }, 2000);
                                    }
                                };

                                floatingShareBtn._currentBlockId = blockId;
                                floatingShareBtn.addEventListener('click', newClickListener);
                            }
                        });
                    }
                }
            } else if (
                !floatingBtnsContainer &&
                container.classList.contains('highlightit-no-header')
            ) {
                const withShare = container.dataset.withShare !== undefined;
                const withDownload = container.dataset.withDownload !== undefined;
                const newFloatingBtns = this.createFloatingButtons(
                    cleanedCode,
                    withShare,
                    withDownload,
                    container
                );
                container.appendChild(newFloatingBtns);
            }

            if (showLanguage && language) {
                const header = container.querySelector('.highlightit-header');
                if (header) {
                    const languageLabel = header.querySelector('.highlightit-language');
                    if (languageLabel) {
                        languageLabel.textContent = displayLabel || language;
                    } else if (language) {
                        const newLanguageLabel = document.createElement('span');
                        newLanguageLabel.className = 'highlightit-language';
                        newLanguageLabel.textContent = displayLabel || language;
                        header.insertBefore(newLanguageLabel, header.firstChild);
                    }
                }
            }
        } catch (error) {
            console.warn(`HighlightIt: Error highlighting with language ${language}`, error);
            element.innerHTML = this.escapeHtml(cleanedCode);
        }
    }

    /**
     * Setup a click handler for line share buttons
     * @param {HTMLElement} button - The line share button
     * @param {HTMLElement} container - The container element
     */
    static setupLineShareButtonHandler(button, container) {
        const clickListener = async (e) => {
            e.stopPropagation();

            const currentBlockId = container.getAttribute('data-original-id') || container.id;
            const lineNumber = button.dataset.lineNumber;
            const url = new URL(window.location.href);
            url.hash = `${currentBlockId}_${lineNumber}`;

            const success = await polyfills.copyToClipboard(url.toString());

            if (success) {
                button.classList.add('copied');
                button.innerHTML = cache.svgIcons.check;

                const containerElement = button.closest('.highlightit-line-number-container');
                if (containerElement) {
                    containerElement.classList.add('has-copied-button');
                    polyfills.updateHasClass(
                        containerElement,
                        '.highlightit-line-share.copied',
                        'has-copied-button',
                        true
                    );
                }

                setTimeout(() => {
                    button.classList.remove('copied');
                    button.innerHTML = cache.svgIcons.link;

                    if (containerElement) {
                        containerElement.classList.remove('has-copied-button');
                        polyfills.updateHasClass(
                            containerElement,
                            '.highlightit-line-share.copied',
                            'has-copied-button',
                            false
                        );
                    }
                }, 2000);
            }
        };

        button._clickListener = clickListener;
        button.addEventListener('click', clickListener);
    }

    /**
     * Find the original element for a live-updated element
     * @param {HTMLElement} element - The element to find the original for
     * @param {HTMLElement} container - The container element
     * @returns {HTMLElement|null} - The original element or null if not found
     * @private
     */
    static findOriginalElement(element, container) {
        const linkedId =
            (element.parentElement &&
                element.parentElement.dataset &&
                element.parentElement.dataset.linkedOriginal) ||
            (container && container.dataset && container.dataset.linkedOriginal) ||
            (element.parentElement && element.parentElement.getAttribute('data-linked-original')) ||
            (container && container.getAttribute('data-linked-original'));

        if (linkedId) {
            const originalElement = document.querySelector(
                `.highlightit-original[data-highlightit-id="${linkedId}"]`
            );
            if (originalElement) {
                return originalElement;
            }
        }

        const originalId =
            (element.parentElement && element.parentElement.getAttribute('data-original-id')) ||
            (container && container.getAttribute('data-original-id'));

        if (originalId) {
            const idElement = document.getElementById(originalId);
            if (idElement) {
                return idElement;
            }
        }

        if (
            container &&
            container.previousSibling &&
            container.previousSibling.classList &&
            container.previousSibling.classList.contains('highlightit-original')
        ) {
            return container.previousSibling;
        }

        return null;
    }

    /**
     * Initialize the share functionality
     */
    static initSharing() {
        setTimeout(() => {
            this.scrollToAnchor();
        }, 100);

        window.addEventListener('hashchange', () => {
            this.scrollToAnchor();
        });
    }

    /**
     * Get file extension from language name
     * @param {string} language - The language to convert to file extension
     * @returns {string} - The file extension for the language
     * @private
     */
    static getLanguageFileExtension(language) {
        if (!language) return 'txt';

        for (const [ext, lang] of cache.extensionMap.entries()) {
            if (lang === language.toLowerCase()) {
                return ext;
            }
        }

        return language.toLowerCase();
    }
}

if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => HighlightIt.initSharing());
    } else {
        HighlightIt.initSharing();
    }
}

export default HighlightIt;

/**
 * Highlight a new element that wasn't present when the library was initialized
 * @param {HTMLElement} element - The element to highlight
 * @param {Object} options - Configuration options
 * @param {boolean} [options.autoDetect=true] - Whether to auto-detect language if not specified
 * @param {boolean} [options.addCopyButton=true] - Whether to add a copy button
 * @param {boolean} [options.showLanguage=true] - Whether to show the language label
 * @param {boolean} [options.addHeader=true] - Whether to add a header section
 * @param {boolean} [options.addLines=false] - Whether to add line numbers
 * @param {boolean} [options.withReload=false] - Whether to enable live updates
 * @param {boolean} [options.addShare=false] - Whether to add a share button
 * @param {boolean} [options.addDownload=false] - Whether to add a download button
 * @param {string} [options.filename] - The filename to use for the download button
 * @param {string} [options.language] - The language to use for syntax highlighting
 * @param {string} [options.theme] - Theme override for this element ('light', 'dark', or 'auto')
 * @param {number} [options.lineStart] - Starting line number (default is 1, can be positive or negative)
 * @returns {HTMLElement} - The highlighted element container
 */
HighlightIt.highlight = function (element, options = {}) {
    if (
        !element ||
        element.classList.contains('highlightit-original') ||
        element.closest('.highlightit-container') ||
        (element.parentElement && element.parentElement.classList.contains('highlightit-container'))
    ) {
        console.warn('HighlightIt: Element is already highlighted or is a hidden original element');
        return element;
    }

    const {
        autoDetect = true,
        addCopyButton = true,
        showLanguage = true,
        addHeader = true,
        addLines = false,
        withReload = false,
        addShare = false,
        addDownload = false,
        filename,
        language,
        theme,
        lineStart,
    } = options;

    if (addLines) {
        element.dataset.withLines = '';
    }

    if (lineStart !== undefined) {
        element.dataset.lineStart = lineStart;
    }

    if (withReload) {
        element.dataset.withReload = '';
    }

    if (!addHeader) {
        element.dataset.noHeader = '';
    }

    if (!addCopyButton) {
        element.dataset.noCopy = '';
    }

    if (addShare) {
        element.dataset.withShare = '';
    }

    if (addDownload) {
        element.dataset.withDownload = '';
    }

    if (filename) {
        element.dataset.filename = filename;
    }

    if (language) {
        element.dataset.language = language;
    }

    if (theme) {
        element.dataset.theme = theme;
    }

    this.processElement(
        element,
        autoDetect,
        addCopyButton,
        showLanguage,
        addHeader,
        addLines,
        addShare,
        addDownload
    );

    const container =
        element.closest('.highlightit-container') ||
        (element.parentElement && element.parentElement.closest('.highlightit-container'));

    return container || element;
};
