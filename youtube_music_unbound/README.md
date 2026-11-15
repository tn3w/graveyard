<picture>
   <img alt="Preview of YouTube Music Unbound" src="https://github.com/tn3w/youtube_music_unbound/releases/download/img/youtube_music_unbound.jpg"></img>
</picture>

<h2 align="center">YouTube Music Unbound</h2>
<p align="center">A lightweight <strong>native YouTube Music client</strong> built with Flutter, providing a standalone app experience with enhanced privacy features, native system integration, and minimal bundle size.</p>

> [!IMPORTANT]
> Contributors Needed: The adblock.js script is currently not working properly. Looking for contributors with experience in:
> - InAppWebView and JavaScript injection
> - Communication between Flutter WebView and injected JS scripts
> - Ad blocking techniques for web-based media players
> 
> If you know how to efficiently block ads in InAppWebView environments, please contribute!

## Disclaimer

This project is not affiliated with, endorsed by, or in any way associated with Alphabet Inc., Google LLC, YouTube, or YouTube Music. All trademarks belong to their respective owners. This project is for educational purposes only.

## Features

- Native WebView Integration - Uses system WebView for minimal overhead
- Ad Blocking - Built-in UBlock Origin filters
- Media Controls - Native system media controls on all platforms
- Discord Rich Presence - Show what you're listening to
- Android Background Playback - Continue playing when minimized
- System Tray - Quick access on desktop platforms
- Privacy Enhanced - Blocks trackers and third-party cookies
- Optimized Performance - Lazy loading and efficient resource management

## Supported Platforms

- Windows (10/11 1809+) - Requires [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Linux (Ubuntu 20.04+)
- Android (7.0+, API 24+)

## How It Works

### Architecture

The app uses Flutter's InAppWebView to load YouTube Music in a native wrapper. The main entry point (`lib/main.dart`) initializes the WebView and coordinates all services.

### Services

- `MediaSessionController` - Handles native media controls (play/pause/next/previous) on Android (via audio_service), Windows/macOS (via SMTC), and Linux (via MPRIS)
- `SystemTrayManager` - Manages the system tray icon and context menu on desktop platforms
- `DiscordRpcService` - Updates Discord Rich Presence with current track information

### Injected Scripts

JavaScript scripts are injected into the WebView to extend functionality:

- `adblock.js` - Blocks ad requests, prunes ad data from API responses, hides ad elements, and auto-skips video ads
- `metadata_extractor.js` - Polls the page for track metadata (title, artist, album, artwork) and playback state, sending updates to Flutter via JS handlers
- `media_controls.js` - Exposes media control functions to Flutter by clicking the appropriate UI buttons
- `transparent_titlebar.js` - Adjusts CSS for a custom transparent title bar on desktop
- `auto_stop_blocker.js` - Dismisses the "Are you still there?" idle popup

### Ad Blocking
NOT WORKING/LACKING - Contribution Welcomed!

Ad blocking works at multiple levels:
1. Network-level blocking via `shouldInterceptRequest` in Flutter
2. API response pruning to remove ad data from YouTube responses
3. DOM element hiding via CSS injection
4. Video ad skipping by seeking to end and clicking skip buttons

## Building

### Quick Build (Optimized Release)

Android Release:
```bash
flutter build apk --release --split-debug-info=build/symbols --obfuscate
```

Windows Release:
```bash
flutter build windows --release --split-debug-info=build/symbols --obfuscate
```

Linux Release:
```bash
flutter build linux --release --split-debug-info=build/symbols --obfuscate
```

## License

Copyright 2025 YouTube Music Unbound Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
