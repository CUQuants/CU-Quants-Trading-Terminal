# API Credentials Required for Market Ticker

## What Changed

The MarketTicker component now checks for API credentials before attempting to connect to the WebSocket and display market data.

## Before

- Ticker tried to connect immediately on page load
- Showed "Connecting to market data..." even without API credentials
- Could cause errors or confusion for users who haven't set up their API yet

## After

**Without API Credentials:**
```
⚠️ Connect your API in Settings to view market data
```
(With a clickable link to Settings page)

**With API Credentials:**
- Normal ticker behavior with live market data
- Shows real-time prices for 14 trading pairs
- Connects to WebSocket automatically

## How It Works

### 1. Credential Check on Mount

```typescript
useEffect(() => {
  const checkCredentials = () => {
    const hasCredentials = krakenAPI.hasCredentials()
    setHasApiCredentials(hasCredentials)
  }
  
  checkCredentials()
  
  // Check every 2 seconds in case credentials are added
  const interval = setInterval(checkCredentials, 2000)
  
  return () => clearInterval(interval)
}, [])
```

### 2. Conditional Ticker Initialization

```typescript
// Only initialize ticker if API credentials exist
const shouldInitializeTicker = hasApiCredentials
const { tickers, isConnected } = useMarketTicker(
  shouldInitializeTicker ? TICKER_PAIRS : []
)
```

### 3. Show Warning Message

```typescript
if (!hasApiCredentials) {
  return (
    <div className={styles.tickerContainer}>
      <div className={styles.noCredentials}>
        <span className={styles.warningIcon}>⚠️</span>
        <span className={styles.warningText}>
          Connect your API in <Link to="/settings">Settings</Link> to view market data
        </span>
      </div>
    </div>
  )
}
```

### 4. Skip WebSocket Connection When No Pairs

```typescript
// In useMarketTicker hook
if (initialPairs.length === 0) {
  uiLogger.info('useMarketTicker: No pairs specified, skipping WebSocket connection')
  return
}
```

## User Flow

### Without API Credentials

1. User opens the app
2. Ticker shows: **"⚠️ Connect your API in Settings to view market data"**
3. User clicks "Settings" link
4. User enters API key and secret
5. User saves credentials
6. Ticker automatically detects credentials (within 2 seconds)
7. WebSocket connects and live data appears

### With API Credentials

1. User opens the app
2. Ticker immediately starts connecting
3. Live market data displays for all 14 pairs
4. Normal operation continues

## Features

✅ **Auto-detection** - Checks credentials every 2 seconds
✅ **No manual refresh** - Updates automatically when credentials added
✅ **Clear messaging** - User knows exactly what to do
✅ **Clickable link** - Direct navigation to Settings page
✅ **No errors** - Won't attempt WebSocket connection without credentials
✅ **Smooth transition** - When credentials added, seamlessly starts ticker

## Styling

The warning message is styled to match the terminal theme:

```css
.noCredentials {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background-color: var(--color-black);
}

.warningIcon {
  font-size: 16px;  /* ⚠️ emoji */
}

.warningText {
  color: var(--color-white);
  font-size: 13px;
  font-weight: 500;
}

.settingsLink {
  color: var(--color-blue);
  text-decoration: underline;
  font-weight: 600;
}

.settingsLink:hover {
  color: #0088ff;  /* Lighter blue on hover */
}
```

## Logging

Enhanced logging shows the credential check process:

```
[INFO] [UI] MarketTicker: Component mounted { pairCount: 14, hasApiCredentials: false }
[INFO] [UI] MarketTicker: API credentials check { hasCredentials: false }
[INFO] [UI] useMarketTicker: No pairs specified, skipping WebSocket connection

// After user adds credentials:
[INFO] [UI] MarketTicker: API credentials check { hasCredentials: true }
[INFO] [UI] useMarketTicker: Initializing { initialPairsCount: 14 }
[INFO] [WebSocket] Initiating WebSocket connection
[INFO] [WebSocket] ✅ WebSocket connected successfully
```

## Files Modified

### `src/components/MarketTicker/MarketTicker.tsx`
- ✅ Added credential check on mount
- ✅ Added periodic re-checking (every 2 seconds)
- ✅ Added conditional rendering for no credentials state
- ✅ Added Link to Settings page
- ✅ Pass empty array to useMarketTicker when no credentials

### `src/components/MarketTicker/MarketTicker.module.css`
- ✅ Added `.noCredentials` container style
- ✅ Added `.warningIcon` style
- ✅ Added `.warningText` style
- ✅ Added `.settingsLink` with hover effect

### `src/hooks/useMarketTicker.ts`
- ✅ Added early return if no pairs specified
- ✅ Added logging for skipped connection
- ✅ Prevents WebSocket errors when credentials missing

## Testing

### Test 1: No Credentials
1. Clear localStorage
2. Refresh app
3. Should see warning message
4. Click "Settings" link → navigates to Settings page

### Test 2: Add Credentials
1. Start without credentials (see warning)
2. Navigate to Settings
3. Enter API key and secret
4. Save
5. Wait up to 2 seconds
6. Ticker should automatically start showing live data

### Test 3: Remove Credentials
1. Start with credentials (ticker working)
2. Clear localStorage in console: `localStorage.clear()`
3. Wait up to 2 seconds
4. Should revert to warning message

## Benefits

1. **Better UX** - Clear instructions instead of confusing "connecting" state
2. **No Errors** - Won't try to connect WebSocket without credentials
3. **Automatic** - No manual refresh needed when credentials added
4. **Discoverable** - New users immediately know they need to configure API
5. **Professional** - Clean, Bloomberg-style messaging

## Edge Cases Handled

✅ Credentials added while app running → Auto-detects within 2 seconds
✅ Credentials removed while app running → Reverts to warning message
✅ Page refresh → Checks credentials on mount
✅ Direct navigation → Works on any page
✅ Slow credential save → Periodic check catches it

## Future Enhancements

Possible improvements:
- Add "Retry Connection" button if WebSocket fails
- Show credential status in debug panel
- Add animation when transitioning from warning to ticker
- Cache WebSocket connection to avoid reconnecting
- Add "Learn More" link with API setup instructions

---

**Now the ticker only runs when your API is connected, and users see a clear message directing them to Settings!** 🎉
