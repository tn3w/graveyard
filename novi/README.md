# Novi

Open-source music player for Android.

**Repository:** https://github.com/tn3w/novi  
**Tags:** music, audio, player, android, kotlin, jetpack-compose, media3

## Requirements

- Android 8.0+ (API 26)
- Android Studio or Gradle 9.4+

## Run in Emulator (no Android Studio)

### One-time setup

```bash
# Install cmdline-tools
cd /tmp
curl -O https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip
unzip commandlinetools-linux-13114758_latest.zip
mkdir -p ~/Android/Sdk/cmdline-tools
mv cmdline-tools ~/Android/Sdk/cmdline-tools/latest

export ANDROID_HOME=~/Android/Sdk
TOOLS=$ANDROID_HOME/cmdline-tools/latest/bin

# Install a system image and create an AVD
yes | $TOOLS/sdkmanager "system-images;android-35;google_apis;x86_64"
echo "no" | $TOOLS/avdmanager create avd -n novi_avd \
  -k "system-images;android-35;google_apis;x86_64" --device "pixel_6"
```

### Run

```bash
export ANDROID_HOME=~/Android/Sdk

# Start emulator
$ANDROID_HOME/emulator/emulator -avd novi_avd -no-snapshot-load &

# Build APK
./gradlew assembleDebug

# Wait for boot, then install and launch
until $ANDROID_HOME/platform-tools/adb shell getprop sys.boot_completed \
  2>/dev/null | grep -q "1"; do sleep 3; done

$ANDROID_HOME/platform-tools/adb install app/build/outputs/apk/debug/app-debug.apk
$ANDROID_HOME/platform-tools/adb shell monkey -p com.tn3w.novi -c android.intent.category.LAUNCHER 1
```

## Build

```bash
./gradlew assembleDebug
```

## Stack

| Layer    | Library                     |
| -------- | --------------------------- |
| UI       | Jetpack Compose + Material3 |
| Playback | Media3 ExoPlayer            |
| Language | Kotlin 2.1                  |

## UI

**Bottom navigation bar** with 5 tabs: Home, Discover, Search, Library, Me.

- Icons switch between outlined (unselected) and filled (selected)
- Top edge fades to transparent via vertical gradient, blending into page content
- Adapts to dark and light mode via `NoviTheme` (green accent)
- Theme defined in `ui/theme/Theme.kt` + `ui/theme/Color.kt`
- `BottomNavBar` composable in `ui/components/BottomNavBar.kt`

**Now Playing** — mini bar + full-page player in `NowPlayingSheet.kt`.

- Tap mini bar to expand into full-screen player with spring animation
- Full player: down arrow, playlist name, large album art, track info, like/add buttons, seek bar with thumb, toggleable time display, shuffle/prev/play/next/repeat controls, bottom action row (device, share, lyrics, queue, more)
- Background uses the track's dominant color
- Bottom nav and mini bar hide when player is expanded
- Swipe down or tap arrow to collapse back

## Project Structure

```
novi/
├── app/
│   ├── src/main/
│   │   ├── java/com/tn3w/novi/
│   │   │   ├── MainActivity.kt
│   │   │   ├── ui/theme/          # Color.kt, Theme.kt (NoviTheme)
│   │   │   └── ui/components/     # BottomNavBar.kt
│   │   ├── res/
│   │   │   ├── drawable/      # adaptive icon assets (dark bg + play triangle)
│   │   │   ├── mipmap-anydpi-v26/  # ic_launcher + ic_launcher_round
│   │   │   └── values/        # strings.xml, themes.xml
│   │   └── AndroidManifest.xml
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── gradle/
│   ├── libs.versions.toml     # version catalog
│   └── wrapper/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── local.properties           # sdk.dir=/home/user/Android/Sdk
└── README.md
```

Package: `com.tn3w.novi`, minSdk 26 (Android 8.0)
AGP 8.10.0 + Kotlin 2.1.20 + Compose BOM 2025.04.01
Media3 (ExoPlayer + Session) in version catalog, ready to add when needed
`org.gradle.java.home` set to Java 17 in gradle.properties — AGP 8.x is incompatible with Java 26
Gradle 9.4.0 wrapper, configuration cache + parallel builds enabled
Permissions pre-declared: `READ_MEDIA_AUDIO, FOREGROUND_SERVICE_MEDIA_PLAYBACK`

## Credits

Design inspired by https://www.youtube.com/watch?v=suhEIUapSJQ
