# Logging System Summary

## What Was Added

Comprehensive logging has been added throughout the entire trading terminal application for debugging and monitoring.

## Files Created/Modified

### New Files
1. **src/utils/logger.ts** - Centralized logging utility with categorized loggers
2. **src/components/DebugPanel/DebugPanel.tsx** - Visual debug panel component
3. **src/components/DebugPanel/DebugPanel.module.css** - Styling for debug panel
4. **LOGGING_GUIDE.md** - Complete documentation

### Modified Files
1. **src/services/krakenAPI.ts** - Added API request/response logging
2. **src/services/krakenWebSocket.ts** - Added WebSocket connection/message logging
3. **src/hooks/useMarketTicker.ts** - Added hook lifecycle logging
4. **src/components/MarketTicker/MarketTicker.tsx** - Added component state logging
5. **src/pages/SettingsPage.tsx** - Added settings and connection logging
6. **src/App.tsx** - Added route change and app initialization logging
7. **src/vite-env.d.ts** - Fixed TypeScript definitions for import.meta.env

## Features

### 1. Console Logging
All logs appear in browser console with:
- Color-coded levels (DEBUG, INFO, WARN, ERROR)
- Timestamps
- Categories (API, WebSocket, UI)
- Structured data objects

### 2. Debug Panel
- **Toggle:** Press `Ctrl + Shift + D` or click 🐛 button
- **Features:**
  - Shows last 100 logs in real-time
  - Color-coded by level
  - Expandable data objects
  - Clear logs button
  - Download logs as JSON
- **Auto-updates** every second

### 3. Log Categories

**API Logs** (blue in console):
- Credential loading/setting
- Rate limiting
- Request/response logging
- Error handling

**WebSocket Logs** (blue in console):
- Connection status
- Subscription management
- Message receiving
- Reconnection attempts

**UI Logs** (blue in console):
- Component lifecycle
- Route changes
- State updates
- User interactions

## Usage

### In Browser
```javascript
// Open console (F12)
// Logs appear automatically

// Toggle debug panel
// Press: Ctrl + Shift + D

// Download logs
// Click "Download" in debug panel
```

### In Code
```typescript
import { apiLogger, wsLogger, uiLogger, logger } from '../utils/logger'

// Use category-specific loggers
apiLogger.info('Something happened', { data })
wsLogger.warn('Warning message', { details })
uiLogger.debug('Debug info', { state })

// Or use main logger with custom category
logger.error('MyCategory', 'Error occurred', error)
```

## Log Levels

- **DEBUG** - Only in development, verbose details
- **INFO** - General information about operations
- **WARN** - Potential issues or warnings
- **ERROR** - Errors and exceptions

## What's Logged

### Application Startup
1. App initialization
2. Route loading
3. API credential loading
4. WebSocket connection
5. Component mounting

### During Operation
1. Every API request (public/private)
2. API rate limiting events
3. WebSocket messages
4. Subscription events
5. Component state changes
6. User interactions
7. Route changes

### Errors
1. API errors with full details
2. WebSocket connection failures
3. Credential validation issues
4. Parse errors
5. Network issues

## Performance

- Minimal overhead in production
- DEBUG logs disabled in production builds
- Log history limited to 1000 entries
- Native browser APIs used

## Security

- API credentials never logged in full
- Only lengths and existence checked
- Private data sanitized (shown as ***)
- Safe for sharing

## Next Steps

1. **Start the dev server:**
   ```bash
   npm run dev
   ```

2. **Open browser console (F12)**

3. **Enable debug panel:**
   - Press `Ctrl + Shift + D`
   - Or click 🐛 button in bottom-right

4. **Use the app and watch logs:**
   - Navigate between pages
   - Configure API keys in Settings
   - Watch market ticker connect
   - See all operations logged in real-time

5. **Report issues:**
   - Download logs as JSON
   - Share with development team

## Quick Reference

| Action | Shortcut |
|--------|----------|
| Toggle Debug Panel | `Ctrl + Shift + D` |
| Open Console | `F12` |
| Clear Logs | Click "Clear" in panel |
| Download Logs | Click "Download" in panel |

## Example Log Flow

When you visit the app, you'll see:
```
[INFO] [UI] App: Application initialized
[INFO] [UI] App: Route changed { path: "/" }
[INFO] [API] Loading API credentials from localStorage
[INFO] [UI] MarketTicker: Component mounted { pairCount: 14 }
[INFO] [WebSocket] Initiating WebSocket connection
[INFO] [WebSocket] ✅ WebSocket connected successfully (public)
[INFO] [WebSocket] Subscribing to ticker updates { pairs: [...] }
[DEBUG] [WebSocket] Ticker subscription request sent
[DEBUG] [UI] useMarketTicker: Ticker update received { pair: "XBT/USD" }
```

## Troubleshooting

**No logs appearing?**
- Check console is open (F12)
- Check console filters
- Enable debug panel (Ctrl + Shift + D)

**Too many logs?**
- Filter by category in console
- Adjust log levels
- Close debug panel

**Performance issues?**
- Clear log history
- Disable debug panel
- Check if in production mode

## Documentation

See **LOGGING_GUIDE.md** for complete documentation including:
- Detailed usage examples
- Common debugging scenarios
- Advanced filtering
- Production considerations
- Best practices
