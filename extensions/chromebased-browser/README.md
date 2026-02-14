# Screeny Tab Tracker - Browser Extension

This extension sends browser tab information to the Screeny window switcher, allowing you to switch between tabs across all browser windows using Alt+Space.

## Features

- Automatically detects browser type (Chrome, Edge, Vivaldi, Brave, Opera)
- Monitors all tabs across all browser windows
- Sends tab data to local Screeny API (localhost:5555)
- Supports tab activation from Screeny window switcher
- Privacy-focused: All data stays on your local machine

## Installation

1. **Open Extension Management Page:**
   - Chrome: Navigate to `chrome://extensions`
   - Edge: Navigate to `edge://extensions`
   - Vivaldi: Navigate to `vivaldi://extensions`
   - Brave: Navigate to `brave://extensions`

2. **Enable Developer Mode:**
   - Toggle the "Developer mode" switch in the top-right corner

3. **Load the Extension:**
   - Click "Load unpacked"
   - Navigate to and select this folder: `C:\dev\mytools\screeny\extensions\chromebased-browser`
   - The extension should now appear in your extensions list

4. **Verify Installation:**
   - Click the extension icon in your browser toolbar
   - You should see the Screeny Tab Tracker popup

## Usage

### Prerequisites

The Screeny API must be running for the extension to work:

```bash
cd C:\dev\mytools\screeny
start_assigner.bat
```

### Verification

1. **Check Extension Status:**
   - Click the extension icon
   - Status should show: "✓ Connected to Screeny API"
   - If disconnected, make sure the API is running

2. **Test Window Switcher:**
   - Open several tabs in your browser
   - Press `Alt+Space` to open Screeny window switcher
   - Your browser tabs should appear in the list
   - Type to filter, use arrow keys to select, press Enter to switch

## How It Works

1. **Tab Monitoring:**
   - Extension monitors all tabs using Chrome's `chrome.tabs` API
   - Tracks tab creation, removal, updates, and focus changes

2. **Data Synchronization:**
   - Sends tab data to `http://localhost:5555/screenassign/browser-tabs` every 2 seconds
   - Also sends updates immediately when tabs change

3. **Tab Activation:**
   - Extension polls `http://localhost:5555/screenassign/chrome-commands` every 500ms
   - When you select a tab in Screeny, it queues an activation command
   - Extension receives the command and activates the tab

## Troubleshooting

### Extension shows "Not connected"

**Solution:** Start the Screeny API service:
```bash
cd C:\dev\mytools\screeny
start_assigner.bat
```

Verify the API is running by visiting http://localhost:5555/screenassign/health in your browser.

### Tabs not appearing in Screeny window switcher

1. Check extension popup shows correct tab count
2. Verify extension is sending data (check extension console):
   - Right-click extension icon → "Inspect popup" → Console tab
   - Should see messages about API availability
3. Try refreshing the extension:
   - Go to browser extensions page
   - Click the reload icon on the Screeny Tab Tracker extension

### Tab activation doesn't work

1. Make sure the tab still exists (wasn't closed)
2. Check browser console for errors (F12)
3. Reload the extension

### Extension console shows errors

**Common error: "Failed to fetch"**
- This means the API isn't running or isn't reachable
- Start `start_assigner.bat` and wait a few seconds

**Error: "API not available"**
- The API health check failed
- Verify nothing else is using port 5555
- Check Windows Firewall isn't blocking localhost connections

## Privacy & Security

- **Local Only:** All data is sent to `localhost:5555` only
- **No External Servers:** No data leaves your computer
- **No Tracking:** Extension doesn't collect or store any personal data
- **Minimal Permissions:** Only requests `tabs` and `storage` permissions

## Technical Details

### Data Sent to API

```json
{
  "timestamp": 1706000000000,
  "chrome_pid": "extension_id_here",
  "browser_name": "Chrome",
  "tabs": [
    {
      "id": 123,
      "windowId": 1,
      "title": "GitHub Issues",
      "url": "https://github.com/...",
      "active": true,
      "pinned": false,
      "index": 0,
      "audible": false
    }
  ]
}
```

### Update Intervals

- Tab data sync: Every 2 seconds
- Command polling: Every 500ms
- API health check: Every 20 seconds
- Event-driven updates: Immediate (on tab changes)

### Data Retention

Tab data is stored in memory on the API server with a 10-second TTL (Time To Live). If the extension stops sending updates, the data is automatically cleaned up after 10 seconds.

## Support

For issues or questions, refer to the main Screeny documentation in `C:\dev\mytools\screeny\README.md`.

## Version History

### 1.0.0 (Current)
- Initial release
- Support for Chrome-based browsers (Chrome, Edge, Vivaldi, Brave, Opera)
- Real-time tab monitoring and synchronization
- Tab activation via window switcher
- Browser name detection
