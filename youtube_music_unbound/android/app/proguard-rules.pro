# Flutter wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# InAppWebView
-keep class com.pichillilorenzo.flutter_inappwebview.** { *; }
-keep class android.webkit.** { *; }

# Audio Service
-keep class com.ryanheise.audioservice.** { *; }

# Discord RPC
-keep class dev.luan.discord_rpc.** { *; }

# Preserve annotations
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes Exceptions

# Google Play Core (dontwarn for missing classes)
-dontwarn com.google.android.play.core.**
-keep class com.google.android.play.core.** { *; }
