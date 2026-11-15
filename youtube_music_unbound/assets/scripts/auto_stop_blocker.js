(() => {
  let lastActivity = Date.now();
  ['mousedown', 'keydown'].forEach((event) =>
    document.addEventListener(event, () => (lastActivity = Date.now()))
  );
  document.addEventListener(
    'yt-popup-opened',
    (event) =>
      event.detail?.nodeName === 'YTMUSIC-YOU-THERE-RENDERER' &&
      Date.now() - lastActivity > 3000 &&
      document.querySelector('ytmusic-popup-container')?.click()
  );
  new MutationObserver(() => {
    const video = document.querySelector('video');
    if (video && !video._ymuOverridden) {
      video._ymuOverridden = video.pause;
      video.pause = () => Date.now() - lastActivity < 3000 && video._ymuOverridden();
    }
  }).observe(document.body, { childList: true, subtree: true });
})();
