enum MediaCommand { play, pause, playPause, next, previous, stop }

class PlaybackCommand {
  final MediaCommand command;
  final Map<String, dynamic>? params;

  const PlaybackCommand({required this.command, this.params});
}
