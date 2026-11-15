/**
 * Polyfills and browser compatibility helpers
 */

const polyfills = {
    supports: {
        requestAnimationFrame: typeof requestAnimationFrame === 'function',
        ResizeObserver: typeof ResizeObserver === 'function',
        MutationObserver: typeof MutationObserver === 'function',
        classList:
            'classList' in document.documentElement &&
            typeof document.documentElement.classList !== 'undefined',
        dataset:
            'dataset' in document.documentElement &&
            typeof document.documentElement.dataset !== 'undefined',
        clipboard: 'clipboard' in navigator,
        clipboardItem: typeof ClipboardItem !== 'undefined',
        touch:
            'ontouchstart' in window ||
            navigator.maxTouchPoints > 0 ||
            navigator.msMaxTouchPoints > 0,
        getBoundingClientRect: 'getBoundingClientRect' in document.documentElement,
        animation: 'Animation' in window && 'animate' in document.documentElement,
        cssHas: (function () {
            try {
                document.querySelector(':has(*)');
                return true;
            } catch {
                return false;
            }
        })(),
        download: typeof document.createElement('a').download !== 'undefined',
        blob: typeof Blob !== 'undefined',
        URL: typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function',
        TextEncoder: typeof TextEncoder !== 'undefined',
        crypto: typeof crypto !== 'undefined' && typeof crypto.subtle !== 'undefined',
        BigInt: typeof BigInt !== 'undefined',
        padStart: typeof String.prototype.padStart === 'function',
    },

    initStringPadding: function () {
        if (!this.supports.padStart) {
            String.prototype.padStart = function padStart(targetLength, padString) {
                targetLength = targetLength >> 0;
                padString = String(typeof padString !== 'undefined' ? padString : ' ');
                if (this.length >= targetLength) {
                    return String(this);
                } else {
                    targetLength = targetLength - this.length;
                    if (targetLength > padString.length) {
                        padString += padString.repeat(targetLength / padString.length);
                    }
                    return padString.slice(0, targetLength) + String(this);
                }
            };
        }
    },

    objectEntries: function (obj) {
        if (typeof Object.entries === 'function') {
            return Object.entries(obj);
        }

        const entries = [];
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                entries.push([key, obj[key]]);
            }
        }
        return entries;
    },

    init: function () {
        this.initStringPadding();
    },

    requestAnimationFrame: (function () {
        return (
            window.requestAnimationFrame ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame ||
            window.oRequestAnimationFrame ||
            window.msRequestAnimationFrame ||
            function (callback) {
                return window.setTimeout(callback, 1000 / 60);
            }
        );
    })(),

    TextEncoder: (function () {
        if (typeof TextEncoder !== 'undefined') return TextEncoder;

        return class TextEncoder {
            constructor() {
                this.encoding = 'utf-8';
            }

            encode(str) {
                if (str === null || str === undefined) return new Uint8Array();

                const string = String(str);
                let resPos = -1;

                const len = string.length;
                let byteSize = 0;

                for (let i = 0; i < len; i++) {
                    const code = string.charCodeAt(i);

                    if (code < 0x80) {
                        byteSize += 1;
                    } else if (code < 0x800) {
                        byteSize += 2;
                    } else if (code < 0xd800 || code >= 0xe000) {
                        byteSize += 3;
                    } else {
                        i++;
                        byteSize += 4;
                    }
                }

                const buffer = new Uint8Array(byteSize);

                for (let i = 0; i < len; i++) {
                    let codePoint = string.charCodeAt(i);

                    if (codePoint >= 0xd800 && codePoint < 0xe000) {
                        if (++i >= len) {
                            break;
                        }
                        const second = string.charCodeAt(i);
                        if (second >= 0xdc00 && second < 0xe000) {
                            codePoint = 0x10000 + ((codePoint - 0xd800) << 10) + (second - 0xdc00);
                        } else {
                            i--;
                        }
                    }

                    if (codePoint < 0x80) {
                        buffer[++resPos] = codePoint;
                    } else if (codePoint < 0x800) {
                        buffer[++resPos] = 0xc0 | (codePoint >> 6);
                        buffer[++resPos] = 0x80 | (codePoint & 0x3f);
                    } else if (codePoint < 0x10000) {
                        buffer[++resPos] = 0xe0 | (codePoint >> 12);
                        buffer[++resPos] = 0x80 | ((codePoint >> 6) & 0x3f);
                        buffer[++resPos] = 0x80 | (codePoint & 0x3f);
                    } else {
                        buffer[++resPos] = 0xf0 | (codePoint >> 18);
                        buffer[++resPos] = 0x80 | ((codePoint >> 12) & 0x3f);
                        buffer[++resPos] = 0x80 | ((codePoint >> 6) & 0x3f);
                        buffer[++resPos] = 0x80 | (codePoint & 0x3f);
                    }
                }

                return buffer;
            }
        };
    })(),

    simpleHash: function (str) {
        if (!str) return 'h-000000000000';

        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = (hash << 5) - hash + char;
            hash = hash & hash;
        }

        const hashStr = Math.abs(hash).toString(16).padStart(12, '0');
        return 'h-' + hashStr.substring(0, 12);
    },

    BigIntPolyfill: (function () {
        if (typeof BigInt !== 'undefined') return null;

        return class BigIntSimulation {
            constructor(value) {
                this.value = String(value);
            }

            static from(value) {
                return new BigIntSimulation(value);
            }

            divide(other) {
                let otherVal = typeof other === 'object' ? parseInt(other.value) : parseInt(other);
                let val = parseInt(this.value);
                let result = Math.floor(val / otherVal);
                return new BigIntSimulation(result);
            }

            modulo(other) {
                let otherVal = typeof other === 'object' ? parseInt(other.value) : parseInt(other);
                let val = parseInt(this.value);
                let result = val % otherVal;
                return result;
            }

            shiftLeft(bits) {
                let val = parseInt(this.value);
                let result = val << bits;
                return new BigIntSimulation(result);
            }

            or(other) {
                let otherVal = typeof other === 'object' ? parseInt(other.value) : parseInt(other);
                let val = parseInt(this.value);
                let result = val | otherVal;
                return new BigIntSimulation(result);
            }

            toString() {
                return this.value;
            }

            valueOf() {
                return parseInt(this.value);
            }
        };
    })(),

    /**
     * MutationObserver polyfill for older browsers
     * This is a simplified version that only supports the options needed by HighlightIt
     */
    MutationObserver: (function () {
        if (typeof MutationObserver !== 'undefined') return MutationObserver;

        return class MutationObserverPolyfill {
            constructor(callback) {
                this.callback = callback;
                this.observed = new Map();
                this.timeout = null;
                this.pollInterval = 100;
            }

            observe(target, options) {
                if (!target || !options) return;

                const snapshot = {
                    element: target,
                    options: options,
                    attributes: this._getAttributes(target),
                    characterData: options.characterData ? target.textContent : null,
                    childList: options.childList ? this._getChildList(target) : null,
                };

                this.observed.set(target, snapshot);

                if (!this.timeout) {
                    this._startPolling();
                }
            }

            disconnect() {
                if (this.timeout) {
                    clearTimeout(this.timeout);
                    this.timeout = null;
                }
                this.observed.clear();
            }

            takeRecords() {
                return [];
            }

            _startPolling() {
                this.timeout = setTimeout(() => {
                    const mutations = [];

                    this.observed.forEach((snapshot, target) => {
                        if (!document.contains(target)) {
                            this.observed.delete(target);
                            return;
                        }

                        if (snapshot.options.attributes) {
                            const currentAttributes = this._getAttributes(target);
                            const oldAttributes = snapshot.attributes;

                            for (const entry of polyfills.objectEntries(oldAttributes)) {
                                const name = entry[0];
                                const value = entry[1];
                                if (
                                    !(name in currentAttributes) ||
                                    currentAttributes[name] !== value
                                ) {
                                    mutations.push({
                                        type: 'attributes',
                                        target: target,
                                        attributeName: name,
                                        oldValue: snapshot.options.attributeOldValue ? value : null,
                                    });
                                }
                            }

                            for (const name in currentAttributes) {
                                if (!(name in oldAttributes)) {
                                    mutations.push({
                                        type: 'attributes',
                                        target: target,
                                        attributeName: name,
                                        oldValue: null,
                                    });
                                }
                            }

                            snapshot.attributes = currentAttributes;
                        }

                        if (snapshot.options.characterData) {
                            const currentText = target.textContent;
                            if (currentText !== snapshot.characterData) {
                                mutations.push({
                                    type: 'characterData',
                                    target: target,
                                    oldValue: snapshot.options.characterDataOldValue
                                        ? snapshot.characterData
                                        : null,
                                });
                                snapshot.characterData = currentText;
                            }
                        }

                        if (snapshot.options.childList) {
                            const currentChildren = this._getChildList(target);
                            const oldChildren = snapshot.childList;

                            if (currentChildren.length !== oldChildren.length) {
                                mutations.push({
                                    type: 'childList',
                                    target: target,
                                    addedNodes: [],
                                    removedNodes: [],
                                });
                            }

                            snapshot.childList = currentChildren;
                        }
                    });

                    if (mutations.length > 0) {
                        this.callback(mutations);
                    }

                    if (this.observed.size > 0) {
                        this._startPolling();
                    } else {
                        this.timeout = null;
                    }
                }, this.pollInterval);
            }

            _getAttributes(element) {
                const result = {};
                const attributes = element.attributes;
                if (attributes) {
                    for (let i = 0; i < attributes.length; i++) {
                        const attr = attributes[i];
                        result[attr.name] = attr.value;
                    }
                }
                return result;
            }

            _getChildList(element) {
                return Array.from(element.childNodes);
            }
        };
    })(),

    ResizeObserver: (function () {
        if (typeof ResizeObserver === 'function') return ResizeObserver;

        return class ResizeObserver {
            constructor(callback) {
                this.callback = callback;
                this.observedElements = new Set();
                this.observer = new MutationObserver(this.handleMutation.bind(this));
            }

            observe(element) {
                if (this.observedElements.has(element)) return;
                this.observedElements.add(element);
                this.observer.observe(element, {
                    attributes: true,
                    attributeFilter: ['style', 'class'],
                });
                this.checkSize(element);
            }

            unobserve(element) {
                this.observedElements.delete(element);
                this.observer.unobserve(element);
            }

            disconnect() {
                this.observer.disconnect();
                this.observedElements.clear();
            }

            handleMutation(mutations) {
                mutations.forEach((mutation) => {
                    if (mutation.target && this.observedElements.has(mutation.target)) {
                        this.checkSize(mutation.target);
                    }
                });
            }

            checkSize(element) {
                const size = {
                    width: element.offsetWidth,
                    height: element.offsetHeight,
                };
                this.callback([{ target: element, contentRect: size }]);
            }
        };
    })(),

    getBoundingClientRect: function (el) {
        if (!el) return { top: 0, right: 0, bottom: 0, left: 0, width: 0, height: 0 };

        if (this.supports.getBoundingClientRect) {
            try {
                return el.getBoundingClientRect();
            } catch {
                //
            }
        }

        const rect = {
            top: el.offsetTop,
            left: el.offsetLeft,
            width: el.offsetWidth,
            height: el.offsetHeight,
        };

        rect.right = rect.left + rect.width;
        rect.bottom = rect.top + rect.height;

        let parent = el.offsetParent;
        while (parent) {
            rect.top += parent.offsetTop;
            rect.left += parent.offsetLeft;
            parent = parent.offsetParent;
        }

        rect.top -= window.scrollY || document.documentElement.scrollTop || 0;
        rect.left -= window.scrollX || document.documentElement.scrollLeft || 0;

        return rect;
    },

    classList: {
        add: function (element, className) {
            if (!element) return;

            try {
                if (this.supports.classList) {
                    element.classList.add(className);
                } else {
                    const classes = (element.className || '').split(' ');
                    if (!classes.includes(className)) {
                        classes.push(className);
                    }
                    element.className = classes.join(' ');
                }
            } catch {
                const classes = (element.className || '').split(' ');
                if (!classes.includes(className)) {
                    classes.push(className);
                }
                element.className = classes.join(' ');
            }
        },
        remove: function (element, className) {
            if (!element) return;

            try {
                if (this.supports.classList) {
                    element.classList.remove(className);
                } else {
                    element.className = (element.className || '')
                        .split(' ')
                        .filter((c) => c !== className)
                        .join(' ');
                }
            } catch {
                element.className = (element.className || '')
                    .split(' ')
                    .filter((c) => c !== className)
                    .join(' ');
            }
        },
        contains: function (element, className) {
            if (!element) return false;

            try {
                if (this.supports.classList) {
                    return element.classList.contains(className);
                }
                return (element.className || '').split(' ').includes(className);
            } catch {
                return (element.className || '').split(' ').includes(className);
            }
        },
    },

    dataset: {
        get: function (element, key) {
            if (!element) return undefined;

            try {
                if (this.supports.dataset) {
                    return element.dataset[key];
                }
                return element.getAttribute(`data-${key}`);
            } catch {
                return element.getAttribute(`data-${key}`);
            }
        },
        set: function (element, key, value) {
            if (!element) return;

            try {
                if (this.supports.dataset) {
                    element.dataset[key] = value;
                } else {
                    element.setAttribute(`data-${key}`, value);
                }
            } catch {
                element.setAttribute(`data-${key}`, value);
            }
        },
    },

    copyToClipboard: async function (text) {
        if (this.supports.clipboard) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch {
                //
            }
        }

        if (this.supports.clipboard && this.supports.clipboardItem) {
            try {
                const clipboardItem = new ClipboardItem({
                    'text/plain': new Blob([text], { type: 'text/plain' }),
                });
                await navigator.clipboard.write([clipboardItem]);
                return true;
            } catch {
                //
            }
        }

        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            return success;
        } catch {
            document.body.removeChild(textArea);
            return false;
        }
    },

    downloadFile: function (filename, content, mimeType = 'text/plain') {
        if (this.supports.blob && this.supports.URL) {
            try {
                const blob = new Blob([content], { type: mimeType });
                const url = URL.createObjectURL(blob);

                if (this.supports.download) {
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();

                    setTimeout(() => {
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                    }, 100);

                    return true;
                } else {
                    window.open(url, '_blank');

                    setTimeout(() => {
                        URL.revokeObjectURL(url);
                    }, 100);

                    return true;
                }
            } catch (e) {
                console.error('Error downloading file:', e);
            }
        }

        try {
            const iframeId = 'highlightit-download-iframe';
            let iframe = document.getElementById(iframeId);

            if (!iframe) {
                iframe = document.createElement('iframe');
                iframe.id = iframeId;
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
            }

            const iframeDocument = iframe.contentWindow.document;
            iframeDocument.open('text/html', 'replace');
            iframeDocument.write(content);
            iframeDocument.close();

            iframeDocument.execCommand('SaveAs', true, filename);
            return true;
        } catch (e) {
            console.error('Legacy download failed:', e);
            return false;
        }
    },

    animate: function (element, keyframes, options) {
        if (!element) return null;

        if (this.supports.animation) {
            try {
                return element.animate(keyframes, options);
            } catch {
                //
            }
        }

        const animationId = Date.now().toString(36);
        const duration = options.duration || 1000;

        Object.keys(keyframes[0]).forEach((prop) => {
            element.style[prop] = keyframes[0][prop];
        });

        setTimeout(() => {
            element.style.transition = `all ${duration}ms ${options.easing || 'ease'}`;

            const finalState = keyframes[keyframes.length - 1];
            Object.keys(finalState).forEach((prop) => {
                element.style[prop] = finalState[prop];
            });

            setTimeout(() => {
                element.style.transition = '';
                if (options.fill !== 'forwards') {
                    Object.keys(finalState).forEach((prop) => {
                        element.style[prop] = '';
                    });
                }
            }, duration);
        }, 0);

        return {
            id: animationId,
            cancel: function () {
                element.style.transition = '';
            },
            finished: new Promise((resolve) => {
                setTimeout(resolve, duration);
            }),
        };
    },

    /**
     * Helper to check if a container has an element with a certain class
     * Used as a fallback for browsers that don't support :has() selector
     *
     * @param {HTMLElement} container - The container element to check
     * @param {string} selector - The selector to look for within the container
     * @param {string} className - The class to add/remove from the container
     * @param {boolean} shouldHaveClass - Whether to add or remove the class
     */
    updateHasClass: function (container, selector, className, shouldHaveClass) {
        if (!container || !selector || !className) return;
        if (this.supports.cssHas) return;

        const hasElement = container.querySelector(selector);

        if (shouldHaveClass && hasElement) {
            this.classList.add(container, className);
        } else if (!shouldHaveClass && !hasElement) {
            this.classList.remove(container, className);
        }
    },
};

export default polyfills;
