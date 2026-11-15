# Passugar 🍬

> **Because life's too short for weak passwords!**

Passugar is a delightfully simple browser extension that makes password management a piece of cake! Generate rock-solid passwords and memorable passphrases in just one click.

The name? It's Password + Sugar = Passugar... because we're making secure passwords sweet and easy to use! 

## ✨ Features

- 🔐 Generate ridiculously strong passwords and passphrases
- 📋 Copy to clipboard faster than you can say "hunter2"
- 👁️ Toggle password visibility with a single click
- 🌓 Choose between dark and light theme based on your mood
- 🎨 Beautiful, modern UI that's a treat for your eyes
- 🌐 Works seamlessly on all your favorite websites
- 🔒 Privacy first: no analytics, no tracking, no cookies
- 🙅‍♂️ Stores absolutely nothing - your passwords stay with you

## 🚀 Installation

### Firefox

1. Visit [Passugar on Firefox Add-ons](https://addons.mozilla.org/firefox/addon/passugar/) (coming soon!)
2. Click "Add to Firefox"
3. Enjoy your new password superpowers!

### Manual Installation

1. Download this repository
2. Open Firefox and navigate to `about:debugging`
3. Click "This Firefox" → "Load Temporary Add-on..."
4. Select the `manifest.json` file from the downloaded folder
5. Look at you, living on the edge!

## 🍰 How to Use

### Generate a Password

1. Click the Passugar icon in your toolbar
2. Hit the "Generate Password" button
3. Copy your new super-secure password with one click
4. Paste it wherever you need a strong password
5. Sleep well knowing your accounts are safer!

### On Password Fields

1. Click on any password field on a website
2. See our magical overlay appear
3. Click "Use strong password"
4. Watch as Passugar fills in a strong password for you
5. Feel smug about your excellent security practices

## 🛠️ Password Settings

Passugar isn't just powerful—it's flexible too:

- **Password Length**: Crank it up to 128 characters if you're feeling paranoid!
- **Character Types**: Mix and match uppercase, lowercase, numbers, symbols, and even extended ASCII
- **Passphrase Mode**: Generate memorable phrases instead of random characters
- **Word Count**: Choose how many words you want in your passphrase

## 🔍 Security Notes

- All password generation happens locally in your browser
- No passwords are ever transmitted, stored, or logged
- We request only the minimum permissions needed to function
- It's just you, your browser, and some sweet password generation

## 🧪 Development

Want to contribute or customize? Passugar's code is as clean as its UI:

```
passugar/
├── manifest.json     # Extension configuration
├── background.js     # Background processes
├── content.js        # Content script for web page integration
├── overlay.css       # Styles for the password field overlay
├── popup/            # The main popup interface
│   ├── popup.html    # Popup structure
│   ├── popup.css     # Popup styling
│   └── popup.js      # Popup functionality
└── icons/            # Extension icons
```

## 💡 Tips & Tricks

- **Double-click** any password field to toggle visibility
- Use **passphrases** for services you need to remember (like your master password)
- Use **random passwords** for everything else (that's what password managers are for!)
- **Theme toggle** in the popup header changes between light and dark mode

## ❓ FAQ

### "How strong are these passwords, really?"

Strong enough to make even the most determined hacker consider a career change! Our standard 32-character passwords have enough entropy to withstand brute-force attacks for the foreseeable future.

### "Should I use Passugar instead of a password manager?"

Nope! Passugar pairs beautifully with password managers. We generate the passwords, they store them. It's a match made in security heaven!

### "What permissions does Passugar need?"

Just the bare minimum: `activeTab` to detect password fields and `storage` to remember your settings. No creepy permissions required!

### "Why doesn't Passugar work on [insert website]?"

Some websites use custom form fields that don't play nice with our detection. If you find one, [let us know](https://github.com/tn3w/passugar/issues) and we'll try to fix it!

## 🌐 Browser Compatibility

- **Firefox:** Fully supported and tested
- **Chromium:** Support planned for future releases

## 🕵️ Privacy Policy

Our privacy policy is so simple, it barely needs explanation:

1. We don't collect your data
2. We don't store your passwords
3. We don't track you
4. We don't use analytics
5. That's it. Really.

## 🙏 Acknowledgments

- Icon designed by [Freepik - Flaticon](https://www.flaticon.com/free-icons/sugar)
- Built with ❤️ using vanilla JavaScript, CSS, and HTML
- Inspired by all the terrible password policies we've encountered

## 📜 License

Passugar is released under the MIT License. Do what you want with it—we're not your mom!

## 💖 Why Passugar?

Because password management shouldn't require a PhD in cryptography or the patience of a saint. We made password security sweet and simple—just the way it should be.

Remember: a good password is like a good joke. Nobody should be able to guess it!

---

*Made with ❤️ and a sprinkle of sugar. Don't forget to brush your teeth after using!*
