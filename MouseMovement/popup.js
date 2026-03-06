// popup.js

document.addEventListener("DOMContentLoaded", () => {
    const dataCountElement = document.getElementById("dataCount");
    const downloadButton = document.getElementById("downloadBtn");
  
    // Request stored data
    chrome.runtime.sendMessage({ action: "getStoredData" }, (response) => {
      const mouseData = response;
      dataCountElement.textContent = `Data points: ${mouseData.length}`;
    });
  
    downloadButton.addEventListener("click", () => {
      chrome.runtime.sendMessage({ action: "getStoredData" }, (response) => {
        const mouseData = response;
        const blob = new Blob([JSON.stringify(mouseData)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "mouse_data.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      });
    });
  });
  