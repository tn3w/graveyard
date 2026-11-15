(function() {
  'use strict';
    
  const customCSS = `
    ytmusic-nav-bar {
      margin-top: 32px !important;
    }
    
    ytmusic-guide-renderer {
      margin-top: 32px !important;
    }
    
    #nav-bar-background.ytmusic-app-layout {
      padding-top: 32px !important;
    }
  `;
  
  function injectCSS() {
    const styleId = 'transparent-titlebar-styles';
    const existingStyle = document.getElementById(styleId);
    if (existingStyle) {
      existingStyle.remove();
    }
    
    const styleElement = document.createElement('style');
    styleElement.id = styleId;
    styleElement.textContent = customCSS;
    document.head.appendChild(styleElement);
  }
  
  injectCSS();
  
  const observer = new MutationObserver((mutations) => {
    const navOccurred = mutations.some(mutation => 
      mutation.type === 'childList' && 
      mutation.addedNodes.length > 0
    );
    
    if (navOccurred) {
      injectCSS();
    }
  });
  
  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    });
  }
})();
