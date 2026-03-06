#!/bin/bash
set -euo pipefail

readonly TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

fetch_latest_version() {
    local keyring_path="/usr/share/keyrings/antigravity-archive-keyring.gpg"
    local sources_path="/etc/apt/sources.list.d/antigravity.list"
    
    curl -fsSL "https://us-central1-apt.pkg.dev/doc/repo-signing-key.gpg" \
        | gpg --batch --yes --dearmor -o "$keyring_path"
    
    echo "deb [signed-by=$keyring_path arch=amd64] \
https://us-central1-apt.pkg.dev/projects/antigravity-auto-updater-dev/ \
antigravity-debian main" > "$sources_path"
    
    apt-get update -qq
    
    local version=$(apt-cache madison antigravity | head -n1 | \
        awk '{print $3}' | cut -d'-' -f1)
    local url=$(apt-get download --print-uris antigravity | \
        awk '{print $1}' | tr -d "'")
    
    curl -fsSL -o "$TEMP_DIR/antigravity.deb" "$url"
    local sha256=$(sha256sum "$TEMP_DIR/antigravity.deb" | awk '{print $1}')
    
    echo "$version $sha256 $url"
}

update_pkgbuild() {
    local version=$1
    local sha256=$2
    local url=$3
    
    sed -i "s/^pkgver=.*/pkgver=$version/" PKGBUILD
    sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
    sed -i "s|antigravity-.*\.deb::|antigravity-$version.deb::|" PKGBUILD
    sed -i "s|antigravity_.*_amd64|antigravity_${version}-$(echo $url | \
        grep -oP 'antigravity_[^_]*-\K[^_]*')|" PKGBUILD
    sed -i "s/^sha256sums=.*/sha256sums=('$sha256')/" PKGBUILD
}

main() {
    if ! command -v docker &>/dev/null; then
        echo "Error: docker required" >&2
        exit 1
    fi
    
    local output=$(docker run --rm ubuntu:22.04 bash -c "
        apt-get update -qq && apt-get install -y -qq curl gnupg apt-transport-https
        $(declare -f fetch_latest_version)
        fetch_latest_version
    ")
    
    read -r version sha256 url <<< "$output"
    
    local current_version=$(grep '^pkgver=' PKGBUILD | cut -d'=' -f2)
    
    if [ "$current_version" = "$version" ]; then
        echo "Already up to date: $version"
        exit 0
    fi
    
    echo "Updating from $current_version to $version"
    update_pkgbuild "$version" "$sha256" "$url"
    
    makepkg --printsrcinfo > .SRCINFO
    
    echo "Updated to version $version"
}

main
