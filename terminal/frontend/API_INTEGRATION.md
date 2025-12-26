# Kraken API Integration - Complete Guide

## Overview

The trading terminal now includes **full Kraken API integration** with both REST and WebSocket connectivity, based on the structure from `main.py` but optimized for React and TypeScript.

---

## Architecture

```
services/
├── krakenAPI.ts         # REST API service (similar to main.py KrakenAPI class)
└── krakenWebSocket.ts   # WebSocket manager for real-time data

hooks/
├── useOpenOrders.ts     # Hook for order management
├── useMarketTicker.ts   # Hook for real-time price ticker
├── useOrderBook.ts      # Hook for order book data
└── usePlaceOrder.ts     # Hook for placing orders
```

---

## 🔐 Authentication

### Setting Up API Credentials

1. **Get Kraken API Keys**:
   - Log into your Kraken account
   - Navigate to Settings → API
   - Create new API key with required permissions:
     - ✅ Query Funds
     - ✅ Query Open Orders
     - ✅ Query Closed Orders
     - ✅ Create & Modify Orders
     - ✅ Cancel/Close Orders

2. **Configure in Terminal**:
   - Navigate to Settings page (Alt + S)
   - Enter API Key
   - Enter API Secret
   - Click "Save Configuration"

### How It Works

```typescript
// API service automatically loads credentials from localStorage
const krakenAPI = new KrakenAPIService()

// Set credentials programmatically
krakenAPI.setCredentials(apiKey, apiSecret)

// Check if configured
if (krakenAPI.hasCredentials()) {
  // Ready to make authenticated calls
}
```

---

## 📡 REST API Service

### Features

✅ **HMAC-SHA512 Signature Generation** (just like main.py)  
✅ **Rate Limiting** (15 calls per 3 second window)  
✅ **Automatic nonce generation**  
✅ **Error handling with Kraken error responses**  
✅ **Type-safe responses with TypeScript**

### Available Methods

#### Public Endpoints (No Auth Required)

```typescript
// Get order book
const book = await krakenAPI.getOrderBook('XBT/USD', 10)

// Get ticker info
const ticker = await krakenAPI.getTicker('ETH/USD')

// Get multiple tickers at once
const tickers = await krakenAPI.getTickers(['XBT/USD', 'ETH/USD'])
```

#### Private Endpoints (Auth Required)

```typescript
// Get open orders
const orders = await krakenAPI.getOpenOrders()

// Place an order
const result = await krakenAPI.addOrder(
  'XBT/USD',      // pair
  'buy',          // type
  'limit',        // ordertype
  '0.001',        // volume
  '40000'         // price (optional for market orders)
)

// Cancel order
await krakenAPI.cancelOrder('ORDER-ID')

// Cancel all orders
await krakenAPI.cancelAllOrders()

// Get account balance
const balance = await krakenAPI.getBalance()

// Get trade balance (with margin info)
const tradeBalance = await krakenAPI.getTradeBalance()

// Get closed orders
const closed = await krakenAPI.getClosedOrders()

// Get trade history
const history = await krakenAPI.getTradesHistory()
```

### Response Format

All methods return a `KrakenResponse<T>`:

```typescript
{
  error: string[]        // Array of error messages (empty if success)
  result?: T             // Result data (only present if successful)
}
```

### Rate Limiting

Automatically managed with token bucket algorithm:
- **15 requests per 3 seconds**
- Automatically waits when limit reached
- No manual intervention needed

---

## ⚡ WebSocket Service

### Features

✅ **Auto-reconnect** with exponential backoff  
✅ **Heartbeat** to keep connection alive  
✅ **Multiple subscriptions** (ticker, order book, trades)  
✅ **Private feed support** for order updates  
✅ **Type-safe callbacks**

### Connecting

```typescript
import { krakenWS } from '../services/krakenWebSocket'

// Connect to public feed
await krakenWS.connectPublic()

// Connect to private feed (for order updates)
await krakenWS.connectPrivate(apiKey, apiSecret)

// Check connection
if (krakenWS.isConnected()) {
  // Ready to subscribe
}
```

### Subscriptions

#### Ticker Data

```typescript
krakenWS.subscribeTicker(['XBT/USD', 'ETH/USD'], (data) => {
  console.log('Ticker update:', data)
  // {
  //   pair: 'XBT/USD',
  //   bid: '42000.0',
  //   ask: '42001.0',
  //   last: '42000.5',
  //   volume: '1234.567',
  //   high: '43000',
  //   low: '41000',
  //   change: '500',
  //   changePercent: '1.2'
  // }
})
```

#### Order Book

```typescript
krakenWS.subscribeOrderBook(['XBT/USD'], 10, (data) => {
  console.log('Order book update:', data)
  // {
  //   pair: 'XBT/USD',
  //   bids: [['42000', '1.5', '1234567890'], ...],
  //   asks: [['42001', '2.0', '1234567891'], ...]
  // }
})
```

#### Trades

```typescript
krakenWS.subscribeTrades(['XBT/USD'], (data) => {
  console.log('Trade update:', data)
})
```

### Unsubscribing

```typescript
krakenWS.unsubscribe('ticker', ['XBT/USD'])
krakenWS.unsubscribe('book', ['ETH/USD'])
```

### Disconnect

```typescript
krakenWS.disconnect()
```

---

## 🎣 React Hooks

### useOpenOrders

Manages open orders with auto-refresh:

```typescript
import { useOpenOrders } from '../hooks/useOpenOrders'

function OrdersComponent() {
  const { orders, isLoading, error, refresh, cancelOrder, cancelAll } = useOpenOrders(
    true,  // autoRefresh
    3000   // refresh interval (ms)
  )

  return (
    <div>
      {Object.entries(orders).map(([id, order]) => (
        <div key={id}>
          {order.descr.pair} - {order.descr.type} {order.vol}
          <button onClick={() => cancelOrder(id)}>Cancel</button>
        </div>
      ))}
      <button onClick={cancelAll}>Cancel All</button>
    </div>
  )
}
```

