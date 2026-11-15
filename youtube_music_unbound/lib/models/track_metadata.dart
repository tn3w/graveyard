class TrackMetadata {
  final String title;
  final String artist;
  final String? album;
  final String? artworkUrl;
  final Duration? duration;
  final Duration? position;

  const TrackMetadata({
    required this.title,
    required this.artist,
    this.album,
    this.artworkUrl,
    this.duration,
    this.position,
  });

  factory TrackMetadata.fromJson(Map<String, dynamic> json) {
    return TrackMetadata(
      title: json['title'] as String? ?? 'Unknown Title',
      artist: json['artist'] as String? ?? 'Unknown Artist',
      album: json['album'] as String?,
      artworkUrl: json['artworkUrl'] as String?,
      duration: json['duration'] != null
          ? Duration(seconds: (json['duration'] as num).toInt())
          : null,
      position: json['position'] != null
          ? Duration(seconds: (json['position'] as num).toInt())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'artist': artist,
      'album': album,
      'artworkUrl': artworkUrl,
      'duration': duration?.inSeconds,
      'position': position?.inSeconds,
    };
  }

  TrackMetadata copyWith({
    String? title,
    String? artist,
    String? album,
    String? artworkUrl,
    Duration? duration,
    Duration? position,
  }) {
    return TrackMetadata(
      title: title ?? this.title,
      artist: artist ?? this.artist,
      album: album ?? this.album,
      artworkUrl: artworkUrl ?? this.artworkUrl,
      duration: duration ?? this.duration,
      position: position ?? this.position,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is TrackMetadata &&
        other.title == title &&
        other.artist == artist &&
        other.album == album &&
        other.artworkUrl == artworkUrl &&
        other.duration == duration &&
        other.position == position;
  }

  @override
  int get hashCode {
    return Object.hash(title, artist, album, artworkUrl, duration, position);
  }
}
