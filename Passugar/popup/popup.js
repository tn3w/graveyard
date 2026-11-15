document.addEventListener('DOMContentLoaded', function () {
	initializeTheme()

	const generateBtn = document.getElementById('generate-btn')
	const passwordDisplay = document.getElementById('password-display')
	const copyBtn = document.getElementById('copy-btn')
	const toggleSettingsBtn = document.getElementById('toggle-settings')
	const settingsContent = document.getElementById('settings-content')
	const usePassphraseCheckbox = document.getElementById('use-passphrase')
	const passwordOptions = document.getElementById('password-options')
	const passphraseOptions = document.getElementById('passphrase-options')
	const passwordLengthSlider = document.getElementById('password-length')
	const passwordLengthValue = document.getElementById('password-length-value')
	const passphraseLengthSlider = document.getElementById('passphrase-length')
	const passphraseLengthValue = document.getElementById('passphrase-length-value')
	const toggleVisibilityBtn = document.getElementById('toggle-visibility')

	const uppercaseCheckbox = document.getElementById('uppercase')
	const lowercaseCheckbox = document.getElementById('lowercase')
	const numbersCheckbox = document.getElementById('numbers')
	const specialCheckbox = document.getElementById('special')
	const extendedCheckbox = document.getElementById('extended')

	let settings = {
		usePassphrase: false,
		passwordLength: 32,
		passphraseLength: 7,
		uppercase: true,
		lowercase: true,
		numbers: true,
		special: true,
		extended: false
	}

	let actualPassword = ''
	let passwordVisible = true
	let visibilityTimeout = null

	function updatePasswordDisplay() {
		if (passwordVisible) {
			passwordDisplay.textContent = actualPassword
			document.body.removeAttribute('data-password-hidden')
		} else {
			passwordDisplay.textContent = actualPassword ? '•'.repeat(actualPassword.length) : ''
			document.body.setAttribute('data-password-hidden', 'true')
		}
	}

	async function loadSettings() {
		try {
			const result = await browser.storage.local.get('passwordSettings')
			if (result.passwordSettings) {
				settings = { ...settings, ...result.passwordSettings }

				usePassphraseCheckbox.checked = settings.usePassphrase
				passwordLengthSlider.value = settings.passwordLength
				passwordLengthValue.textContent = settings.passwordLength
				passphraseLengthSlider.value = settings.passphraseLength
				passphraseLengthValue.textContent = settings.passphraseLength
				uppercaseCheckbox.checked = settings.uppercase
				lowercaseCheckbox.checked = settings.lowercase
				numbersCheckbox.checked = settings.numbers
				specialCheckbox.checked = settings.special
				extendedCheckbox.checked = settings.extended

				togglePassphraseOptions(settings.usePassphrase)
			}
		} catch (error) {
			console.error('Error loading settings:', error)
		}
	}

	async function saveSettings() {
		try {
			await browser.storage.local.set({ passwordSettings: settings })
		} catch (error) {
			console.error('Error saving settings:', error)
		}
	}

	function toggleSettings() {
		toggleSettingsBtn.classList.toggle('expanded')

		if (!settingsContent.classList.contains('expanded')) {
			settingsContent.style.height = 'auto'
			const contentHeight = settingsContent.scrollHeight + 'px'
			settingsContent.style.height = '0'

			settingsContent.offsetHeight

			settingsContent.style.height = contentHeight
			settingsContent.classList.add('expanded')

			setTimeout(() => {
				settingsContent.style.height = 'auto'
			}, 300)
		} else {
			settingsContent.style.height = settingsContent.scrollHeight + 'px'

			settingsContent.offsetHeight

			settingsContent.style.height = '0'
			settingsContent.classList.remove('expanded')
		}
	}

	function togglePassphraseOptions(usePassphrase) {
		if (usePassphrase) {
			passwordOptions.classList.add('hidden')
			passphraseOptions.classList.remove('hidden')
		} else {
			passwordOptions.classList.remove('hidden')
			passphraseOptions.classList.add('hidden')
		}
	}

	function initializeTheme() {
		const htmlElement = document.documentElement
		const themeToggleBtn = document.getElementById('theme-toggle')

		browser.storage.local
			.get('theme')
			.then((result) => {
				if (result.theme) {
					htmlElement.setAttribute('data-theme', result.theme)
				} else {
					const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches
					const defaultTheme = isDarkMode ? 'dark' : 'light'

					htmlElement.setAttribute('data-theme', defaultTheme)
					browser.storage.local.set({ theme: defaultTheme })
				}
			})
			.catch((error) => {
				console.error('Error loading theme preference:', error)
			})

		if (themeToggleBtn) {
			themeToggleBtn.replaceWith(themeToggleBtn.cloneNode(true))

			const newThemeToggleBtn = document.getElementById('theme-toggle')

			newThemeToggleBtn.addEventListener('click', function (event) {
				event.preventDefault()
				event.stopPropagation()

				const currentTheme = htmlElement.getAttribute('data-theme')
				const newTheme = currentTheme === 'dark' ? 'light' : 'dark'

				console.log(`Changing theme from ${currentTheme} to ${newTheme}`)

				htmlElement.setAttribute('data-theme', newTheme)

				browser.storage.local
					.set({ theme: newTheme })
					.catch((error) => console.error('Error saving theme preference:', error))

				return false
			})
		} else {
			console.error('Theme toggle button not found in the DOM')
		}
	}

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
		if (settings.usePassphrase) {
			return generatePassphrase(settings.passphraseLength)
		}

		try {
			const options = {
				length: settings.passwordLength,
				uppercase: settings.uppercase,
				lowercase: settings.lowercase,
				numbers: settings.numbers,
				special: settings.special,
				extended: settings.extended
			}

			const response = await browser.runtime.sendMessage({
				action: 'generatePassword',
				options: options
			})

			return response.password
		} catch (error) {
			console.error('Error generating password:', error)
			return 'Error-generating-password'
		}
	}

	generateBtn.addEventListener('click', async function () {
		const password = await generatePassword()
		actualPassword = password
		updatePasswordDisplay()
		copyBtn.disabled = false
	})

	copyBtn.addEventListener('click', function () {
		navigator.clipboard.writeText(actualPassword).then(() => {
			copyBtn.textContent = 'Copied!'
			setTimeout(() => {
				copyBtn.textContent = 'Copy to Clipboard'
			}, 2000)
		})
	})

	toggleSettingsBtn.addEventListener('click', toggleSettings)

	usePassphraseCheckbox.addEventListener('change', function () {
		settings.usePassphrase = this.checked
		togglePassphraseOptions(this.checked)
		saveSettings()
	})

	passwordLengthSlider.addEventListener('input', function () {
		settings.passwordLength = parseInt(this.value)
		passwordLengthValue.textContent = this.value
		saveSettings()
	})

	passphraseLengthSlider.addEventListener('input', function () {
		settings.passphraseLength = parseInt(this.value)
		passphraseLengthValue.textContent = this.value
		saveSettings()
	})

	uppercaseCheckbox.addEventListener('change', function () {
		settings.uppercase = this.checked
		saveSettings()
	})

	lowercaseCheckbox.addEventListener('change', function () {
		settings.lowercase = this.checked
		saveSettings()
	})

	numbersCheckbox.addEventListener('change', function () {
		settings.numbers = this.checked
		saveSettings()
	})

	specialCheckbox.addEventListener('change', function () {
		settings.special = this.checked
		saveSettings()
	})

	extendedCheckbox.addEventListener('change', function () {
		settings.extended = this.checked
		saveSettings()
	})

	toggleVisibilityBtn.addEventListener('click', () => {
		passwordVisible = !passwordVisible
		updatePasswordDisplay()
	})

	passwordDisplay.addEventListener('dblclick', () => {
		if (visibilityTimeout) {
			clearTimeout(visibilityTimeout)
		}

		const wasVisible = passwordVisible
		passwordVisible = true
		updatePasswordDisplay()

		if (!wasVisible) {
			visibilityTimeout = setTimeout(() => {
				passwordVisible = false
				updatePasswordDisplay()
			}, 5000)
		}
	})

	loadSettings()
	initializeTheme()

	passwordVisible = true
})
