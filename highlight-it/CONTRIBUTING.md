# Contributing to Highlight-It 🚀

Thank you for your interest in contributing to Highlight-It! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Security](#security)
- [Questions?](#questions)

## Getting Started 🎯

Before you start contributing, please:

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Submit a pull request

## Development Setup 🛠️

1. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/highlight-it.git
cd highlight-it
```

2. Install dependencies:

```bash
npm install
```

3. Open `demo.html` in your browser to see your changes in action.

## Making Changes ✨

### Branch Naming

- Feature branches: `feature/your-feature-name`
- Bug fixes: `fix/your-fix-name`
- Documentation: `docs/your-doc-name`

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Example:

```
feat(theme): add support for custom theme creation

- Add theme builder interface
- Implement theme preview
- Add theme export functionality

Closes #123
```

## Code Style 🎨

We follow these coding standards:

- Use ES6+ features
- Follow the existing code style
- Add JSDoc comments for public APIs
- Keep functions focused and small
- Use meaningful variable names
- Add error handling where appropriate

Example:

```javascript
/**
 * Creates a new code block with the specified options
 * @param {Object} options - Configuration options
 * @param {string} options.language - Programming language
 * @param {boolean} [options.withLines=false] - Whether to show line numbers
 * @returns {HTMLElement} The created code block element
 */
function createCodeBlock(options) {
    const { language, withLines = false } = options;
    // ... implementation
}
```

## Testing 🧪

> [!WARNING]
> FIXME: Tests are not added yet.

Before submitting a pull request:

1. Run the test suite:

```bash
npm test
```

2. Add tests for new features
3. Ensure all tests pass
4. Check code coverage

## Documentation 📚

When adding new features or changing existing ones:

1. Update the README.md if necessary
2. Add JSDoc comments for new functions
3. Update the API documentation
4. Add examples if applicable

## Security 🔒

For security-related concerns, please refer to our [Security Policy](SECURITY.md). This includes:

- How to report vulnerabilities
- What to report
- Our security commitments
- Security best practices
- Security acknowledgments

## Questions? ❓

If you have any questions:

1. Check the [documentation](https://github.com/tn3w/highlight-it#readme)
2. Open an issue
3. Join our discussions

## Thank You! 🙏

Your contributions help make Highlight-It better for everyone. We appreciate your time and effort!

---

<p align="center">
  Made with ❤️ by the Highlight-It Team
</p>
