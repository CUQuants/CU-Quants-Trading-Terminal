# Logging System - Quick Start

## 🚀 Instant Access

**Press `Ctrl + Shift + D`** to toggle the debug panel!

Or open browser console (`F12`) to see all logs.

## What You'll See

### In Browser Console
```
[2025-12-25T10:30:45.123Z] [INFO] [UI] App: Application initialized
[2025-12-25T10:30:45.234Z] [INFO] [WebSocket] Initiating WebSocket connection
[2025-12-25T10:30:45.456Z] [INFO] [WebSocket] ✅ WebSocket connected successfully
[2025-12-25T10:30:45.567Z] [INFO] [WebSocket] Subscribing to ticker updates
[2025-12-25T10:30:45.789Z] [DEBUG] [UI] useMarketTicker: Ticker update received
```

### In Debug Panel
- Visual log viewer with color-coding
- Last 100 logs displayed
- Real-time updates every second
- Download logs as JSON
- Clear logs button

## Log Categories

| Category | Color | What It Logs |
|----------|-------|--------------|
| **API** | Blue | Kraken API requests, responses, rate limiting |
| **WebSocket** | Blue | Connections, subscriptions, messages |
| **UI** | Blue | Components, routes, user interactions |

## Log Levels

| Level | When Used | Production |
|-------|-----------|------------|
| DEBUG | Verbose details | Hidden ❌ |
| INFO | Normal operations | Shown ✅ |
| WARN | Potential issues | Shown ✅ |
| ERROR | Failures | Shown ✅ |

## Common Debug Scenarios

### WebSocket Not Connecting?
Look for:
```
[ERROR] [WebSocket] WebSocket error occurred
```
**Fix:** Check network connection

### API Credentials Invalid?
Look for:
```
[ERROR] [API] API request returned errors { errors: ["EAPI:Invalid key"] }
```
**Fix:** Update credentials in Settings

### Rate Limited?
Look for:
```
[WARN] [API] Rate limit reached, waiting 1500ms
```
**Fix:** This is normal, system auto-throttles

### No Market Data?
Look for:
```
[INFO] [UI] MarketTicker: Ticker data updated { tickerCount: 0 }
```
**Fix:** Wait for WebSocket reconnection

## Export Logs

1. Press `Ctrl + Shift + D` to open debug panel
2. Click "Download" button
3. Share the JSON file for support

## Files Modified

- ✅ **src/utils/logger.ts** - Core logging utility
- ✅ **src/components/DebugPanel/** - Visual debug panel
- ✅ **src/services/krakenAPI.ts** - API logging
- ✅ **src/services/krakenWebSocket.ts** - WebSocket logging
- ✅ **src/hooks/useMarketTicker.ts** - Hook logging
- ✅ **src/components/MarketTicker/** - Component logging
- ✅ **src/pages/SettingsPage.tsx** - Settings logging
- ✅ **src/App.tsx** - Route logging

## Full Documentation

See **LOGGING_GUIDE.md** for complete details.

---

**That's it! Start the app and press `Ctrl + Shift + D` to see it in action! 🎉**
