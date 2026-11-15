(function() {
  'use strict';
  
  const AD_PROPERTIES = [
    'adPlacements',
    'adSlots', 
    'playerAds',
    'adBreakHeartbeatParams'
  ];

  const PLAYER_RESPONSE_AD_PROPERTIES = [
    'playerResponse.adPlacements',
    'playerResponse.playerAds',
    'playerResponse.adSlots'
  ];

  const URL_PATTERNS_TO_PRUNE = [
    /playlist\?list=/,
    /\/player(?!.*(get_drm_license))/,
    /watch\?[tv]=/,
    /get_watch\?/,
    /\/next\?/,
    /music\.youtube\.com/
  ];

  const AD_BLOCKING_SELECTORS = [
    '#offer-module',
    '#promotion-shelf',
    '#description-inner > ytd-merch-shelf-renderer',
    'ytd-rich-item-renderer:has(> #content > ytd-ad-slot-renderer)',
    'ytd-ad-slot-renderer',
    'ytd-banner-promo-renderer',
    '.ytd-player-legacy-desktop-watch-ads-renderer',
    '.ytp-ad-module',
    '.ytp-ad-overlay-container',
    '.ytp-ad-text-overlay',
    '.ytp-ad-skip-button-container',
    'ytmusic-promoted-sparkles-web-renderer',
    'ytmusic-statement-banner-renderer',
    'ytmusic-mealbar-promo-renderer',
    '.ytmusic-player-bar[is-ad]',
    'tp-yt-paper-dialog:has(ytmusic-survey-renderer)'
  ];

  const NETWORK_BLOCK_PATTERNS = [
    'youtube.com/pagead/',
    'youtube.com/ptracking',
    'youtube.com/api/stats/ads',
    'youtube.com/api/stats/atr',
    'youtube.com/youtubei/v1/player/ad_break',
    'youtube.com/get_midroll_',
    'googlesyndication.com',
    'googleads.g.doubleclick.net',
    'doubleclick.net',
    'google.com/pagead/',
    'googleadservices.com',
    'googletagmanager.com',
    'googletagservices.com',
    '/pagead/',
    '/ad_break',
    '/get_midroll_',
    'initplayback?source=youtube'
  ];
  
  const setConstantValues = () => {
    const defineProperty = (obj, path, value) => {
      const keys = path.split('.');
      let current = obj;
      
      for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        if (!(key in current)) {
          try {
            Object.defineProperty(current, key, {
              value: {},
              writable: true,
              configurable: true,
              enumerable: true
            });
          } catch (e) {
            current[key] = {};
          }
        }
        current = current[key];
      }
      
      const finalKey = keys[keys.length - 1];
      try {
        Object.defineProperty(current, finalKey, {
          get: () => value,
          set: () => {},
          configurable: false,
          enumerable: true
        });
      } catch (e) {}
    };

    try {
      Object.defineProperty(window, 'google_ad_status', {
        value: 1,
        writable: false,
        configurable: false
      });
    } catch (e) {}

    const adPropertiesToBlock = [
      'ytInitialPlayerResponse.adPlacements',
      'ytInitialPlayerResponse.adSlots',
      'ytInitialPlayerResponse.playerAds',
      'playerResponse.adPlacements'
    ];

    adPropertiesToBlock.forEach(prop => {
      defineProperty(window, prop, undefined);
    });
  };
  
  const pruneAdData = (data, deep = true) => {
    if (!data || typeof data !== 'object') return data;

    AD_PROPERTIES.forEach(prop => {
      if (prop in data) {
        delete data[prop];
      }
    });

    if (data.playerResponse) {
      AD_PROPERTIES.forEach(prop => {
        if (prop in data.playerResponse) {
          delete data.playerResponse[prop];
        }
      });
      
      if (data.playerResponse.streamingData?.serverAbrStreamingUrl) {
        delete data.playerResponse.streamingData.serverAbrStreamingUrl;
      }
    }

    if (deep) {
      for (const key in data) {
        if (data[key] && typeof data[key] === 'object') {
          pruneAdData(data[key], false);
        }
      }
    }

    return data;
  };

  const shouldPruneUrl = (url) => {
    if (!url || typeof url !== 'string') return false;
    return URL_PATTERNS_TO_PRUNE.some(pattern => pattern.test(url));
  };
  
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
    
    if (url && NETWORK_BLOCK_PATTERNS.some(pattern => url.includes(pattern))) {
      return new Response('{}', {
        status: 200,
        statusText: 'OK',
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (shouldPruneUrl(url)) {
      try {
        const clonedResponse = response.clone();
        const text = await clonedResponse.text();
        
        if (text) {
          let data = JSON.parse(text);
          data = pruneAdData(data);
          
          return new Response(JSON.stringify(data), {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers
          });
        }
      } catch (e) {
        return response;
      }
    }
    
    return response;
  };
  
  const originalXHROpen = XMLHttpRequest.prototype.open;
  const originalXHRSend = XMLHttpRequest.prototype.send;
  
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._adblock_url = url;
    return originalXHROpen.apply(this, [method, url, ...rest]);
  };
  
  XMLHttpRequest.prototype.send = function(...args) {
    const url = this._adblock_url;
    
    if (url && NETWORK_BLOCK_PATTERNS.some(pattern => url.includes(pattern))) {
      Object.defineProperty(this, 'status', { value: 200 });
      Object.defineProperty(this, 'statusText', { value: 'OK' });
      Object.defineProperty(this, 'responseText', { value: '{}' });
      Object.defineProperty(this, 'response', { value: '{}' });
      
      setTimeout(() => {
        this.dispatchEvent(new Event('load'));
        this.dispatchEvent(new Event('loadend'));
        if (this.onload) this.onload();
        if (this.onloadend) this.onloadend();
      }, 0);
      return;
    }
    
    if (shouldPruneUrl(url)) {
      const originalOnReadyStateChange = this.onreadystatechange;
      const self = this;
      
      this.onreadystatechange = function() {
        if (self.readyState === 4 && self.status === 200) {
          try {
            let data = JSON.parse(self.responseText);
            data = pruneAdData(data);
            const cleanedText = JSON.stringify(data);
            
            Object.defineProperty(self, 'responseText', {
              writable: true,
              value: cleanedText
            });
            Object.defineProperty(self, 'response', {
              writable: true,
              value: cleanedText
            });
          } catch (e) {}
        }
        
        if (originalOnReadyStateChange) {
          return originalOnReadyStateChange.apply(this, arguments);
        }
      };
    }
    
    return originalXHRSend.apply(this, args);
  };
  
  const originalStringify = JSON.stringify;
  JSON.stringify = function(value, replacer, space) {
    const result = originalStringify.call(this, value, replacer, space);
    
    if (result && typeof result === 'string') {
      let modified = result.replace(
        /"clientScreen":"WATCH"/g,
        '"clientScreen":"ADUNIT"'
      );
      
      if (modified.includes('isWebNativeShareAvailable":true}}')) {
        modified = modified.replace(
          'isWebNativeShareAvailable":true}}',
          'isWebNativeShareAvailable":true},"clientScreen":"ADUNIT"}'
        );
      }
      
      return modified;
    }
    
    return result;
  };
  
  const originalSetTimeout = window.setTimeout;
  window.setTimeout = function(callback, delay, ...args) {
    if (delay >= 15000 && delay <= 20000) {
      const callbackStr = callback?.toString?.() || '';
      if (callbackStr.includes('[native code]') || callbackStr.length < 50) {
        delay = Math.floor(delay * 0.001);
      }
    }
    return originalSetTimeout.call(this, callback, delay, ...args);
  };
  
  const injectAdBlockCSS = () => {
    const css = AD_BLOCKING_SELECTORS.map(
      selector => `${selector} { display: none !important; visibility: hidden !important; height: 0 !important; width: 0 !important; }`
    ).join('\n');
    
    const style = document.createElement('style');
    style.id = 'ytm-adblock-css';
    style.textContent = css;
    
    if (document.head) {
      document.head.appendChild(style);
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        document.head.appendChild(style);
      });
    }
  };
  
  const removeAdElements = () => {
    AD_BLOCKING_SELECTORS.forEach(selector => {
      try {
        document.querySelectorAll(selector).forEach(el => {
          el.style.display = 'none';
          el.style.visibility = 'hidden';
          el.remove();
        });
      } catch (e) {}
    });
  };
  
  let lastSkippedAdUrl = '';
  
  const getAdPlayer = () => {
    const moviePlayer = document.getElementById('movie_player');
    if (!moviePlayer) return null;

    const videoStream = moviePlayer.getElementsByClassName('video-stream');
    const adsModule = moviePlayer.getElementsByClassName('ytp-ad-module');

    if (videoStream.length && adsModule.length && adsModule[0].childElementCount > 0) {
      return videoStream[0];
    }
    return null;
  };

  const skipVideoAd = () => {
    const player = getAdPlayer();
    if (!player) return;
    
    if (!isFinite(player.duration)) return;
    if (player.src === lastSkippedAdUrl) return;
    
    player.currentTime = player.duration - 0.1;
    player.playbackRate = 16;
    lastSkippedAdUrl = player.src;
  };

  const clickSkipButton = () => {
    const skipSelectors = [
      '.ytp-ad-skip-button',
      '.ytp-ad-skip-button-modern', 
      '.ytp-skip-ad-button',
      'button.ytp-ad-skip-button',
      '.ytp-ad-skip-button-slot button'
    ];
    
    for (const selector of skipSelectors) {
      const button = document.querySelector(selector);
      if (button && button.offsetParent !== null) {
        button.click();
        return true;
      }
    }
    return false;
  };

  const handlePlayerAds = () => {
    try {
      const player = document.getElementById('movie_player');
      if (!player) return;
      
      const ytPlayer = player.getPlayer?.() || player;
      if (!ytPlayer) return;
      
      const playerResponse = ytPlayer.getPlayerResponse?.();
      if (!playerResponse) return;
      
      const adSlots = playerResponse.adSlots;
      if (!adSlots) return;
      
      adSlots.forEach(slot => {
        const triggers = slot?.adSlotRenderer?.fulfillmentContent
          ?.fulfilledLayout?.playerBytesAdLayoutRenderer
          ?.layoutExitSkipTriggers;
          
        if (triggers) {
          triggers.forEach(trigger => {
            ytPlayer.onAdUxClicked?.(
              'skip-button',
              trigger.skipRequestedTrigger?.triggeringLayoutId
            );
          });
        }
      });
    } catch (e) {}
  };
  
  const interceptInitialPlayerResponse = () => {
    try {
      if (window.ytInitialPlayerResponse) {
        AD_PROPERTIES.forEach(prop => {
          if (window.ytInitialPlayerResponse[prop]) {
            window.ytInitialPlayerResponse[prop] = undefined;
          }
        });
      }
    } catch (e) {}
  };
  
  const dismissIdlePopup = () => {
    const renderers = document.getElementsByTagName('ytmusic-you-there-renderer');
    if (renderers.length === 0) return;
    
    const renderer = renderers[0];
    if (!renderer.checkVisibility?.()) return;
    
    const button = renderer.querySelector('button');
    if (button) button.click();
  };
  
  const checkAds = () => {
    removeAdElements();
    interceptInitialPlayerResponse();
    clickSkipButton();
    skipVideoAd();
    handlePlayerAds();
    dismissIdlePopup();
  };
  
  const setupMutationObserver = () => {
    const observer = new MutationObserver((mutations) => {
      let shouldCheck = false;
      
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          shouldCheck = true;
          
          mutation.addedNodes.forEach(node => {
            if (node.tagName === 'SCRIPT' || node.tagName === 'IFRAME') {
              const src = node.src || node.getAttribute('src') || '';
              if (NETWORK_BLOCK_PATTERNS.some(p => src.includes(p))) {
                node.remove();
              }
            }
          });
        }
      }
      
      if (shouldCheck) {
        checkAds();
      }
    });
    
    if (document.body) {
      observer.observe(document.body, { childList: true, subtree: true });
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        observer.observe(document.body, { childList: true, subtree: true });
      });
    }
  };
  
  const SKIPPED_TAG = 'adblock_monitored';
  let checkInterval = null;
  
  const monitorVideo = (video) => {
    if (video.getAttribute(SKIPPED_TAG) === '1') return;
    video.setAttribute(SKIPPED_TAG, '1');
    
    const videoObserver = new MutationObserver((mutations) => {
      mutations.forEach(mutation => {
        if (mutation.attributeName === 'src') {
          checkAds();
        }
      });
    });
    
    videoObserver.observe(video, { attributes: true });
    
    video.addEventListener('play', () => {
      if (checkInterval) clearInterval(checkInterval);
      checkInterval = setInterval(checkAds, 500);
    });
    
    video.addEventListener('pause', () => {
      if (checkInterval) {
        clearInterval(checkInterval);
        checkInterval = null;
      }
      dismissIdlePopup();
    });
  };

  const findAndMonitorVideos = () => {
    const videos = document.querySelectorAll('video');
    videos.forEach(monitorVideo);
    
    setTimeout(findAndMonitorVideos, 2000);
  };
  
  const onNavigate = () => {
    lastSkippedAdUrl = '';
    interceptInitialPlayerResponse();
    removeAdElements();
    checkAds();
    findAndMonitorVideos();
  };
  
  setConstantValues();
  injectAdBlockCSS();
  setupMutationObserver();
  
  try {
    if (window.navigation?.addEventListener) {
      window.navigation.addEventListener('navigate', onNavigate);
    }
  } catch (e) {}
  
  window.addEventListener('yt-navigate-finish', onNavigate);
  window.addEventListener('popstate', onNavigate);
  
  const originalPushState = history.pushState;
  const originalReplaceState = history.replaceState;
  
  history.pushState = function() {
    originalPushState.apply(this, arguments);
    setTimeout(onNavigate, 100);
  };
  
  history.replaceState = function() {
    originalReplaceState.apply(this, arguments);
    setTimeout(onNavigate, 100);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onNavigate);
  } else {
    onNavigate();
  }
  
  setInterval(checkAds, 1000);
})();
