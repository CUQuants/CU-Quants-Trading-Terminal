# Logging & Debugging Guide

## Overview

The trading terminal includes comprehensive logging throughout the application to help with debugging and monitoring. All logs are displayed in both the browser console and in a built-in debug panel.

## Quick Start

### Enable Debug Panel

Press **Ctrl + Shift + D** to toggle the debug panel.

Or click the **🐛 Debug** button in the bottom-right corner.

### View Console Logs

Open browser DevTools (F12) and check the Console tab. Logs are color-coded by level:
- **DEBUG** (gray) - Detailed debugging information
- **INFO** (blue) - General information
- **WARN** (orange) - Warnings and potential issues
- **ERROR** (red) - Errors and exceptions

## Log Categories

### API Logs
All Kraken API interactions are logged:

```typescript
import { apiLogger } from './utils/logger'

// Example logs you'll see:
// [INFO] [API] Making public API request { endpoint: "Ticker", data: {...} }
// [INFO] [API] Public API request successful { endpoint: "Ticker" }
// [ERROR] [API] API request returned errors { endpoint: "Balance", errors: [...] }
// [WARN] [API] Rate limit reached, waiting 1500ms
```

**What's Logged:**
- API credential loading/setting
- Rate limiting (when requests are throttled)
- Every API request (public and private)
- API responses (success/error)
- Request parameters (sanitized for security)

### WebSocket Logs
Real-time connection and data stream logs:

```typescript
import { wsLogger } from './utils/logger'

// Example logs you'll see:
// [INFO] [WebSocket] Initiating WebSocket connection { url: "wss://ws.kraken.com" }
// [INFO] [WebSocket] ✅ WebSocket connected successfully (public)
// [INFO] [WebSocket] Subscribing to ticker updates { pairs: [...], pairCount: 14 }
// [DEBUG] [WebSocket] WebSocket message received { dataType: "array", length: 450 }
// [WARN] [WebSocket] WebSocket connection closed
// [ERROR] [WebSocket] WebSocket error occurred
```

**What's Logged:**
- Connection attempts and status
- Subscription requests
- Incoming messages (with size info)
- Reconnection attempts
- Authentication flow (for private feeds)

### UI Logs
Component lifecycle and user interactions:

```typescript
import { uiLogger } from './utils/logger'

// Example logs you'll see:
// [INFO] [UI] App: Application initialized
// [INFO] [UI] App: Route changed { path: "/trading" }
// [INFO] [UI] MarketTicker: Component mounted { pairCount: 14 }
// [INFO] [UI] MarketTicker: Connection status changed { isConnected: true }
// [DEBUG] [UI] MarketTicker: Ticker data updated { tickerCount: 14, hasData: true }
// [INFO] [UI] useMarketTicker: Ticker update received { pair: "XBT/USD", last: "43250.50" }
```

**What's Logged:**
- Component mounting/unmounting
- Route changes
- State updates
- User interactions
- Data flow through hooks

## Using the Logger

### In Your Code

```typescript
import { logger, apiLogger, wsLogger, uiLogger } from '../utils/logger'

// Use category-specific loggers
apiLogger.info('API call successful', { data })
wsLogger.warn('Connection unstable', { attempts })
uiLogger.debug('Component rendered', { props })

// Or use the main logger with custom categories
logger.info('MyCategory', 'Something happened', { details })
logger.error('MyCategory', 'Error occurred', error)
```

### Log Levels

```typescript
// DEBUG - Only in development mode
logger.debug('Category', 'Detailed info for debugging', data)

// INFO - General information
logger.info('Category', 'Normal operation', data)

// WARN - Potential issues
logger.warn('Category', 'Warning message', data)

// ERROR - Errors and exceptions
logger.error('Category', 'Error message', error)
```

## Debug Panel Features

### Actions

1. **Clear** - Clear all logs from memory and display
2. **Download** - Download logs as JSON file
3. **Close** - Hide the debug panel

### Display

- Shows last 100 logs (most recent first)
- Color-coded by level
- Timestamps in local time
- Expandable data objects
- Auto-updates every second

### Keyboard Shortcuts

- **Ctrl + Shift + D** - Toggle debug panel

## Common Debugging Scenarios

### WebSocket Not Connecting

Check logs for:
```
[ERROR] [WebSocket] WebSocket error occurred
[WARN] [WebSocket] Connection already in progress
```

**Solution:** Ensure you're not behind a firewall blocking WebSocket connections.

