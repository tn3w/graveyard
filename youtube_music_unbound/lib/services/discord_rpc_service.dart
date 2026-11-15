import 'dart:async';
import 'package:dart_discord_rpc/dart_discord_rpc.dart';
import '../models/track_metadata.dart';
import '../models/playback_state.dart';

class DiscordRpcService {
  static const String _applicationId = '1234567890123456789';
  static const int _maxRetryDelay = 30;
  static const Duration _updateInterval = Duration(seconds: 15);

  DiscordRPC? _rpc;
  bool _isConnected = false;
  bool _isConnecting = false;
  int _retryDelay = 1;
  Timer? _reconnectTimer;
  Timer? _updateTimer;

  TrackMetadata? _currentMetadata;
  PlaybackState _currentState = PlaybackState.stopped;
  DateTime? _playbackStartTime;

  Future<void> initialize() async {
    if (_isConnecting || _isConnected) return;

    _isConnecting = true;

    try {
      _rpc = DiscordRPC(applicationId: _applicationId);
      _rpc!.start(autoRegister: true);
      _isConnected = true;
      _isConnecting = false;
      _retryDelay = 1;

      if (_currentMetadata != null && _currentState == PlaybackState.playing) {
        _updatePresence();
      }

      _startPeriodicUpdates();
    } catch (e) {
      _isConnected = false;
      _isConnecting = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: _retryDelay), () {
      _retryDelay = (_retryDelay * 2).clamp(1, _maxRetryDelay);
      initialize();
    });
  }

  void _startPeriodicUpdates() {
    _updateTimer?.cancel();
    _updateTimer = Timer.periodic(_updateInterval, (_) {
      if (_isConnected &&
          _currentMetadata != null &&
          _currentState == PlaybackState.playing) {
        _updatePresence();
      }
    });
  }

  Future<void> updateMetadata(
    TrackMetadata metadata,
    PlaybackState state,
  ) async {
    _currentMetadata = metadata;
    _currentState = state;

    if (state == PlaybackState.playing && _playbackStartTime == null) {
      _playbackStartTime = DateTime.now();
    } else if (state != PlaybackState.playing) {
      _playbackStartTime = null;
    }

    if (!_isConnected) {
      if (!_isConnecting) initialize();
      return;
    }

    if (state == PlaybackState.stopped || state == PlaybackState.paused) {
      clearPresence();
    } else {
      _updatePresence();
    }
  }

  void _updatePresence() {
    if (!_isConnected || _rpc == null || _currentMetadata == null) {
      return;
    }

    try {
      final metadata = _currentMetadata!;
      final now = DateTime.now();

      int? startTimestamp;
      int? endTimestamp;

      if (_playbackStartTime != null && metadata.duration != null) {
        final elapsed = metadata.position ?? Duration.zero;
        final remaining = metadata.duration! - elapsed;

        startTimestamp = _playbackStartTime!.millisecondsSinceEpoch;
        endTimestamp = now.add(remaining).millisecondsSinceEpoch;
      }

      _rpc!.updatePresence(
        DiscordPresence(
          details: metadata.title,
          state: 'by ${metadata.artist}',
          largeImageKey: metadata.artworkUrl ?? 'default',
          largeImageText: metadata.album ?? metadata.title,
          startTimeStamp: startTimestamp,
          endTimeStamp: endTimestamp,
        ),
      );
    } catch (e) {
      _handleConnectionError();
    }
  }

  void clearPresence() {
    if (!_isConnected || _rpc == null) return;

    try {
      _rpc!.clearPresence();
      _playbackStartTime = null;
    } catch (e) {
      _handleConnectionError();
    }
  }

  void _handleConnectionError() {
    _isConnected = false;
    _updateTimer?.cancel();
    _scheduleReconnect();
  }

  void dispose() {
    _reconnectTimer?.cancel();
    _updateTimer?.cancel();

    if (_isConnected && _rpc != null) {
      try {
        _rpc!.shutDown();
      } catch (e) {
        // Ignore shutdown errors
      }
    }

    _rpc = null;
    _isConnected = false;
    _isConnecting = false;
  }
}
