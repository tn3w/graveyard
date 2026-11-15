(function() {
  let lastMetadata = null;
  let lastPlaybackState = null;
  let pollingInterval = null;

  function extractMetadata() {
    try {
      let title = null;
      let artist = null;
      let album = null;
      let artworkUrl = null;
      let duration = null;
      let position = null;

      if ('mediaSession' in navigator && navigator.mediaSession.metadata) {
        const metadata = navigator.mediaSession.metadata;
        title = metadata.title || null;
        artist = metadata.artist || null;
        album = metadata.album || null;
        
        if (metadata.artwork && metadata.artwork.length > 0) {
          artworkUrl = metadata.artwork[0].src || null;
        }
      }

      const videoElement = document.querySelector('video');
      if (videoElement) {
        duration = Math.floor(videoElement.duration) || null;
        position = Math.floor(videoElement.currentTime) || null;
      }

      if (!title && !artist) {
        const titleElement = document.querySelector(
          'ytmusic-player-bar .title.ytmusic-player-bar'
        );
        const bylineElement = document.querySelector(
          'ytmusic-player-bar .byline.ytmusic-player-bar'
        );
        const imageElement = document.querySelector(
          'ytmusic-player-bar img.image'
        );

        title = titleElement?.textContent?.trim() || null;
        const byline = bylineElement?.textContent?.trim() || null;
        artworkUrl = artworkUrl || imageElement?.src || null;

        if (byline) {
          const parts = byline.split('•').map(p => p.trim());
          artist = parts[0] || null;
          album = album || parts[1] || null;
        }
      }

      if (!title || !artist) {
        return null;
      }

      return {
        title: title,
        artist: artist,
        album: album,
        artworkUrl: artworkUrl,
        duration: duration,
        position: position,
      };
    } catch (error) {
      console.error('Metadata extraction error:', error);
      return null;
    }
  }

  function extractPlaybackState() {
    try {
      const videoElement = document.querySelector('video');
      if (!videoElement) {
        return 'stopped';
      }

      if (videoElement.paused) {
        return 'paused';
      } else if (videoElement.readyState < 3) {
        return 'buffering';
      } else {
        return 'playing';
      }
    } catch (error) {
      console.error('Playback state extraction error:', error);
      return 'stopped';
    }
  }

  function hasMetadataChanged(newMetadata) {
    if (!lastMetadata && newMetadata) return true;
    if (!newMetadata) return false;
    
    return (
      lastMetadata.title !== newMetadata.title ||
      lastMetadata.artist !== newMetadata.artist ||
      lastMetadata.album !== newMetadata.album ||
      lastMetadata.artworkUrl !== newMetadata.artworkUrl
    );
  }

  function pollMetadata() {
    const metadata = extractMetadata();
    
    if (metadata && hasMetadataChanged(metadata)) {
      lastMetadata = metadata;
      
      if (window.flutter_inappwebview) {
        window.flutter_inappwebview.callHandler(
          'metadataUpdate',
          metadata
        );
      }
    }

    const playbackState = extractPlaybackState();
    if (playbackState !== lastPlaybackState) {
      lastPlaybackState = playbackState;
      
      if (window.flutter_inappwebview) {
        window.flutter_inappwebview.callHandler(
          'playbackStateUpdate',
          { state: playbackState }
        );
      }
    }
  }

  function startPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    pollingInterval = setInterval(pollMetadata, 1000);
    pollMetadata();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startPolling);
  } else {
    startPolling();
  }
})();