### useMarketTicker

Real-time ticker data via WebSocket:

```typescript
import { useMarketTicker } from '../hooks/useMarketTicker'

function TickerComponent() {
  const { tickers, isConnected, subscribe, unsubscribe } = useMarketTicker([
    'XBT/USD',
    'ETH/USD'
  ])

  const tickerData = tickers.get('XBT/USD')

  return (
    <div>
      {isConnected ? 'Connected' : 'Connecting...'}
      <div>BTC: ${tickerData?.last}</div>
      <button onClick={() => subscribe(['SOL/USD'])}>
        Add SOL
      </button>
    </div>
  )
}
```

### useOrderBook

Real-time order book updates:

```typescript
import { useOrderBook } from '../hooks/useOrderBook'

function OrderBookComponent({ pair }: { pair: string }) {
  const { orderBook, isLoading, error } = useOrderBook(pair, 10)

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div>
      <h3>Asks</h3>
      {orderBook?.asks.map(([price, volume]) => (
        <div key={price}>{price} - {volume}</div>
      ))}
      <h3>Bids</h3>
      {orderBook?.bids.map(([price, volume]) => (
        <div key={price}>{price} - {volume}</div>
      ))}
    </div>
  )
}
```

### usePlaceOrder

Place orders with loading states:

```typescript
import { usePlaceOrder } from '../hooks/usePlaceOrder'

function OrderEntryComponent() {
  const { placeOrder, isSubmitting, lastError } = usePlaceOrder()

  const handleSubmit = async () => {
    const result = await placeOrder(
      'XBT/USD',
      'buy',
      'limit',
      '0.001',
      '40000'
    )

    if (result.success) {
      console.log('Order placed:', result.txid)
    } else {
      console.error('Order failed:', result.error)
    }
  }

  return (
    <div>
      <button onClick={handleSubmit} disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Place Order'}
      </button>
      {lastError && <div>Error: {lastError}</div>}
    </div>
  )
}
```

---

## 🔧 Component Integration

### MarketTicker

Now uses **live WebSocket data**:

```typescript
// Automatically subscribes to 14 pairs
const TICKER_PAIRS = [
  'XBT/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD',
  'ADA/USD', 'DOT/USD', 'MATIC/USD', 'LINK/USD',
  'UNI/USD', 'ATOM/USD', 'AVAX/USD', 'LTC/USD',
  'BCH/USD', 'ALGO/USD'
]

// Real-time updates via WebSocket
const { tickers, isConnected } = useMarketTicker(TICKER_PAIRS)
```

### Settings Page

**Saves credentials** and tests connection:

```typescript
const handleSave = async () => {
  // Save to localStorage
  localStorage.setItem('apiConfig', JSON.stringify(apiConfig))
  
  // Update API service
  krakenAPI.setCredentials(apiKey, apiSecret)
  
  // Test connection
  const result = await krakenAPI.getBalance()
  if (!result.error) {
    console.log('Connected successfully!')
  }
}
```

---

## 📊 Kraken Pair Formats

Kraken uses specific pair formats:

| Common Name | Kraken Symbol |
|-------------|---------------|
| Bitcoin     | `XBT/USD`     |
| Ethereum    | `ETH/USD`     |
| Solana      | `SOL/USD`     |
| Ripple      | `XRP/USD`     |
| Cardano     | `ADA/USD`     |
| Polkadot    | `DOT/USD`     |
| Polygon     | `MATIC/USD`   |

**Note**: Bitcoin is `XBT` (not `BTC`) in Kraken API!

---

## ⚠️ Error Handling

All API calls include comprehensive error handling:

```typescript
try {
  const result = await krakenAPI.getTicker('XBT/USD')
  
  if (result.error && result.error.length > 0) {
    console.error('Kraken error:', result.error.join(', '))
  } else if (result.result) {
    console.log('Success:', result.result)
  }
} catch (err) {
  console.error('Network error:', err)
}
```

---

## 🚀 Getting Started

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Configure API keys** in Settings (Alt + S)

4. **Watch real-time data** flow in!

---

## 📝 Differences from main.py

| Feature | main.py | React Terminal |
|---------|---------|----------------|
| Language | Python | TypeScript |
| HTTP Client | `requests` | `fetch` API |
| WebSocket | `websocket-client` | Native WebSocket |
| Signature | `hmac` + `hashlib` | `crypto-js` |
| Rate Limiting | Manual tracking | Token bucket algorithm |
| UI Framework | Tkinter | React |
| State Management | Class instance | React hooks |

---

## 🔒 Security Notes

- API keys stored in localStorage (browser-only)
- **Production**: Move to secure backend
- **Never** commit API keys to version control
- Consider using environment variables

---

## 🐛 Troubleshooting

**"API credentials not configured"**
- Go to Settings and enter your API key/secret

**"Rate limit reached"**
- Automatic backoff in place
- Reduce request frequency if needed

**WebSocket disconnecting**
- Auto-reconnect enabled
- Check network connection
- Verify Kraken API status

**Invalid signature**
- Check API secret is correct
- Ensure no extra whitespace in credentials
- Try regenerating API keys

---

## 📚 Resources

- [Kraken REST API Docs](https://docs.kraken.com/rest/)
- [Kraken WebSocket Docs](https://docs.kraken.com/websockets/)
- [Kraken API Support](https://support.kraken.com/hc/en-us/categories/204677617-API)

---

**Built with ❤️ for CU Quants Trading Team**
