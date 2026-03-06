# google-antigravity-bin

Arch Linux package for Google Antigravity IDE.

## Installation

### From AUR

```bash
yay -S google-antigravity-bin
```

### Manual

```bash
git clone https://aur.archlinux.org/google-antigravity-bin.git
cd google-antigravity-bin
makepkg -si
```

## Updating

The package is automatically updated via GitHub Actions every 6 hours and 
published to AUR.

To manually check for updates:

```bash
./update-version.sh
makepkg -si
```

## Setup for AUR Publishing

Add these secrets to your GitHub repository:

- `AUR_USERNAME`: Your AUR username
- `AUR_EMAIL`: Your AUR email
- `AUR_SSH_PRIVATE_KEY`: Your AUR SSH private key

## License

Google Antigravity is proprietary software by Google.
