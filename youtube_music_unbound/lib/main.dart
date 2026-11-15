import 'dart:io' show Platform, exit;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:window_manager/window_manager.dart';
import 'services/media_session_controller.dart';
import 'services/system_tray_manager.dart';
import 'services/discord_rpc_service.dart';
import 'models/track_metadata.dart';
import 'models/playback_state.dart';
import 'models/media_command.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (Platform.isAndroid) {
    try {
      await InAppWebViewController.setWebContentsDebuggingEnabled(true);
    } catch (e) {
      // Ignore errors enabling web contents debugging
    }
  }

  runApp(const YouTubeMusicUnbound());
}

class YouTubeMusicUnbound extends StatelessWidget {
  const YouTubeMusicUnbound({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'YouTube Music Unbound',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true),
      home: const WebViewContainer(),
    );
  }
}

class WebViewContainer extends StatefulWidget {
  const WebViewContainer({super.key});

  @override
  State<WebViewContainer> createState() => _WebViewContainerState();
}

class _WebViewContainerState extends State<WebViewContainer>
    with WidgetsBindingObserver {
  InAppWebViewController? webViewController;
  MediaSessionController? _mediaSessionController;
  SystemTrayManager? _systemTrayManager;
  DiscordRpcService? _discordRpcService;

  static const String _youtubeMusicUrl = 'https://music.youtube.com';

  TrackMetadata? _currentMetadata;
  PlaybackState _playbackState = PlaybackState.stopped;

  static const List<String> _blockPatterns = [
    'youtube.com/pagead/',
    'youtube.com/ptracking',
    'youtube.com/api/stats/ads',
    'youtube.com/api/stats/atr',
    'youtube.com/youtubei/v1/player/ad_break',
    'youtube.com/get_midroll_',
    '/get_video_info?*=adunit',
    '/get_video_info?*adunit',
    'initplayback?source=youtube',
    'googlesyndication.com',
    'googleadservices.com',
    'googleads.g.doubleclick.net',
    'doubleclick.net',
    'google.com/pagead/',
    'googletagmanager.com',
    'googletagservices.com',
    'googlevideo.com/initplayback',
    'youtube.com/error_204',
    'youtube.com/generate_204',
    'youtube.com/csi_204',
    's.youtube.com/api/stats/watchtime',
    'youtube.com/api/stats/watchtime',
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeMediaSession();
    _initializeSystemTray();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (!Platform.isAndroid) return;
    if (state == AppLifecycleState.detached) {
      _gracefulShutdown();
    }
  }

  void _initializeMediaSession() {
    if (!_isDesktop && !Platform.isAndroid && !Platform.isIOS) return;

    try {
      _mediaSessionController = createMediaSessionController();
      _mediaSessionController?.commandStream.listen(
        _handleMediaCommand,
        onError: (error) {},
      );
    } catch (e) {
      // Ignore media session initialization errors
    }
  }

  bool get _isDesktop =>
      Platform.isWindows || Platform.isLinux || Platform.isMacOS;

  void _initializeSystemTray() {
    if (!_isDesktop) return;

    try {
      _systemTrayManager = SystemTrayManager(
        onMediaCommand: _handleMediaCommand,
        onExit: _handleExit,
      );
      _systemTrayManager?.initialize();
    } catch (e) {
      // Ignore system tray initialization errors
    }
  }

  void _ensureDiscordRpcInitialized() {
    if (_discordRpcService != null || !_isDesktop) return;

    try {
      _discordRpcService = DiscordRpcService();
      _discordRpcService?.initialize();
    } catch (e) {
      // Ignore Discord RPC initialization errors
    }
  }

  void _handleExit() {
    _systemTrayManager?.dispose();
    _mediaSessionController?.dispose();
    _discordRpcService?.dispose();
    exit(0);
  }

  void _handleMediaCommand(MediaCommand command) {
    executePlaybackCommand(PlaybackCommand(command: command));
  }

  void _handleMetadataUpdate(Map<String, dynamic> metadata) {
    try {
      final newMetadata = TrackMetadata.fromJson(metadata);

      setState(() => _currentMetadata = newMetadata);

      _mediaSessionController?.updateMetadata(newMetadata);

      if (newMetadata.position != null && newMetadata.duration != null) {
        _mediaSessionController?.setPlaybackPosition(
          newMetadata.position!,
          newMetadata.duration!,
        );
      }

      _ensureDiscordRpcInitialized();
      _discordRpcService?.updateMetadata(newMetadata, _playbackState);
    } catch (e) {
      final fallbackMetadata = TrackMetadata(
        title: metadata['title']?.toString() ?? 'Unknown',
        artist: metadata['artist']?.toString() ?? 'Unknown',
        album: metadata['album']?.toString(),
        artworkUrl: metadata['artworkUrl']?.toString(),
        duration: null,
        position: null,
      );
      setState(() => _currentMetadata = fallbackMetadata);
    }
  }

  void _handlePlaybackStateUpdate(Map<String, dynamic> stateData) {
    try {
      final stateString = stateData['state'] as String?;
      if (stateString == null) return;

      final newState = _parsePlaybackState(stateString);

      setState(() => _playbackState = newState);

      _mediaSessionController?.updatePlaybackState(newState);
      _systemTrayManager?.updatePlaybackState(newState);

      if (_currentMetadata != null) {
        _ensureDiscordRpcInitialized();
        _discordRpcService?.updateMetadata(_currentMetadata!, newState);
      }
    } catch (e) {
      // Ignore playback state update errors
    }
  }

  PlaybackState _parsePlaybackState(String state) {
    switch (state.toLowerCase()) {
      case 'playing':
        return PlaybackState.playing;
      case 'paused':
        return PlaybackState.paused;
      case 'buffering':
        return PlaybackState.buffering;
      default:
        return PlaybackState.stopped;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: _isMobile
          ? RepaintBoundary(
              child: InAppWebView(
                initialUrlRequest: URLRequest(url: WebUri(_youtubeMusicUrl)),
                initialSettings: _getWebViewSettings(),
                onWebViewCreated: _onWebViewCreated,
                onLoadStop: _onLoadStop,
                onReceivedError: _onReceivedError,
                onReceivedHttpError: _onReceivedHttpError,
                shouldInterceptRequest: _shouldInterceptRequest,
              ),
            )
          : Stack(
              children: [
                RepaintBoundary(
                  child: InAppWebView(
                    initialUrlRequest: URLRequest(
                      url: WebUri(_youtubeMusicUrl),
                    ),
                    initialSettings: _getWebViewSettings(),
                    onWebViewCreated: _onWebViewCreated,
                    onLoadStop: _onLoadStop,
                    onReceivedError: _onReceivedError,
                    onReceivedHttpError: _onReceivedHttpError,
                    shouldInterceptRequest: _shouldInterceptRequest,
                  ),
                ),
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: _buildCustomTitleBar(context),
                ),
              ],
            ),
    );
  }

  Future<void> _onWebViewCreated(InAppWebViewController controller) async {
    try {
      webViewController = controller;

      final adblockScript = await rootBundle.loadString(
        'assets/scripts/adblock.js',
      );

      await controller.addUserScript(
        userScript: UserScript(
          source: adblockScript,
          injectionTime: UserScriptInjectionTime.AT_DOCUMENT_START,
          contentWorld: ContentWorld.PAGE,
          forMainFrameOnly: false,
        ),
      );

      await _setupJavaScriptHandlers(controller);

      if (_isDesktop) {
        await _injectTransparentTitleBarCSS(controller);
      }
    } catch (e) {
      _showErrorSnackBar('Failed to initialize WebView');
    }
  }

  Future<void> _onLoadStop(
    InAppWebViewController controller,
    WebUri? url,
  ) async {
    try {
      if (_isDesktop) {
        final script = await rootBundle.loadString(
          'assets/scripts/transparent_titlebar.js',
        );
        await controller.evaluateJavascript(source: script);
      }

      final metadataScript = await rootBundle.loadString(
        'assets/scripts/metadata_extractor.js',
      );
      await controller.evaluateJavascript(source: metadataScript);

      final controlsScript = await rootBundle.loadString(
        'assets/scripts/media_controls.js',
      );
      await controller.evaluateJavascript(source: controlsScript);
    } catch (e) {
      // Ignore load stop errors
    }
  }

  bool get _isMobile => Platform.isAndroid || Platform.isIOS;

  void _onReceivedError(
    InAppWebViewController controller,
    WebResourceRequest request,
    WebResourceError error,
  ) {
    _showErrorSnackBar('Failed to load YouTube Music. Check connection.');
  }

  void _onReceivedHttpError(
    InAppWebViewController controller,
    WebResourceRequest request,
    WebResourceResponse errorResponse,
  ) {
    final statusCode = errorResponse.statusCode ?? 0;
    if (statusCode >= 500) {
      _showErrorSnackBar('Server error. Try again later.');
    } else if (statusCode >= 400) {
      _showErrorSnackBar('Failed to load content.');
    }
  }

  Future<WebResourceResponse?> _shouldInterceptRequest(
    InAppWebViewController controller,
    WebResourceRequest request,
  ) async {
    final url = request.url.toString();
    if (_shouldBlockUrl(url)) {
      String contentType = 'text/plain';
      Uint8List data;

      if (url.contains('.js')) {
        contentType = 'application/javascript';
        data = Uint8List.fromList('void 0;'.codeUnits);
      } else if (url.contains('.json') ||
          url.contains('api/stats') ||
          url.contains('youtubei/v1')) {
        contentType = 'application/json';
        data = Uint8List.fromList('{}'.codeUnits);
      } else if (url.contains('.css')) {
        contentType = 'text/css';
        data = Uint8List.fromList(''.codeUnits);
      } else {
        data = Uint8List.fromList(' '.codeUnits);
      }

      return WebResourceResponse(
        data: data,
        statusCode: 200,
        reasonPhrase: 'OK',
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
        },
      );
    }
    return null;
  }

  bool _shouldBlockUrl(String url) {
    return _blockPatterns.any((pattern) => url.contains(pattern));
  }

  Widget _buildCustomTitleBar(BuildContext context) {
    return Container(
      height: 40,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.black.withValues(alpha: 0.7),
            Colors.black.withValues(alpha: 0.3),
            Colors.transparent,
          ],
        ),
      ),
      child: Row(
        children: [
          const SizedBox(width: 12),
          const Text(
            'YouTube Music Unbound',
            style: TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w500,
              shadows: [
                Shadow(
                  color: Colors.black54,
                  offset: Offset(0, 1),
                  blurRadius: 2,
                ),
              ],
            ),
          ),
          const Spacer(),
          _buildTitleBarButton(
            icon: Icons.remove,
            onPressed: () async {
              await windowManager.minimize();
            },
          ),
          _buildTitleBarButton(
            icon: Icons.crop_square,
            onPressed: () async {
              final isMaximized = await windowManager.isMaximized();
              if (isMaximized) {
                await windowManager.unmaximize();
              } else {
                await windowManager.maximize();
              }
            },
          ),
          _buildTitleBarButton(
            icon: Icons.close,
            onPressed: () async {
              await windowManager.hide();
            },
            isClose: true,
          ),
        ],
      ),
    );
  }

  Widget _buildTitleBarButton({
    required IconData icon,
    required VoidCallback onPressed,
    bool isClose = false,
  }) {
    return SizedBox(
      width: 46,
      height: 32,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          hoverColor: isClose ? Colors.red : Colors.white12,
          child: Icon(icon, size: 16, color: Colors.white70),
        ),
      ),
    );
  }

  InAppWebViewSettings _getWebViewSettings() {
    final userAgent = Platform.isAndroid
        ? 'Mozilla/5.0 (Linux; Android 10; K) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/134.0.0.0 Mobile Safari/537.3'
        : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/605.1.15 (KHTML, like Gecko) '
              'Version/17.10 Safari/605.1.1';

    return InAppWebViewSettings(
      userAgent: userAgent,
      thirdPartyCookiesEnabled: false,
      javaScriptEnabled: true,
      mediaPlaybackRequiresUserGesture: false,
      allowsInlineMediaPlayback: true,
      transparentBackground: false,
      disableContextMenu: true,
      supportZoom: false,
      useOnLoadResource: true,
      hardwareAcceleration: true,
      useHybridComposition: Platform.isAndroid,
      cacheEnabled: true,
      clearCache: false,
      incognito: false,
      useOnDownloadStart: false,
      enableViewportScale: true,
      disableVerticalScroll: false,
      disableHorizontalScroll: false,
      allowsPictureInPictureMediaPlayback: true,
      blockNetworkImage: false,
      blockNetworkLoads: false,
    );
  }

  Future<void> _injectTransparentTitleBarCSS(
    InAppWebViewController controller,
  ) async {
    try {
      final script = await rootBundle.loadString(
        'assets/scripts/transparent_titlebar.js',
      );

      await controller.addUserScript(
        userScript: UserScript(
          source: script,
          injectionTime: UserScriptInjectionTime.AT_DOCUMENT_END,
        ),
      );
    } catch (e) {
      // Ignore injection errors
    }
  }

  Future<void> _setupJavaScriptHandlers(
    InAppWebViewController controller,
  ) async {
    try {
      controller.addJavaScriptHandler(
        handlerName: 'metadataUpdate',
        callback: (args) {
          if (args.isNotEmpty && args[0] is Map) {
            _handleMetadataUpdate(Map<String, dynamic>.from(args[0]));
          }
        },
      );

      controller.addJavaScriptHandler(
        handlerName: 'playbackStateUpdate',
        callback: (args) {
          if (args.isNotEmpty && args[0] is Map) {
            _handlePlaybackStateUpdate(Map<String, dynamic>.from(args[0]));
          }
        },
      );
    } catch (e) {
      // Ignore JavaScript handler setup errors
    }
  }

  Future<bool> executePlaybackCommand(PlaybackCommand command) async {
    if (webViewController == null) return false;

    try {
      final commandName = command.command.name.toLowerCase();
      await webViewController!.evaluateJavascript(
        source:
            '''
          if (window.executeMediaCommand) {
            window.executeMediaCommand("$commandName");
          }
        ''',
      );
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> _gracefulShutdown() async {
    try {
      if (_playbackState == PlaybackState.playing) {
        await executePlaybackCommand(
          PlaybackCommand(command: MediaCommand.pause),
        );
      }

      await _mediaSessionController?.dispose();
      _discordRpcService?.dispose();
    } catch (e) {
      // Ignore shutdown errors
    }
  }

  void _showErrorSnackBar(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 4),
        behavior: SnackBarBehavior.floating,
        action: SnackBarAction(
          label: 'Dismiss',
          onPressed: () {
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
          },
        ),
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);

    try {
      _systemTrayManager?.dispose();
      _mediaSessionController?.dispose();
      _discordRpcService?.dispose();
    } catch (e) {
      // Ignore dispose errors
    }

    webViewController = null;
    super.dispose();
  }
}
