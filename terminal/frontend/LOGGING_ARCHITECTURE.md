# Logging System Architecture

## Component Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   App    │  │HomePage  │  │ Trading  │  │ Settings │        │
│  │          │  │          │  │   Page   │  │   Page   │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                         │                                        │
│                    uiLogger.info()                              │
└─────────────────────────┼──────────────────────────────────────┘
                          │
┌─────────────────────────┼──────────────────────────────────────┐
│                   Component Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │MarketTicker  │  │  DataTable   │  │    Panel     │         │
│  │              │  │              │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                         │                                       │
│                    uiLogger.debug()                            │
└─────────────────────────┼─────────────────────────────────────┘
                          │
┌─────────────────────────┼─────────────────────────────────────┐
│                     Hooks Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │useMarket     │  │useOpenOrders │  │usePlaceOrder │        │
│  │  Ticker      │  │              │  │              │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                 │
│         └─────────────────┴─────────────────┘                 │
│                         │                                      │
│                    uiLogger.info()                            │
└─────────────────────────┼────────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                  │
         ▼                                  ▼
┌─────────────────────┐          ┌─────────────────────┐
│   API Service       │          │  WebSocket Service  │
│  krakenAPI.ts       │          │ krakenWebSocket.ts  │
│                     │          │                     │
│ - getBalance()      │          │ - connectPublic()   │
│ - getOrderBook()    │          │ - subscribeTicker() │
│ - addOrder()        │          │ - handleMessage()   │
│ - cancelOrder()     │          │ - reconnect()       │
│                     │          │                     │
│  apiLogger.info()   │          │  wsLogger.info()    │
└─────────┬───────────┘          └─────────┬───────────┘
          │                                │
          └────────────────┬───────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Logger Utility (logger.ts)                 │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  apiLogger   │  │  wsLogger    │  │  uiLogger    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                         │                                     │
│                         ▼                                     │
│              Logger.getInstance()                            │
│                         │                                     │
│            ┌────────────┴────────────┐                       │
│            │                         │                       │
│            ▼                         ▼                       │
│    ┌──────────────┐         ┌──────────────┐               │
│    │ Log History  │         │ Console Out  │               │
│    │ (in memory)  │         │  (browser)   │               │
│    │ Max 1000     │         │  Colored     │               │
│    └──────┬───────┘         └──────────────┘               │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│                      Output Layer                             │
│                                                                │
│  ┌────────────────────┐         ┌────────────────────┐       │
│  │  Browser Console   │         │   Debug Panel      │       │
│  │  (F12)             │         │  (Ctrl+Shift+D)    │       │
│  │                    │         │                    │       │
│  │ - Color-coded      │         │ - Last 100 logs    │       │
│  │ - Timestamps       │         │ - Color-coded      │       │
│  │ - Filterable       │         │ - Real-time        │       │
│  │ - Searchable       │         │ - Downloadable     │       │
│  │                    │         │ - Clearable        │       │
│  └────────────────────┘         └────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

## Log Flow Example

### User Action: Opening Trading Page

```
1. User clicks "Trading" in sidebar
   │
   ├─► [INFO] [UI] App: Route changed { path: "/trading" }
   │
2. TradingPage component mounts
   │
   ├─► [INFO] [UI] TradingPage: Component mounted
   │
3. useOpenOrders hook initializes
   │
   ├─► [INFO] [UI] useOpenOrders: Initializing
   │
4. API call to fetch open orders
   │
   ├─► [INFO] [API] Making private API request { endpoint: "OpenOrders" }
   ├─► [DEBUG] [API] Sending private request { url: "...", nonce: "..." }
   │
5. Rate limiting check
   │
   ├─► [DEBUG] [API] Rate limit check passed { currentCalls: 5, maxCalls: 15 }
   │
6. API responds
   │
   ├─► [INFO] [API] Private API request successful { endpoint: "OpenOrders" }
   │
7. Data displayed in component
   │
   └─► [DEBUG] [UI] useOpenOrders: Orders updated { orderCount: 3 }
```

