import 'package:flutter_test/flutter_test.dart';
import 'package:youtube_music_unbound/services/system_tray_manager.dart';
import 'package:youtube_music_unbound/models/playback_state.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('SystemTrayManager', () {
    test('should create instance with callbacks', () {
      final manager = SystemTrayManager(
        onMediaCommand: (command) {},
        onExit: () {},
      );

      expect(manager, isNotNull);
    });

    test('should update playback state without errors', () async {
      final manager = SystemTrayManager(
        onMediaCommand: (command) {},
        onExit: () {},
      );

      await manager.updatePlaybackState(PlaybackState.playing);
      await manager.updatePlaybackState(PlaybackState.paused);

      expect(true, isTrue);
    });
  });
}
