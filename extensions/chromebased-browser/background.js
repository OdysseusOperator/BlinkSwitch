// Screeny Tab Tracker - Background Service Worker
// Monitors all tabs and syncs with Screeny API

// Configuration
const API_BASE_URL = 'http://localhost:5555/screenassign';
const UPDATE_INTERVAL = 2000; // 2 seconds
const COMMAND_POLL_INTERVAL = 500; // 500ms for responsive tab switching
const PING_TIMEOUT = 5000; // 5 seconds
const API_HEALTH_CHECK_INTERVAL = 20000; // Check API health every 20 seconds

let isApiAvailable = false;
let updateTimer = null;
let commandPollTimer = null;
let healthCheckTimer = null;

// Detect browser name
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

const BROWSER_NAME = getBrowserName();
console.log(`Screeny Tab Tracker starting for ${BROWSER_NAME}`);

// Check if API is available
async function checkApiHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), PING_TIMEOUT);
    
    console.log(`Checking API health at ${API_BASE_URL}/health...`);
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    isApiAvailable = response.ok;
    
    if (isApiAvailable) {
      console.log('API is available');
    } else {
      console.log(`API returned status ${response.status}`);
    }
  } catch (error) {
    isApiAvailable = false;
    console.log('API not available:', error.message);
  }
  return isApiAvailable;
}

// Get all tabs from all windows
async function getAllTabs() {
  const windows = await chrome.windows.getAll({ populate: true });
  const allTabs = [];
  
  for (const window of windows) {
    for (const tab of window.tabs) {
      allTabs.push({
        id: tab.id,
        windowId: tab.windowId,
        title: tab.title || '(untitled)',
        url: tab.url || '',
        favIconUrl: tab.favIconUrl || '',
        active: tab.active,
        pinned: tab.pinned,
        index: tab.index,
        audible: tab.audible || false
      });
    }
  }
  
  return allTabs;
}

// Send tabs to Flask API
async function sendTabsToApi() {
  if (!isApiAvailable) {
    console.log('Skipping tab send - API not available');
    return;
  }
  
  try {
    const tabs = await getAllTabs();
    console.log(`Sending ${tabs.length} tabs to API...`);
    
    const payload = {
      timestamp: Date.now(),
      chrome_pid: chrome.runtime.id, // Unique per extension instance
      browser_name: BROWSER_NAME,
      tabs: tabs
    };
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), PING_TIMEOUT);
    
    const response = await fetch(`${API_BASE_URL}/browser-tabs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      console.error('Failed to send tabs:', response.statusText);
      isApiAvailable = false;
    } else {
      console.log(`Successfully sent ${tabs.length} tabs`);
    }
  } catch (error) {
    console.error('Error sending tabs:', error.message);
    isApiAvailable = false;
  }
}

// Poll for activation commands from API
async function checkForActivationCommands() {
  if (!isApiAvailable) {
    return;
  }
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), PING_TIMEOUT);
    
    const response = await fetch(`${API_BASE_URL}/chrome-commands`, {
      method: 'GET',
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      const data = await response.json();
      const commands = data.commands || [];
      
      for (const cmd of commands) {
        if (cmd.action === 'activateTab' && cmd.tabId) {
          console.log(`Activating tab ${cmd.tabId}`);
          
          // Activate the tab
          chrome.tabs.update(cmd.tabId, { active: true }, (tab) => {
            if (chrome.runtime.lastError) {
              console.error('Tab activation failed:', chrome.runtime.lastError);
            } else if (tab) {
              // Also focus the window
              chrome.windows.update(tab.windowId, { focused: true });
              console.log(`Tab ${cmd.tabId} activated successfully`);
            }
            
            // Acknowledge command (always, even on failure)
            fetch(`${API_BASE_URL}/chrome-commands/${cmd.id}`, {
              method: 'DELETE'
            }).catch(err => console.error('Failed to acknowledge command:', err));
          });
        }
      }
    }
  } catch (error) {
    console.error('Error checking commands:', error.message);
  }
}

// Start periodic tab updates
function startUpdates() {
  stopUpdates(); // Clear any existing timer
  
  // Send immediately
  if (isApiAvailable) {
    sendTabsToApi();
  }
  
  // Then set up periodic updates
  updateTimer = setInterval(async () => {
    if (isApiAvailable) {
      await sendTabsToApi();
    }
  }, UPDATE_INTERVAL);
}

function stopUpdates() {
  if (updateTimer) {
    clearInterval(updateTimer);
    updateTimer = null;
  }
}

// Start command polling
function startCommandPolling() {
  stopCommandPolling();
  
  commandPollTimer = setInterval(async () => {
    if (isApiAvailable) {
      await checkForActivationCommands();
    }
  }, COMMAND_POLL_INTERVAL);
}

function stopCommandPolling() {
  if (commandPollTimer) {
    clearInterval(commandPollTimer);
    commandPollTimer = null;
  }
}

// Start periodic API health checks
function startHealthChecks() {
  stopHealthChecks();
  
  healthCheckTimer = setInterval(async () => {
    await checkApiHealth();
  }, API_HEALTH_CHECK_INTERVAL);
}

function stopHealthChecks() {
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer);
    healthCheckTimer = null;
  }
}

// Event listeners for tab changes (send updates immediately)
chrome.tabs.onCreated.addListener(() => {
  if (isApiAvailable) sendTabsToApi();
});

chrome.tabs.onRemoved.addListener(() => {
  if (isApiAvailable) sendTabsToApi();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only send on title or URL changes to avoid spam
  if (changeInfo.title || changeInfo.url) {
    if (isApiAvailable) sendTabsToApi();
  }
});

chrome.tabs.onActivated.addListener(() => {
  if (isApiAvailable) sendTabsToApi();
});

chrome.windows.onFocusChanged.addListener(() => {
  if (isApiAvailable) sendTabsToApi();
});

// Initialize on extension load
async function initialize() {
  console.log(`${BROWSER_NAME} Tab Tracker initializing...`);
  
  // Check API health first
  const apiHealthy = await checkApiHealth();
  console.log(`API health check result: ${apiHealthy}`);
  
  // Start all periodic tasks
  startUpdates();
  startCommandPolling();
  startHealthChecks();
  
  console.log(`${BROWSER_NAME} Tab Tracker started (API available: ${isApiAvailable})`);
}

// Run initialization
initialize();
