// background.js

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "storeMouseData") {
      chrome.storage.local.get("mouseData", (result) => {
        let mouseData = result.mouseData || [];
        mouseData = mouseData.concat(message.data);
        chrome.storage.local.set({ mouseData: mouseData });
      });
    } else if (message.action === "getStoredData") {
      chrome.storage.local.get("mouseData", (result) => {
        sendResponse(result.mouseData || []);
      });
      return true; // Indicates that the response is sent asynchronously
    }
  });
  