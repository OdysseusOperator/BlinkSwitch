// Screeny Tab Tracker - Popup UI Logic

const API_BASE_URL = 'http://localhost:5555/screenassign';
const API_TIMEOUT = 3000;

// Detect browser name (same logic as background.js)
function getBrowserName() {
  const userAgent = navigator.userAgent.toLowerCase();
  
  if (userAgent.includes('edg/')) {
    return 'Edge';
  } else if (userAgent.includes('vivaldi')) {
    return 'Vivaldi';
  } else if (userAgent.includes('brave')) {
    return 'Brave';
  } else if (userAgent.includes('opera') || userAgent.includes('opr/')) {
    return 'Opera';
  } else if (userAgent.includes('chrome')) {
    return 'Chrome';
  } else {
    return 'Chromium';
  }
}

async function updateStatus() {
  const statusDiv = document.getElementById('status');
  const tabCountDiv = document.getElementById('tabCount');
  const browserNameDiv = document.getElementById('browserName');
  
  // Show browser name
  browserNameDiv.textContent = getBrowserName();
  
  // Show checking status
  statusDiv.className = 'status checking';
  statusDiv.textContent = 'Checking connection...';
  
  try {
    // Check API health
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
    
    const response = await fetch(`${API_BASE_URL}/health`, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      statusDiv.className = 'status connected';
      statusDiv.textContent = '✓ Connected to Screeny API';
    } else {
      statusDiv.className = 'status disconnected';
      statusDiv.textContent = '✗ API Error';
    }
    
  } catch (error) {
    statusDiv.className = 'status disconnected';
    if (error.name === 'AbortError') {
      statusDiv.textContent = '✗ Connection timeout';
    } else {
      statusDiv.textContent = '✗ Not connected (API not running)';
    }
  }
  
  // Get tab count
  try {
    const tabs = await chrome.tabs.query({});
    tabCountDiv.textContent = `${tabs.length} tabs`;
  } catch (error) {
    tabCountDiv.textContent = 'Error counting tabs';
  }
}

// Set up event listeners
document.getElementById('testBtn').addEventListener('click', updateStatus);

// Run on popup open
updateStatus();
