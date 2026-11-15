;(function () {
	'use strict'

	const processedFields = new Set()
	const overlays = new Map()
	const pairedFields = new Map()

	function applyThemeFromStorage() {
		browser.storage.local.get('theme').then((result) => {
			if (result.theme) {
				document.documentElement.setAttribute('data-theme', result.theme)
			} else {
				const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
				document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
			}
		})
	}

	browser.storage.onChanged.addListener((changes) => {
		if (changes.theme) {
			document.documentElement.setAttribute('data-theme', changes.theme.newValue)
		}
	})

	applyThemeFromStorage()

	function getRandomWord() {
		const words = [
			'apple',
			'banana',
			'orange',
			'grape',
			'kiwi',
			'lemon',
			'peach',
			'pear',
			'house',
			'table',
			'chair',
			'window',
			'door',
			'floor',
			'ceiling',
			'wall',
			'water',
			'fire',
			'earth',
			'wind',
			'light',
			'dark',
			'sun',
			'moon',
			'book',
			'page',
			'story',
			'novel',
			'author',
			'reader',
			'writer',
			'paper',
			'music',
			'song',
			'dance',
			'rhythm',
			'melody',
			'harmony',
			'tempo',
			'beat',
			'ocean',
			'river',
			'lake',
			'stream',
			'pond',
			'beach',
			'shore',
			'coast',
			'mountain',
			'valley',
			'hill',
			'cliff',
			'peak',
			'summit',
			'ridge',
			'slope',
			'forest',
			'tree',
			'flower',
			'grass',
			'plant',
			'garden',
			'park',
			'meadow',
			'animal',
			'bird',
			'fish',
			'insect',
			'mammal',
			'reptile',
			'snake',
			'tiger',
			'friend',
			'family',
			'parent',
			'child',
			'brother',
			'sister',
			'mother',
			'father'
		]

		return words[Math.floor(Math.random() * words.length)]
	}

	function getRandomSpecialChar() {
		const specialChars = '!@#$%^&*()-_=+[]{}|;:,.<>?/'
		return specialChars.charAt(Math.floor(Math.random() * specialChars.length))
	}

	function generatePassphrase(wordCount) {
		const words = []
		for (let i = 0; i < wordCount; i++) {
			const word = getRandomWord()
			words.push(Math.random() > 0.5 ? word.charAt(0).toUpperCase() + word.slice(1) : word)
		}

		const separator = getRandomSpecialChar()
		const passphrase = words.join(separator)
		const numbers = Math.floor(Math.random() * 900 + 100)

		return passphrase + numbers
	}

	async function generatePassword() {
		try {
			const result = await browser.storage.local.get('passwordSettings')
			const settings = result.passwordSettings || {
				usePassphrase: false,
				passwordLength: 32,
				passphraseLength: 7,
				uppercase: true,
				lowercase: true,
				numbers: true,
				special: true,
				extended: false
			}

			if (settings.usePassphrase) {
				return generatePassphrase(settings.passphraseLength)
			}

			const response = await browser.runtime.sendMessage({
				action: 'generatePassword',
				options: {
					length: settings.passwordLength,
					uppercase: settings.uppercase,
					lowercase: settings.lowercase,
					numbers: settings.numbers,
					special: settings.special,
					extended: settings.extended
				}
			})

			return response.password
		} catch (error) {
			console.error('Error generating password:', error)
			return 'Error-generating-password'
		}
	}

	function addPasswordToggleFeature(passwordField) {
		passwordField.addEventListener('dblclick', function () {
			this.type = this.type === 'password' ? 'text' : 'password'

			const pairedField = pairedFields.get(this)
			if (pairedField) {
				pairedField.type = this.type
			}
		})
	}

	function createOverlay(passwordField) {
		const overlay = document.createElement('div')
		overlay.className = 'passugar-overlay'

		const branding = document.createElement('div')
		branding.className = 'passugar-branding'

		const iconContainer = document.createElement('div')
		iconContainer.className = 'passugar-icon'

		const iconImg = document.createElement('img')
		iconImg.src = browser.runtime.getURL('icons/passugar-19.png')
		iconImg.alt = 'Passugar'
		iconImg.width = 10
		iconImg.height = 10

		iconContainer.appendChild(iconImg)

		const brandText = document.createElement('span')
		brandText.textContent = 'Passugar'

		branding.appendChild(iconContainer)
		branding.appendChild(brandText)

		const title = document.createElement('div')
		title.className = 'passugar-title'
		title.textContent = 'Use strong password'

		const description = document.createElement('div')
		description.className = 'passugar-description'
		description.textContent = 'Generate a secure, unique password'

		overlay.appendChild(branding)
		overlay.appendChild(title)
		overlay.appendChild(description)

		const rect = passwordField.getBoundingClientRect()
		overlay.style.top = `${rect.bottom + window.scrollY + 5}px`
		overlay.style.left = `${rect.left + window.scrollX}px`

		const fillPassword = async () => {
			const password = await generatePassword()

			passwordField.value = password

			const event = new Event('input', { bubbles: true })
			passwordField.dispatchEvent(event)

			const pairedField = pairedFields.get(passwordField)
			if (pairedField) {
				pairedField.value = password
				pairedField.dispatchEvent(new Event('input', { bubbles: true }))
			} else {
				const form = passwordField.form
				if (form) {
					const inputs = Array.from(form.querySelectorAll('input[type="password"]'))
					const confirmField = inputs.find(
						(input) =>
							input !== passwordField &&
							(input.name.toLowerCase().includes('confirm') ||
								input.id.toLowerCase().includes('confirm') ||
								input.placeholder.toLowerCase().includes('confirm') ||
								input.getAttribute('aria-label')?.toLowerCase().includes('confirm'))
					)

					if (confirmField) {
						confirmField.value = password
						confirmField.dispatchEvent(new Event('input', { bubbles: true }))
						pairedFields.set(passwordField, confirmField)
						pairedFields.set(confirmField, passwordField)
					}
				}
			}

			document.body.removeChild(overlay)
			overlays.delete(passwordField)
		}

		overlay.addEventListener('click', fillPassword)

		document.body.appendChild(overlay)
		overlays.set(passwordField, overlay)
	}

	function detectPasswordFieldType(passwordField) {
		const fieldName = (passwordField.name || '').toLowerCase()
		const fieldId = (passwordField.id || '').toLowerCase()
		const fieldPlaceholder = (passwordField.placeholder || '').toLowerCase()
		const fieldLabel = (passwordField.getAttribute('aria-label') || '').toLowerCase()

		if (
			fieldName.includes('confirm') ||
			fieldName.includes('verify') ||
			fieldId.includes('confirm') ||
			fieldId.includes('verify') ||
			fieldPlaceholder.includes('confirm') ||
			fieldPlaceholder.includes('verify') ||
			fieldLabel.includes('confirm') ||
			fieldLabel.includes('verify') ||
			fieldName === 'password2' ||
			fieldId === 'password2'
		) {
			return 'confirm'
		}

		if (
			fieldName.includes('new') ||
			fieldId.includes('new') ||
			fieldPlaceholder.includes('new') ||
			fieldLabel.includes('new') ||
			fieldName === 'password1' ||
			fieldId === 'password1' ||
			fieldName === 'password' ||
			fieldId === 'password'
		) {
			return 'new'
		}

		return ''
	}

	function findPairedPasswordField(passwordField) {
		if (!passwordField.form) return

		const fieldType = detectPasswordFieldType(passwordField)
		if (!fieldType) return

		const otherType = fieldType === 'new' ? 'confirm' : 'new'
		const inputs = Array.from(passwordField.form.querySelectorAll('input[type="password"]'))

		for (const input of inputs) {
			if (input === passwordField) continue

			const inputType = detectPasswordFieldType(input)
			if (inputType === otherType) {
				pairedFields.set(passwordField, input)
				pairedFields.set(input, passwordField)
				break
			}
		}
	}

	function processPasswordField(passwordField) {
		if (processedFields.has(passwordField)) {
			return
		}

		processedFields.add(passwordField)
		addPasswordToggleFeature(passwordField)

		const fieldType = detectPasswordFieldType(passwordField)

		const pairedField = findPairedPasswordField(passwordField)
		if (pairedField) {
			pairedFields.set(passwordField, pairedField)
			pairedFields.set(pairedField, passwordField)
		}

		const showOverlayOnFocus = () => {
			if (passwordField.value === '') {
				if (fieldType !== 'confirm') {
					createOverlay(passwordField)
				}
			}
		}

		passwordField.addEventListener('focus', showOverlayOnFocus)
	}

	function observeDOMForPasswordFields() {
		document.querySelectorAll('input[type="password"]').forEach(processPasswordField)

		const observer = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				if (mutation.addedNodes) {
					mutation.addedNodes.forEach((node) => {
						if (node.tagName === 'INPUT' && node.type === 'password') {
							processPasswordField(node)
						}

						if (node.querySelectorAll) {
							node.querySelectorAll('input[type="password"]').forEach(
								processPasswordField
							)
						}
					})
				}
			}
		})

		observer.observe(document.body, {
			childList: true,
			subtree: true
		})
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', observeDOMForPasswordFields)
	} else {
		observeDOMForPasswordFields()
	}
})()
