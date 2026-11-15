<picture>
   <img alt="Preview of Lyrics Prompter" src="https://github.com/tn3w/lyrics-prompter/releases/download/img/lyrics-prompter.png"></img>
</picture>

<h2 align="center">Lyrics Prompter</h2>
<p align="center">A lightweight desktop application for <strong>displaying synchronized lyrics</strong>, designed for karaoke-style prompting during performances or practice sessions.</p>

<p align="center">
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-windows-x64-setup.exe"><img src="https://img.shields.io/badge/Windows-Installer-blue?style=for-the-badge&logo=windows" alt="Windows Installer"></a>
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-windows-x86-setup.exe"><img src="https://img.shields.io/badge/Windows_x86-Installer-blue?style=for-the-badge&logo=windows" alt="Windows x86 Installer"></a>
</p>
<p align="center">
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-windows-x64.exe"><img src="https://img.shields.io/badge/Windows-Portable-blue?style=for-the-badge&logo=windows" alt="Windows Portable"></a>
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-windows-x86.exe"><img src="https://img.shields.io/badge/Windows_x86-Portable-blue?style=for-the-badge&logo=windows" alt="Windows x86 Portable"></a>
</p>
<p align="center">
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-x86_64.AppImage"><img src="https://img.shields.io/badge/Linux-AppImage-orange?style=for-the-badge&logo=linux" alt="Linux AppImage Download"></a>
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-amd64.deb"><img src="https://img.shields.io/badge/Linux-.deb-orange?style=for-the-badge&logo=debian" alt="Linux .deb Download"></a>
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics_prompter-x86_64.rpm"><img src="https://img.shields.io/badge/Linux-.rpm-orange?style=for-the-badge&logo=redhat" alt="Linux .rpm Download"></a>
  <a href="https://github.com/tn3w/lyrics-prompter/releases/latest/download/lyrics-prompter-x86_64.pkg.tar.gz"><img src="https://img.shields.io/badge/Linux-Arch-orange?style=for-the-badge&logo=archlinux" alt="Arch Linux Download"></a>
</p>

## Features

- Load and display LRC (synchronized lyrics) files
- Optional audio playback support (MP3, WAV, OGG, FLAC)
- Lyrics-only mode when no audio is loaded
- Real-time countdown to next line
- Progress bar showing current line timing
- Fullscreen mode for stage use
- Resizable window with automatic text scaling

## Usage

1. Click "Load LRC" to open a synchronized lyrics file
2. Optionally click "Load Audio" to load an audio track
3. Click "Play" (or "Lyrics" if no audio) to start
4. Use "Pause" and "Stop" to control playback
5. Toggle "Fullscreen" for distraction-free display

## Building

Requires Rust toolchain.

```sh
cargo build --release
```

The binary will be in `target/release/`.

## Dependencies

- minifb - Window and graphics
- rodio - Audio playback
- rfd - File dialogs
- rusttype - Font rendering

## Platform Support

- Windows (uses Arial Bold font)
- Linux (uses DejaVu Sans Bold font)

## License

Copyright 2025 TN3W

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.