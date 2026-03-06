// content.js

let mouseData = [];

const recordEvent = (type, event) => {
  const { clientX, clientY, pageX, pageY } = event;
  const timestamp = Date.now();
  mouseData.push({ type, x: clientX, y: clientY, pageX, pageY, timestamp });

  // Send the data to background script periodically
  if (mouseData.length % 100 === 0) {
    chrome.runtime.sendMessage({ action: "storeMouseData", data: mouseData });
    mouseData = []; // Clear the local data after sending
  }
};

document.addEventListener("mousemove", (event) => recordEvent("MOVE", event));
document.addEventListener("click", (event) => recordEvent("CLICK", event));
document.addEventListener("scroll", (event) => {
  const timestamp = Date.now();
  mouseData.push({ type: "SCROLL", x: window.scrollX, y: window.scrollY, timestamp });
  if (mouseData.length % 100 === 0) {
    chrome.runtime.sendMessage({ action: "storeMouseData", data: mouseData });
    mouseData = []; // Clear the local data after sending
  }
});

// Send remaining data when the page is unloaded
window.addEventListener("beforeunload", () => {
  if (mouseData.length > 0) {
    chrome.runtime.sendMessage({ action: "storeMouseData", data: mouseData });
  }
});
