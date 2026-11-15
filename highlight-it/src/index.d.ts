/**
 * HighlightIt - A lightweight syntax highlighting library with themes, line numbers, and copy functionality.
 * Uses highlight.js for code highlighting
 */

/**
 * Configuration options for HighlightIt
 */
export interface HighlightItOptions {
	/**
	 * CSS selector for elements to highlight
	 * @default '.highlight-it'
	 */
	selector?: string

	/**
	 * Whether to auto-detect language if not specified
	 * @default true
	 */
	autoDetect?: boolean

	/**
	 * Whether to add a copy button to code blocks
	 * @default true
	 */
	addCopyButton?: boolean

	/**
	 * Whether to show the language label
	 * @default true
	 */
	showLanguage?: boolean

	/**
	 * Whether to add header section
	 * @default true
	 */
	addHeader?: boolean

	/**
	 * Whether to add line numbers
	 * @default false
	 */
	addLines?: boolean

	/**
	 * Whether to add share button to code blocks
	 * @default false
	 */
	addShare?: boolean

	/**
	 * Whether to add download button to code blocks
	 * @default false
	 */
	addDownload?: boolean

	/**
	 * Theme to use ('light', 'dark', or 'auto')
	 * @default 'auto'
	 */
	theme?: 'light' | 'dark' | 'auto'

	/**
	 * Debounce time in ms for live updates (lower values = more responsive)
	 * @default 50
	 */
	debounceTime?: number
}

/**
 * Options for highlighting a single element
 */
export interface HighlightElementOptions {
	/**
	 * Whether to auto-detect language if not specified
	 * @default true
	 */
	autoDetect?: boolean

	/**
	 * Whether to add a copy button to code blocks
	 * @default true
	 */
	addCopyButton?: boolean

	/**
	 * Whether to show the language label
	 * @default true
	 */
	showLanguage?: boolean

	/**
	 * Whether to add header section
	 * @default true
	 */
	addHeader?: boolean

	/**
	 * Whether to add line numbers
	 * @default false
	 */
	addLines?: boolean

	/**
	 * Whether to enable live updates
	 * @default false
	 */
	withReload?: boolean

	/**
	 * Whether to add share button
	 * @default false
	 */
	addShare?: boolean

	/**
	 * Whether to add download button
	 * @default false
	 */
	addDownload?: boolean

	/**
	 * Filename to use for the download button and language detection
	 */
	filename?: string

	/**
	 * The language to use for syntax highlighting
	 */
	language?: string

	/**
	 * Theme override for this element ('light', 'dark', or 'auto')
	 */
	theme?: 'light' | 'dark' | 'auto'

	/**
	 * Starting line number for line numbering
	 * @default 1
	 */
	lineStart?: number
}

/**
 * HighlightIt class for syntax highlighting
 */
declare class HighlightIt {
	/**
	 * Whether the instance has been initialized
	 * @internal
	 */
	private static _initialized: boolean

	/**
	 * Debounce time for live updates in milliseconds
	 * @internal
	 */
	private static debounceTime: number

	/**
	 * Whether the device is a touch device
	 * @internal
	 */
	private static isTouchDevice: boolean

	/**
	 * Initialize HighlightIt by finding and highlighting all matching elements
	 * @param options - Configuration options
	 */
	static init(options?: HighlightItOptions): void

	/**
	 * Highlight a new element that wasn't present when the library was initialized
	 * @param element - The element to highlight
	 * @param options - Configuration options
	 * @returns The highlighted element container
	 */
	static highlight(element: HTMLElement, options?: HighlightElementOptions): HTMLElement

	/**
	 * Generate a hash using SHA-256 and convert to a 12-character base62 string
	 * @param input - The string to hash
	 * @returns A 12-character base62 hash
	 */
	static generateHash(input: string): Promise<string>

	/**
	 * Create a share button for code blocks
	 * @param code - The code to generate hash from if no id exists
	 * @param container - The container element (to extract id)
	 * @returns The share button element
	 *
	 * The ID priority is:
	 * 1. data-original-id attribute on container
	 * 2. Existing container.id
	 * 3. Generated hash from code content
	 */
	static createShareButton(code: string, container: HTMLElement): Promise<HTMLElement>

	/**
	 * Update block ID when code changes for blocks with live updates
	 * @param container - The container element
	 * @param newCode - The new code content
	 * @returns The updated block ID
	 *
	 * The ID priority is:
	 * 1. data-original-id attribute
	 * 2. Existing container.id
	 * 3. Generated hash from newCode
	 *
	 * Note: When using data-with-reload, the original ID is preserved
	 * on the hidden element, and the visible element uses data-original-id
	 * to reference it without duplicating the ID attribute.
	 */
	static updateBlockId(container: HTMLElement, newCode: string): Promise<string>

