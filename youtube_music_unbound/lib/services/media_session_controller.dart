import 'dart:async';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:audio_service/audio_service.dart';
import '../models/track_metadata.dart';
import '../models/playback_state.dart' as app;
import '../models/media_command.dart';

abstract class MediaSessionController {
  void updateMetadata(TrackMetadata metadata);
  void updatePlaybackState(app.PlaybackState state);
  void setPlaybackPosition(Duration position, Duration duration);
  Stream<MediaCommand> get commandStream;
  Future<void> dispose();
}

MediaSessionController createMediaSessionController() {
  if (Platform.isAndroid) {
    return _AndroidController();
  } else if (Platform.isLinux) {
    return _LinuxController();
  } else if (Platform.isWindows || Platform.isMacOS) {
    return _DesktopController();
  }
  throw UnsupportedError('Platform not supported');
}

class _AndroidController implements MediaSessionController {
  final _commands = StreamController<MediaCommand>.broadcast();
  AudioHandler? _handler;
  bool _initialized = false;
  Completer<void>? _initCompleter;

  @override
  Stream<MediaCommand> get commandStream => _commands.stream;

  _AndroidController() {
    _init();
  }

  Future<void> _init() async {
    if (_initialized) return;
    if (_initCompleter != null) {
      await _initCompleter!.future;
      return;
    }
    _initCompleter = Completer<void>();
    try {
      _handler = await AudioService.init(
        builder: () => _AudioHandler(_commands),
        config: const AudioServiceConfig(
          androidNotificationChannelId: 'com.youtube_music_unbound.channel',
          androidNotificationChannelName: 'YouTube Music Unbound',
          androidNotificationOngoing: false,
          androidShowNotificationBadge: true,
          androidStopForegroundOnPause: false,
          androidNotificationClickStartsActivity: true,
          androidResumeOnClick: true,
        ),
      );
      _initialized = true;
      _initCompleter!.complete();
    } catch (e) {
      _initCompleter!.completeError(e);
      _initCompleter = null;
    }
  }

  @override
  void updateMetadata(TrackMetadata metadata) async {
    try {
      await _init();
      final item = MediaItem(
        id: metadata.artworkUrl ?? metadata.title,
        title: metadata.title,
        artist: metadata.artist,
        album: metadata.album,
        artUri: metadata.artworkUrl != null
            ? Uri.parse(metadata.artworkUrl!)
            : null,
        duration: metadata.duration,
        playable: true,
      );
      if (_handler is _AudioHandler) {
        (_handler as _AudioHandler).setMediaItem(item);
      }
    } catch (_) {}
  }

  @override
  void updatePlaybackState(app.PlaybackState state) async {
    try {
      await _init();
      final pbState = PlaybackState(
        controls: [
          MediaControl.skipToPrevious,
          state == app.PlaybackState.playing
              ? MediaControl.pause
              : MediaControl.play,
          MediaControl.skipToNext,
        ],
        systemActions: const {
          MediaAction.seek,
          MediaAction.seekForward,
          MediaAction.seekBackward,
          MediaAction.play,
          MediaAction.pause,
          MediaAction.skipToNext,
          MediaAction.skipToPrevious,
        },
        androidCompactActionIndices: const [0, 1, 2],
        processingState: _toProcessingState(state),
        playing: state == app.PlaybackState.playing,
      );
      if (_handler is _AudioHandler) {
        (_handler as _AudioHandler).setState(pbState);
      }
    } catch (_) {}
  }

  @override
  void setPlaybackPosition(Duration position, Duration duration) async {
    try {
      await _init();
      final current = _handler?.playbackState.value;
      if (current != null && _handler is _AudioHandler) {
        (_handler as _AudioHandler).setState(
          current.copyWith(updatePosition: position),
        );
      }
    } catch (_) {}
  }

  AudioProcessingState _toProcessingState(app.PlaybackState state) {
    switch (state) {
      case app.PlaybackState.playing:
      case app.PlaybackState.paused:
        return AudioProcessingState.ready;
      case app.PlaybackState.stopped:
        return AudioProcessingState.idle;
      case app.PlaybackState.buffering:
        return AudioProcessingState.buffering;
    }
  }

  @override
  Future<void> dispose() async {
    await _commands.close();
    await _handler?.stop();
    _handler = null;
  }
}

class _AudioHandler extends BaseAudioHandler {
  final StreamController<MediaCommand> _commands;
  bool _wasPlaying = false;

  _AudioHandler(this._commands);

  void setMediaItem(MediaItem item) => mediaItem.add(item);
  void setState(PlaybackState state) => playbackState.add(state);

  @override
  Future<void> play() async => _commands.add(MediaCommand.play);

  @override
  Future<void> pause() async => _commands.add(MediaCommand.pause);

  @override
  Future<void> skipToNext() async => _commands.add(MediaCommand.next);

  @override
  Future<void> skipToPrevious() async => _commands.add(MediaCommand.previous);

  @override
  Future<void> stop() async => _commands.add(MediaCommand.stop);

  @override
  Future<void> onTaskRemoved() async {
    await stop();
    await super.onTaskRemoved();
  }

  @override
  Future<void> customAction(String name, [Map<String, dynamic>? extras]) async {
    if (name == 'audioFocusLoss') {
      final permanent = extras?['permanent'] as bool? ?? false;
      _wasPlaying = playbackState.value.playing;
      if (_wasPlaying) await pause();
      if (permanent) _wasPlaying = false;
    } else if (name == 'audioFocusGain') {
      if (_wasPlaying) {
        await play();
        _wasPlaying = false;
      }
    }
    await super.customAction(name, extras);
  }
}

