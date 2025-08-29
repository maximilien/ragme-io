document.addEventListener('DOMContentLoaded', function() {
  const captureButton = document.getElementById('captureButton');
  const statusDiv = document.getElementById('status');

  // Configuration
  const RAGME_API_URL = 'http://localhost:8021'; //TODO:Update this with your actual API URL

  function showStatus(message, isError = false) {
    statusDiv.textContent = message;
    statusDiv.className = isError ? 'error' : 'success';
  }

  async function captureCurrentPage() {
    try {
      // Get the current active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab) {
        throw new Error('No active tab found');
      }

      // Send the URL to the RagMe API
      const response = await fetch(`${RAGME_API_URL}/add-urls`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          urls: [tab.url]
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      showStatus(`Successfully captured: ${tab.url}`);
    } catch (error) {
      showStatus(`Error: ${error.message}`, true);
    }
  }

  captureButton.addEventListener('click', captureCurrentPage);
});