	/**
	 * Scroll to the element specified in the URL hash
	 * @param attempts - Number of attempts made so far
	 */
	static scrollToAnchor(attempts?: number): void

	/**
	 * Scroll to a highlighted element and optionally to a specific line
	 * @param element - The element to scroll to
	 * @param lineNumber - The line number to highlight, if any
	 * @private
	 */
	private static scrollToHighlightedElement(element: HTMLElement, lineNumber: number | null): void

	/**
	 * Create a full-width highlight that spans both line numbers and code
	 * @param lineContainer - The line container element
	 * @param codeContainer - The code container element
	 * @private
	 */
	private static createFullWidthHighlight(
		lineContainer: HTMLElement,
		codeContainer: HTMLElement
	): void

	/**
	 * Process an element for highlighting, handling both single and nested element structures
	 * @param element - The element to process
	 * @param autoDetect - Whether to auto-detect language
	 * @param addCopyButton - Whether to add a copy button
	 * @param showLanguage - Whether to show the language label
	 * @param addHeader - Whether to add header section
	 * @param addLines - Whether to add line numbers
	 * @param addShare - Whether to add share button
	 * @param addDownload - Whether to add download button
	 * @private
	 */
	private static processElement(
		element: HTMLElement,
		autoDetect: boolean,
		addCopyButton: boolean,
		showLanguage: boolean,
		addHeader: boolean,
		addLines: boolean,
		addShare: boolean,
		addDownload: boolean
	): void

	/**
	 * Initialize sharing functionality
	 */
	static initSharing(): void

	/**
	 * Apply global theme to the document root
	 * @param theme - Theme to apply ('light', 'dark', or 'auto')
	 * @private
	 */
	private static applyGlobalTheme(theme: string): void

	/**
	 * Highlight a single element
	 * @param element - The code element to highlight
	 * @param autoDetect - Whether to auto-detect language
	 * @param addCopyButton - Whether to add a copy button
	 * @param showLanguage - Whether to show the language label
	 * @param addHeader - Whether to add header section
	 * @param addLines - Whether to add line numbers
	 * @param addShare - Whether to add share button
	 * @param addDownload - Whether to add download button
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
	private static highlightElement(
		element: HTMLElement,
		autoDetect: boolean,
		addCopyButton: boolean,
		showLanguage: boolean,
		addHeader: boolean,
		addLines: boolean,
		addShare: boolean,
		addDownload: boolean
	): void

	/**
	 * Set up live updates to watch for changes to the code element
	 * @param element - The code element to watch
	 * @param container - The container element
	 * @param autoDetect - Whether to auto-detect language
	 * @param showLanguage - Whether to show the language label
	 * @param withShare - Whether to update block ID for sharing
	 * @private
	 */
	private static setupLiveUpdates(
		element: HTMLElement,
		container: HTMLElement,
		autoDetect: boolean,
		showLanguage: boolean,
		withShare: boolean
	): void

	/**
	 * Intelligently update line numbers for live updates, preserving existing DOM elements
	 * @param lineNumbersWrapper - The line numbers wrapper element
	 * @param newLineCount - The new line count
	 * @param oldLineCount - The old line count
	 * @param startLine - The starting line number
	 * @param withShare - Whether share buttons should be included
	 * @param blockId - The block ID for share links
	 * @param container - The container element
	 */
	static updateLineNumbersForLiveUpdates(
		lineNumbersWrapper: HTMLElement,
		newLineCount: number,
		oldLineCount: number,
		startLine: number,
		withShare: boolean,
		blockId: string,
		container: HTMLElement
	): void

	/**
	 * Create a styled container for code block
	 * @param element - The code element to wrap
	 * @returns The container element
	 * @private
	 */
	private static createCodeContainer(element: HTMLElement): HTMLElement

	/**
	 * Create code header with language/filename label and copy button
	 * @param displayLabel - The text to display (language or filename)
	 * @param code - The code to copy
	 * @param addCopyButton - Whether to add a copy button
	 * @param showLanguage - Whether to show the language label
	 * @param addShareButton - Whether to add a share button
	 * @param addDownloadButton - Whether to add a download button
	 * @param container - The container element (for share button)
	 * @returns The header element
	 * @private
	 */
	private static createCodeHeader(
		displayLabel: string | null,
		code: string,
		addCopyButton: boolean,
		showLanguage: boolean,
		addShareButton: boolean,
		addDownloadButton: boolean,
		container: HTMLElement
	): HTMLElement