class _DesktopController implements MediaSessionController {
  final _commands = StreamController<MediaCommand>.broadcast();
  static const _channel = MethodChannel('youtube_music_unbound/smtc');
  bool _initialized = false;

  @override
  Stream<MediaCommand> get commandStream => _commands.stream;

  _DesktopController() {
    if (Platform.isWindows || Platform.isMacOS) {
      _channel.setMethodCallHandler(_handleCall);
    }
  }

  Future<void> _init() async {
    if (_initialized || (!Platform.isWindows && !Platform.isMacOS)) {
      return;
    }
    try {
      await _channel.invokeMethod('initialize');
      _initialized = true;
    } catch (_) {}
  }

  Future<void> _handleCall(MethodCall call) async {
    if (call.method == 'onMediaCommand') {
      final args = call.arguments as Map<dynamic, dynamic>;
      final cmd = _parseCommand(args['command'] as String);
      if (cmd != null) _commands.add(cmd);
    }
  }

  MediaCommand? _parseCommand(String cmd) {
    switch (cmd) {
      case 'play':
        return MediaCommand.play;
      case 'pause':
        return MediaCommand.pause;
      case 'next':
        return MediaCommand.next;
      case 'previous':
        return MediaCommand.previous;
      case 'stop':
        return MediaCommand.stop;
      default:
        return null;
    }
  }

  @override
  void updateMetadata(TrackMetadata metadata) async {
    if (!Platform.isWindows && !Platform.isMacOS) return;
    await _init();
    try {
      await _channel.invokeMethod('updateMetadata', {
        'title': metadata.title,
        'artist': metadata.artist,
        'album': metadata.album ?? '',
        'artworkUrl': metadata.artworkUrl ?? '',
      });
    } catch (_) {}
  }

  @override
  void updatePlaybackState(app.PlaybackState state) async {
    if (!Platform.isWindows && !Platform.isMacOS) return;
    await _init();
    try {
      await _channel.invokeMethod('updatePlaybackState', {
        'state': _stateToString(state),
      });
    } catch (_) {}
  }

  @override
  void setPlaybackPosition(Duration position, Duration duration) async {
    if (!Platform.isWindows && !Platform.isMacOS) return;
    await _init();
    try {
      await _channel.invokeMethod('setPlaybackPosition', {
        'position': position.inMilliseconds,
        'duration': duration.inMilliseconds,
      });
    } catch (_) {}
  }

  String _stateToString(app.PlaybackState state) {
    switch (state) {
      case app.PlaybackState.playing:
        return 'playing';
      case app.PlaybackState.paused:
      case app.PlaybackState.buffering:
        return 'paused';
      case app.PlaybackState.stopped:
        return 'stopped';
    }
  }

  @override
  Future<void> dispose() async => await _commands.close();
}

class _LinuxController implements MediaSessionController {
  final _commands = StreamController<MediaCommand>.broadcast();
  static const _channel = MethodChannel('youtube_music_unbound/mpris');
  bool _initialized = false;

  @override
  Stream<MediaCommand> get commandStream => _commands.stream;

  _LinuxController() {
    _channel.setMethodCallHandler(_handleCall);
  }

  Future<void> _init() async {
    if (_initialized) return;
    try {
      await _channel.invokeMethod('initialize');
      _initialized = true;
    } catch (_) {}
  }

  Future<void> _handleCall(MethodCall call) async {
    if (call.method == 'onMediaCommand') {
      final args = call.arguments as Map<dynamic, dynamic>;
      final cmd = _parseCommand(args['command'] as String);
      if (cmd != null) _commands.add(cmd);
    }
  }

  MediaCommand? _parseCommand(String cmd) {
    switch (cmd) {
      case 'play':
        return MediaCommand.play;
      case 'pause':
        return MediaCommand.pause;
      case 'next':
        return MediaCommand.next;
      case 'previous':
        return MediaCommand.previous;
      case 'stop':
        return MediaCommand.stop;
      default:
        return null;
    }
  }

  @override
  void updateMetadata(TrackMetadata metadata) async {
    await _init();
    try {
      await _channel.invokeMethod('updateMetadata', {
        'title': metadata.title,
        'artist': metadata.artist,
        'album': metadata.album ?? '',
        'artworkUrl': metadata.artworkUrl ?? '',
      });
    } catch (_) {}
  }

  @override
  void updatePlaybackState(app.PlaybackState state) async {
    await _init();
    try {
      await _channel.invokeMethod('updatePlaybackState', {
        'state': _stateToString(state),
      });
    } catch (_) {}
  }

  @override
  void setPlaybackPosition(Duration position, Duration duration) async {
    await _init();
    try {
      await _channel.invokeMethod('setPlaybackPosition', {
        'position': position.inMicroseconds,
        'duration': duration.inMicroseconds,
      });
    } catch (_) {}
  }

  String _stateToString(app.PlaybackState state) {
    switch (state) {
      case app.PlaybackState.playing:
        return 'playing';
      case app.PlaybackState.paused:
      case app.PlaybackState.buffering:
        return 'paused';
      case app.PlaybackState.stopped:
        return 'stopped';
    }
  }

  @override
  Future<void> dispose() async => await _commands.close();
}