### WebSocket Connection Flow

```
1. MarketTicker component mounts
   │
   ├─► [INFO] [UI] MarketTicker: Component mounted { pairCount: 14 }
   │
2. useMarketTicker hook initializes
   │
   ├─► [INFO] [UI] useMarketTicker: Initializing { initialPairs: [...] }
   │
3. WebSocket connection attempt
   │
   ├─► [INFO] [WebSocket] Initiating WebSocket connection
   ├─► [DEBUG] [WebSocket] Connecting to wss://ws.kraken.com
   │
4. Connection established
   │
   ├─► [INFO] [WebSocket] ✅ WebSocket connected successfully (public)
   │
5. Subscribe to ticker data
   │
   ├─► [INFO] [WebSocket] Subscribing to ticker updates { pairs: [...] }
   ├─► [DEBUG] [WebSocket] Ticker subscription request sent
   │
6. Subscription confirmed
   │
   ├─► [INFO] [WebSocket] Subscription confirmed { channel: "ticker", pair: "XBT/USD" }
   │
7. Data starts flowing
   │
   ├─► [DEBUG] [WebSocket] WebSocket message received { dataType: "array" }
   ├─► [DEBUG] [UI] useMarketTicker: Ticker update received { pair: "XBT/USD", last: "43250.50" }
   └─► [DEBUG] [UI] MarketTicker: Ticker data updated { tickerCount: 14 }
```

## Error Handling Flow

```
Error Occurs
    │
    ├─► Component/Service catches error
    │
    ├─► [ERROR] [Category] Error message { details }
    │
    ├─► Error logged to console (RED)
    │
    ├─► Error stored in log history
    │
    ├─► Error appears in Debug Panel
    │
    └─► User can download logs for debugging
```

## Data Structures

### Log Entry
```typescript
{
  timestamp: "2025-12-25T10:30:45.123Z",
  level: "INFO" | "DEBUG" | "WARN" | "ERROR",
  category: "API" | "WebSocket" | "UI" | string,
  message: string,
  data?: any
}
```

### Log History
```typescript
Array<LogEntry>  // Max 1000 entries, FIFO
```

## Performance Considerations

```
┌─────────────────────────────────────────────┐
│ Development Mode (DEV=true)                 │
│ - ALL log levels enabled                    │
│ - Console output: verbose                   │
│ - Debug Panel: available                    │
│ - Performance: ~0.5ms per log               │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Production Mode (PROD=true)                 │
│ - DEBUG logs: disabled                      │
│ - Console output: minimal                   │
│ - Debug Panel: can be disabled              │
│ - Performance: ~0.2ms per log               │
└─────────────────────────────────────────────┘
```

## Integration Points

Every logging call:
1. Checks environment (DEV/PROD)
2. Creates LogEntry object
3. Adds to history (FIFO, max 1000)
4. Outputs to console (color-coded)
5. Available to Debug Panel
6. Can be exported as JSON

## Best Practices

1. **Component Mounting**
   ```typescript
   useEffect(() => {
     uiLogger.info('ComponentName: Component mounted', { props })
   }, [])
   ```

2. **API Calls**
   ```typescript
   apiLogger.info('Making request', { endpoint })
   // ... call API
   apiLogger.info('Request successful', { data })
   ```

3. **WebSocket Events**
   ```typescript
   wsLogger.info('Connection event', { status })
   wsLogger.debug('Message received', { size })
   ```

4. **Error Handling**
   ```typescript
   try {
     // operation
   } catch (error) {
     logger.error('Category', 'Operation failed', error)
   }
   ```

## Access Points

- **Browser Console:** F12 key
- **Debug Panel:** Ctrl + Shift + D
- **Programmatic:** `logger.getHistory()`
- **Download:** Debug Panel > Download button
- **Clear:** Debug Panel > Clear button
