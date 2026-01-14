# Backend Functionality Removed from Frontend

## Date: December 25, 2025

## Summary

All backend functionality has been removed from the frontend and replaced with stub implementations. The frontend now returns mock/empty data for all API calls and logs warnings to the console.

## Files Modified

### 1. `/src/services/krakenAPI.ts`
**Before:** Direct Kraken REST API integration
- HMAC-SHA512 signature generation using CryptoJS
- Direct fetch calls to `https://api.kraken.com`
- Client-side rate limiting
- API key/secret management in localStorage

**After:** Stub implementation
- All methods return mock/empty data
- Logs warnings when called
- Still maintains same interface for compatibility
- No crypto dependencies
- No direct API calls

**Removed:**
- CryptoJS dependency usage
- `generateSignature()` method
- `checkRateLimit()` method
- Direct Kraken API calls in `request()` method
- All cryptographic operations

### 2. `/src/services/krakenWebSocket.ts`
**Before:** Direct Kraken WebSocket integration
- WebSocket connections to `wss://ws.kraken.com`
- Subscription management
- Reconnection logic
- Heartbeat/ping-pong
- Message parsing and distribution

**After:** Stub implementation
- All methods do nothing and log warnings
- `isConnected()` returns false
- No actual WebSocket connections
- Still maintains same interface for compatibility

**Removed:**
- WebSocket connection logic
- Subscription/unsubscription handling
- Reconnection attempts
- Heartbeat intervals
- Message parsing

## Dependencies That Can Be Removed

The following dependencies in `package.json` are no longer needed by the frontend (but may want to keep for now to avoid breaking builds):

```json
{
  "crypto-js": "^4.2.0",      // Was used for HMAC-SHA512 signing
  "@types/crypto-js": "^4.2.1" // TypeScript types for crypto-js
}
```

**Recommendation:** Leave these in `package.json` for now in case you want to quickly test direct API integration during development.

## Hooks Still Using Services

The following hooks still call the stub services (but now receive mock data):

- `/src/hooks/useOpenOrders.ts` - Calls `krakenAPI.getOpenOrders()`
- `/src/hooks/usePlaceOrder.ts` - Calls `krakenAPI.addOrder()`
- `/src/hooks/useMarketTicker.ts` - Calls `krakenWS.subscribeTicker()`
- `/src/hooks/useOrderBook.ts` - Calls `krakenWS.subscribeOrderBook()`
- `/src/hooks/useTrades.ts` - Calls `krakenWS.subscribeTrades()`

**These hooks do NOT need to be modified.** They will work once the backend is implemented and the stub services are updated to call the backend instead of returning mock data.

## What the Stub Services Do

### krakenAPI (REST API Stub)
- `setCredentials()` - Stores in localStorage with warning (INSECURE)
- `hasCredentials()` - Checks localStorage
- `getOrderBook()` - Returns empty order book
- `getTicker()` - Returns empty object
- `getTickers()` - Returns empty object
- `getOpenOrders()` - Returns empty orders object
- `addOrder()` - Returns error "Backend not implemented"
- `cancelOrder()` - Returns error "Backend not implemented"
- `cancelAllOrders()` - Returns error "Backend not implemented"
- `getBalance()` - Returns empty object
- `getTradeBalance()` - Returns undefined
- `getClosedOrders()` - Returns empty object
- `getTradesHistory()` - Returns empty object

### krakenWS (WebSocket Stub)
- `connectPublic()` - Logs warning, resolves immediately
- `disconnect()` - Does nothing
- `subscribeTicker()` - Logs warning, does nothing
- `unsubscribeTicker()` - Logs warning, does nothing
- `subscribeOrderBook()` - Logs warning, does nothing
- `unsubscribeOrderBook()` - Logs warning, does nothing
- `subscribeTrades()` - Logs warning, does nothing
- `unsubscribeTrades()` - Logs warning, does nothing
- `subscribeOwnTrades()` - Logs warning, does nothing
- `unsubscribeOwnTrades()` - Logs warning, does nothing
- `isConnected()` - Returns false

## Next Steps

### For Backend Implementation:
1. See `/backend/TODO.md` for complete implementation checklist
2. Build FastAPI or Flask server
3. Implement Kraken API integration in backend
4. Implement WebSocket server
5. Update frontend stubs to call backend endpoints

### For Frontend Updates (After Backend is Ready):
1. Update `krakenAPI.ts`:
   ```typescript
   public async getOrderBook(pair: string, count = 10) {
     return this.request(`/orderbook/${pair}?count=${count}`)
   }
   ```

2. Update `krakenWebSocket.ts`:
   ```typescript
   public connectPublic(): Promise<void> {
     this.ws = new WebSocket(`${BACKEND_WS_BASE}/ticker`)
     // ... connection logic
   }
   ```

3. Remove all `apiLogger.warn()` calls
4. Add proper error handling
5. Test with real backend

## Testing

To verify the frontend still works with stubs:

```bash
npm run dev
```

**Expected behavior:**
- App loads without errors
- Console shows warnings like "⚠️ Backend not implemented"
- UI displays but shows no data
- No network requests to Kraken API
- No WebSocket connections

## Security Improvements

✅ API keys no longer sent to Kraken from browser  
✅ No crypto operations in frontend  
✅ No direct exposure to Kraken API  
✅ Rate limiting will be handled by backend  
✅ Credentials will be managed server-side  

## Environment Variables

Add to `.env` (or `.env.local`):

```bash
VITE_BACKEND_URL=http://localhost:8000/api
VITE_BACKEND_WS_URL=ws://localhost:8000/ws
```

These are already set with defaults in the code:
- `BACKEND_API_BASE` defaults to `http://localhost:8000/api`
- `BACKEND_WS_BASE` defaults to `ws://localhost:8000/ws`