### API Credentials Invalid

Check logs for:
```
[ERROR] [API] Cannot make private request - credentials not configured
[ERROR] [API] API request returned errors { errors: ["EAPI:Invalid key"] }
```

**Solution:** Go to Settings page and verify your API key and secret.

### Rate Limiting

Check logs for:
```
[WARN] [API] Rate limit reached, waiting 1500ms
```

**Solution:** This is normal. The system automatically throttles requests to comply with Kraken's limits.

### No Market Data

Check logs for:
```
[INFO] [UI] MarketTicker: Ticker data updated { tickerCount: 0, hasData: false }
[WARN] [WebSocket] WebSocket connection closed
```

**Solution:** WebSocket might have disconnected. Wait for automatic reconnection or refresh the page.

## Log Persistence

### Browser Console
- Logs are written to console in real-time
- Persist until page refresh
- Can be filtered in DevTools

### Debug Panel
- Stores last 1000 logs in memory
- Cleared on page refresh
- Can download as JSON file

### Download Format

```json
[
  {
    "timestamp": "2025-12-25T10:30:45.123Z",
    "level": "INFO",
    "category": "API",
    "message": "API credentials loaded successfully",
    "data": {
      "hasApiKey": true,
      "hasApiSecret": true
    }
  }
]
```

## Production Considerations

### Environment-Based Logging

DEBUG logs only appear in development mode:

```typescript
// vite.config.ts determines the mode
// Development: import.meta.env.DEV = true
// Production: import.meta.env.DEV = false
```

In production builds:
- DEBUG logs are suppressed
- INFO, WARN, ERROR still logged
- Console output minimized

### Security Notes

- API credentials are never logged in full
- Only lengths and existence are logged
- Private data is marked as `***` in logs
- Consider removing debug panel in production

## Advanced Usage

### Export Logs for Support

1. Reproduce the issue
2. Open debug panel (Ctrl + Shift + D)
3. Click "Download"
4. Share the JSON file with support team

### Filter Logs in Console

```javascript
// In browser console, filter by category
console.log(logger.getHistory().filter(log => log.category === 'WebSocket'))

// Filter by level
console.log(logger.getHistory().filter(log => log.level === 'ERROR'))

// Filter by time range
console.log(logger.getHistory().filter(log => 
  new Date(log.timestamp) > new Date('2025-12-25T10:00:00')
))
```

### Clear History Programmatically

```javascript
// In browser console
logger.clearHistory()
```

## Monitoring Checklist

When the app starts, you should see:

1. ✅ `[INFO] [UI] App: Application initialized`
2. ✅ `[INFO] [UI] App: Route changed { path: "/" }`
3. ✅ `[INFO] [API] Loading API credentials from localStorage`
4. ✅ `[INFO] [WebSocket] Initiating WebSocket connection`
5. ✅ `[INFO] [WebSocket] ✅ WebSocket connected successfully (public)`
6. ✅ `[INFO] [UI] MarketTicker: Component mounted`
7. ✅ `[INFO] [WebSocket] Subscribing to ticker updates`
8. ✅ `[DEBUG] [UI] useMarketTicker: Ticker update received`

If any step fails, check the error logs for details.

## Performance Impact

- Minimal overhead in production (DEBUG disabled)
- Log history limited to 1000 entries
- Console output uses native browser APIs
- Debug panel updates only when open

## Troubleshooting

### Logs Not Appearing

1. Check browser console is open (F12)
2. Verify console filters aren't hiding logs
3. Check if debug panel is enabled (Ctrl + Shift + D)

### Too Many Logs

1. Close debug panel to reduce UI updates
2. Filter console by category or level
3. Adjust update interval in DebugPanel component

### Performance Issues

1. Clear log history: `logger.clearHistory()`
2. Disable debug panel
3. Check if DEBUG logs are being suppressed in production

## Best Practices

1. **Use Appropriate Levels**
   - DEBUG: Verbose details during development
   - INFO: Normal operations
   - WARN: Recoverable issues
   - ERROR: Failures requiring attention

2. **Include Context**
   - Always pass relevant data as the third parameter
   - Use object notation for clarity

3. **Category Naming**
   - Use existing categories when possible
   - Create new categories for distinct modules

4. **Sensitive Data**
   - Never log full API keys/secrets
   - Sanitize user data before logging

5. **Production**
   - Review logs before deployment
   - Consider disabling debug panel
   - Monitor for excessive logging