	/**
	 * Create copy button element
	 * @param code - The code to copy
	 * @returns The copy button element
	 * @private
	 */
	private static createCopyButton(code: string): HTMLElement

	/**
	 * Create download button element
	 * @param code - The code to download
	 * @param language - The language of the code (for filename extension)
	 * @param container - The container element (for filename attribute)
	 * @returns The download button element
	 * @private
	 */
	private static createDownloadButton(
		code: string,
		language: string | null,
		container: HTMLElement
	): HTMLElement

	/**
	 * Create floating buttons for no-header mode
	 * @param code - The code to copy
	 * @param withShare - Whether to add a share button
	 * @param withDownload - Whether to add a download button
	 * @param container - The container element for share functionality
	 * @returns The floating buttons container
	 * @private
	 */
	private static createFloatingButtons(
		code: string,
		withShare?: boolean,
		withDownload?: boolean,
		container?: HTMLElement | null
	): HTMLElement

	/**
	 * Get language from filename extension
	 * @param filename - The filename to extract extension from
	 * @returns The language name or null if not determined
	 * @private
	 */
	private static getLanguageFromFilename(filename: string): string | null

	/**
	 * Auto-detect language with priority given to popular languages
	 * @param code - The code to detect the language of
	 * @returns The highlight.js result object with language and value properties
	 * @private
	 */
	private static autoDetectLanguage(code: string): { language: string; value: string }

	/**
	 * Escape HTML special characters
	 * @param html - The HTML string to escape
	 * @returns The escaped HTML string
	 * @private
	 */
	private static escapeHtml(html: string): string

	/**
	 * Add line numbers to a code element
	 * @param element - The code element to add line numbers to
	 * @param code - The original code content
	 * @private
	 */
	private static addLineNumbers(element: HTMLElement, code: string): void

	/**
	 * Updates a code block with new content
	 * @param element The code element to update
	 * @param container The container element
	 * @param languageOrFilename The language or filename to use for highlighting
	 * @param code The code to highlight
	 * @param showLanguage Whether to show the language in the header
	 *
	 * @remarks
	 * This method maintains proper ID handling to ensure consistency across re-highlighting:
	 * 1. Line share buttons use the current ID (from data-original-id or container.id) at click time
	 * 2. Share buttons prioritize IDs in the following order:
	 *    - data-original-id attribute on the container
	 *    - Existing container.id
	 *    - Generated hash from code content
	 */
	static updateCodeBlock(
		element: HTMLElement,
		container: HTMLElement,
		languageOrFilename: string | null,
		code: string,
		showLanguage: boolean
	): void

	/**
	 * Setup a click handler for line share buttons
	 * @param button The line share button element
	 * @param container The container element
	 *
	 * @remarks
	 * This method extracts the common click handler logic for line share buttons
	 * to avoid duplicating code and allow updating just the handler when needed.
	 * The handler is stored on the button element as _clickListener to allow
	 * removal and replacement when the container ID changes.
	 */
	static setupLineShareButtonHandler(button: HTMLElement, container: HTMLElement): void

	/**
	 * Find the original element for live updates
	 * @param element - The code element
	 * @param container - The container element
	 * @returns The original element or null if not found
	 * @private
	 */
	private static findOriginalElement(
		element: HTMLElement,
		container: HTMLElement | null
	): HTMLElement | null

	/**
	 * Get file extension from language name
	 * @param language - The language to convert to file extension
	 * @returns The file extension for the language
	 * @private
	 */
	private static getLanguageFileExtension(language: string): string
}

export default HighlightIt

declare global {
	interface Window {
		HighlightIt: typeof HighlightIt
	}

	interface HTMLElement {
		/**
		 * Stored ResizeObserver for line numbers
		 * @internal
		 */
		_lineNumbersResizeObserver?: ResizeObserver

		/**
		 * Highlight.js observer for the element
		 * @internal
		 */
		_highlightObserver?: MutationObserver
	}

	interface HTMLButtonElement {
		/**
		 * Stored code content for copy buttons
		 * @internal
		 */
		_currentCode?: string

		/**
		 * Stored code content for download buttons
		 * @internal
		 */
		_code?: string

		/**
		 * Stored block ID for share buttons
		 * @internal
		 */
		_currentBlockId?: string

		/**
		 * Stored click listener for line share buttons
		 * @internal
		 */
		_clickListener?: (this: GlobalEventHandlers, ev: MouseEvent) => void

		/**
		 * Backup of the click handler
		 * @internal
		 */
		onclickBackup?: (this: GlobalEventHandlers, ev: MouseEvent) => Promise<void>
	}
}
