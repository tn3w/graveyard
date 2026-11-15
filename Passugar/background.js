browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
	if (message.action === 'generatePassword') {
		const options = message.options || {}
		const password = generateStrongPassword(
			options.length || 32,
			options.uppercase !== false,
			options.lowercase !== false,
			options.numbers !== false,
			options.special !== false,
			options.extended || false
		)

		sendResponse({ password })
	}
	return true
})

function generateStrongPassword(
	length = 32,
	useUppercase = true,
	useLowercase = true,
	useNumbers = true,
	useSpecial = true,
	useExtended = false
) {
	const uppercaseChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	const lowercaseChars = 'abcdefghijklmnopqrstuvwxyz'
	const numberChars = '0123456789'
	const specialChars = '!@#$%^&*()-_=+[]{}|;:,.<>?/'
	const extendedChars = '£€¥¢§©®™°¿¡«»≤≥±×÷¬µΩπ∞∫∑√≈≠'

	let charPool = ''
	if (useUppercase) charPool += uppercaseChars
	if (useLowercase) charPool += lowercaseChars
	if (useNumbers) charPool += numberChars
	if (useSpecial) charPool += specialChars
	if (useExtended) charPool += extendedChars

	if (charPool.length === 0) {
		charPool = lowercaseChars + numberChars
	}

	let password = ''
	for (let i = 0; i < length; i++) {
		password += getRandomChar(charPool)
	}

	let finalPassword = password

	if (useUppercase || useLowercase || useNumbers || useSpecial || useExtended) {
		const requiredChars = []

		if (useUppercase) requiredChars.push(getRandomChar(uppercaseChars))
		if (useLowercase) requiredChars.push(getRandomChar(lowercaseChars))
		if (useNumbers) requiredChars.push(getRandomChar(numberChars))
		if (useSpecial) requiredChars.push(getRandomChar(specialChars))
		if (useExtended) requiredChars.push(getRandomChar(extendedChars))

		finalPassword = requiredChars.join('') + password.slice(requiredChars.length)
	}

	return shuffleString(finalPassword).slice(0, length)
}

function getRandomChar(characters) {
	return characters.charAt(Math.floor(Math.random() * characters.length))
}

function shuffleString(str) {
	const array = str.split('')
	for (let i = array.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1))
		;[array[i], array[j]] = [array[j], array[i]]
	}
	return array.join('')
}

function initializeTheme() {
	browser.storage.local.get('theme').then((result) => {
		if (!result.theme) {
			const mediaMatcher = window.matchMedia('(prefers-color-scheme: dark)')
			const isDark = mediaMatcher.matches
			browser.storage.local.set({ theme: isDark ? 'dark' : 'light' })

			mediaMatcher.addEventListener('change', (e) => {
				browser.storage.local.set({ theme: e.matches ? 'dark' : 'light' })
			})
		}
	})
}

initializeTheme()
