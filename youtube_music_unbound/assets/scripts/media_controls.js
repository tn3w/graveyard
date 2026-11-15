(function() {
  function clickButton(selector) {
    const button = document.querySelector(selector);
    if (button) {
      button.click();
      return true;
    }
    return false;
  }

  function executeMediaCommand(command) {
    try {
      switch (command) {
        case 'playpause':
          return clickButton('ytmusic-player-bar #play-pause-button button');
        
        case 'next':
          return clickButton('ytmusic-player-bar .next-button button');
        
        case 'previous':
          return clickButton('ytmusic-player-bar .previous-button button');
        
        case 'stop':
          const video = document.querySelector('video');
          if (video) {
            video.pause();
            video.currentTime = 0;
            return true;
          }
          return false;
        
        default:
          console.warn('Unknown media command:', command);
          return false;
      }
    } catch (error) {
      console.error('Media command error:', error);
      return false;
    }
  }

  window.executeMediaCommand = executeMediaCommand;

  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', () => {
      executeMediaCommand('play');
    });

    navigator.mediaSession.setActionHandler('pause', () => {
      executeMediaCommand('pause');
    });

    navigator.mediaSession.setActionHandler('previoustrack', () => {
      executeMediaCommand('previous');
    });

    navigator.mediaSession.setActionHandler('nexttrack', () => {
      executeMediaCommand('next');
    });

    navigator.mediaSession.setActionHandler('stop', () => {
      executeMediaCommand('stop');
    });
  }
})();
