# CU Quants Terminal Bear — Implementation Plan

This document captures every architectural decision made during planning. It serves as full context for implementation. Read this alongside `SPEC.md`.

---

## High-Level Architecture

There are two independent WebSocket paths in this system:

1. **Public Orderbook WS** — Browser connects directly to the exchange (e.g., `wss://wsus.okx.com:8443/ws/v5/public`). No auth needed. Dynamic per-pair subscriptions. Batched UI updates every 500ms via ref + interval flush. This already exists as hooks (`useOkxOrderbook`, `useKrakenOrderbook`) and will be refactored into context providers.

2. **Private Order Events WS** — Browser connects to the FastAPI backend. The backend maintains an authenticated WebSocket to the exchange's private API (e.g., `wss://wsus.okx.com:8443/ws/v5/private`). The backend subscribes globally to all order events, normalizes them, and relays them to all connected frontend clients. The frontend uses these events to trigger React Query cache invalidations.

```
                          Public Orderbook (no auth)
Browser ──────────────────────────────────────────────> Exchange WS (public)

                          Private Order Events (authenticated)
Browser ───── WS ──────> FastAPI Backend ───── WS ──────> Exchange WS (private)
             /orders/{exchange}            (authenticated, global orders channel)
```

---

## Decision Log

These decisions were made explicitly during planning:

- **Global order subscription**: The backend subscribes to ALL order events for the exchange (not per-instrument). The frontend filters by which pairs it currently cares about. This avoids per-pair subscription management on the private WS side.
- **No subscription management class needed**: The order events subscription is a single always-on connection per exchange. No dynamic subscribe/unsubscribe per pair on the private WS. A dedicated manager class would be over-engineering.
- **Lazy connection lifecycle**: The backend only opens a private WS to an exchange when the first frontend client connects for that exchange. It tears down the connection when the last frontend client for that exchange disconnects (i.e., the user removes all pairs for that exchange).
- **Reference counting for multi-tab**: Multiple browser tabs each open their own WS to the backend. The backend maintains only ONE private connection to each exchange regardless of frontend client count. Connect on first client, disconnect on last.
- **Backend normalizes events**: The backend converts OKX native pairs (`BTC-USDT`) to normalized format (`BTC/USD`) before relaying. The frontend never sees exchange-native formats from the order events stream.
- **Frontend receives a signal, then refetches**: The order event from the backend specifies the affected exchange + normalized pair. The frontend does NOT use the event payload to update local state directly. Instead, it invalidates the React Query cache for that pair, which triggers a REST refetch. This keeps REST as the single source of truth for order state.
- **Batched event processing on frontend**: Order events are accumulated in a ref. Every 500ms, the ref is read, React Query is invalidated for all affected pairs, and the ref is cleared. This prevents rapid-fire refetches from burst events (e.g., multiple partial fills in quick succession).
- **Graceful degradation on pair add**: When a user adds a new ticker/exchange pair, the orderbook WS subscription and the initial order fetch happen independently. If one fails, the other still proceeds. The UI shows the row with whichever data is available and surfaces an inline error for the failed piece. This is preferred over atomic all-or-nothing semantics.
- **Status events alongside order events**: The backend→frontend WS protocol carries two message types: order events and connection status changes. If the backend's private WS to the exchange drops, the frontend is notified and can show a stale-feed warning.
- **React Query cache keyed per-pair**: Query key structure is `["orders", exchange, pair]` (e.g., `["orders", "okx", "BTC/USD"]`). This allows granular invalidation — only the affected pair refetches. If the `OrderPanel` for that pair isn't mounted, React Query skips the refetch entirely (no active observers).

---

## Backend Implementation

### Existing Code (terminal/backend/)

- `app.py` — FastAPI app with lifespan pattern, `ServiceContainer` created on startup
- `exchange_services/exchange.py` — `ExchangeService` ABC with `_request()` helper and abstract methods for `place_order`, `get_orders`, `cancel_order`, and `subscribe_to_order_events` (not yet implemented)
- `exchange_services/okx_service.py` — `OkxService` with full REST implementation (place, get, cancel orders), auth/signing (`_sign`, `_get_headers`), and pair normalization (`_to_native_pair`, `_from_native_pair`). Uses `httpx` for HTTP. Reads API credentials from env vars (`OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE`). Has a `simulated` flag for test trading.
- `exchange_services/service_container.py` — `ServiceContainer` with lazy service creation. Currently only supports OKX.
- `routes/orders.py` — Stub REST endpoints and a WS endpoint stub. Needs to be rewritten.
- `models.py` — Pydantic models: `Order`, `OrderResponse`, `OrdersRequest`

### 1. OKX Private WebSocket Client

Add to `OkxService` (or a dedicated `OkxOrderEventStream` class):

- Connect to `wss://wsus.okx.com:8443/ws/v5/private`
- Authenticate by sending a login message:
  ```json
  {
    "op": "login",
    "args": [{
      "apiKey": "<key>",
      "passphrase": "<passphrase>",
      "timestamp": "<unix_timestamp_seconds>",
      "sign": "<base64_hmac_sha256(timestamp + 'GET' + '/users/self/verify')>"
    }]
  }
  ```
  The signing reuses the existing `_sign` method pattern (timestamp + method + path, HMAC-SHA256, base64 encode). For the private WS login, the prehash string is `timestamp + "GET" + "/users/self/verify"` with an empty body.
- After successful login response, subscribe to the orders channel:
  ```json
  {
    "op": "subscribe",
    "args": [{ "channel": "orders", "instType": "SPOT" }]
  }
  ```
- Handle incoming order events. OKX pushes events for: new orders, partial fills, full fills, cancellations, amendments, and rejections. Each event contains `instId`, `ordId`, `state`, `side`, `px`, `sz`, `fillPx`, `fillSz`, etc.
- Send a `"ping"` frame every 25-30 seconds to keep the connection alive (OKX requires this).
- On disconnect, attempt reconnection with exponential backoff: delays of 1s, 2s, 4s up to a maximum of 3 retries. On all retries exhausted, report connection as `"disconnected"`.
- If the `simulated` flag is set, include the `x-simulated-trading: 1` header equivalent in the login args (OKX simulated trading mode).

### 2. OrderEventRelay

A new class that lives in the `ServiceContainer` (or alongside it). Responsibilities:

- **Frontend client registry**: Maintains a `Dict[str, Set[WebSocket]]` mapping exchange names to connected frontend WebSocket clients.
- **Reference-counted exchange connections**: When a frontend client registers for an exchange and it's the first client for that exchange, the relay starts the private WS connection (via `OkxService`). When the last client for an exchange deregisters, the relay tears down that private WS.
- **Fan-out**: When an order event arrives from the exchange's private WS, the relay normalizes it and sends it to ALL registered frontend clients for that exchange.
- **Status broadcasting**: When the backend's private WS connection status changes (connected, reconnecting, disconnected), the relay pushes a status event to all frontend clients for that exchange.
- **Cleanup**: On app shutdown (lifespan teardown), close all private WS connections and all frontend client connections.

### 3. Normalized Event Schema (Backend → Frontend)

Two message types:

```python
# Order event — sent when the exchange reports an order state change
{
    "type": "order_event",
    "exchange": "okx",
    "pair": "BTC/USD",           # normalized, never native format
    "orderId": "1234567890",
    "status": "filled",          # "live" | "partially_filled" | "filled" | "canceled" | "rejected"
    "side": "buy",
    "price": 68420.0,
    "size": 0.5,
    "timestamp": "2026-02-23T15:30:00.000Z"
}

# Status event — sent when the backend's connection to the exchange changes
{
    "type": "status",
    "exchange": "okx",
    "connectionStatus": "connected"  # "connected" | "reconnecting" | "disconnected"
}
```

### 4. Updated Routes (routes/orders.py)

**WebSocket endpoint** — `@router.websocket("/{exchange}")`:
- On connect: accept the WebSocket, register the client with the `OrderEventRelay` for the given exchange.
- The relay handles starting the private WS if this is the first client.
- Stream normalized events to the client as they arrive.
- On disconnect (client closes tab, network drop): deregister from the relay. Relay tears down private WS if last client.
- No `symbol` parameter — the subscription is global per-exchange.

**REST endpoints** — unchanged in purpose, cleaned up:
- `GET /orders/{exchange}?pair=BTC/USD` — Fetch open orders for a specific exchange and normalized pair. The backend translates to native format, calls the exchange API with auth, returns normalized results. This is what React Query calls.
- `POST /orders/{exchange}` — Place an order. Body: `{ pair, side, type, price?, size }`. Backend translates pair, signs request, forwards to exchange.
- `DELETE /orders/{exchange}/{order_id}?pair=BTC/USD` — Cancel an order. Backend translates pair, signs request, forwards to exchange.

All REST endpoints proxy through the `OkxService` (or whichever exchange service) which handles auth/signing.

### 5. Updated Models (models.py)

Extend or add:
- `OrderEvent` — Pydantic model for the normalized order event pushed over WS
- `StatusEvent` — Pydantic model for connection status events
- Clean up `OrdersRequest` to not be overloaded (separate request models for place, cancel, get)

### 6. Updated App Lifespan (app.py)

- Create `ServiceContainer` and `OrderEventRelay` on startup
- Wire the relay into the service container (or make it accessible to routes)
- On shutdown: call relay cleanup to close all connections
- Register the orders router with the app

---

## Frontend Implementation

### Existing Code (dashboard_v2/src/)

- `main.tsx` — Basic React 19 entry, renders `<App />` directly, no providers
- `App.tsx` — Manages exchange/symbol state locally, renders `KrakenView` or `OkxView` based on selection
- `components/` — `Orderbook`, `OrderbookSide`, `OrderbookRow`, `KrakenView`, `OkxView`. Pure display components for orderbook data.
- `hooks/` — `useKrakenOrderbook`, `useOkxOrderbook`. Each manages its own WS lifecycle with batched ref+interval flush pattern.
- `types/orderbook.ts` — `Exchange`, `OrderbookLevel`, `OrderbookData`, Kraken/OKX WS message types, `EXCHANGE_SYMBOLS` config
- No React Query, no context providers, no order management components, no toast system

### 1. Install Dependencies

```bash
npm install @tanstack/react-query react-hot-toast
```

### 2. Types (types/orders.ts)

```typescript
export interface Order {
  id: string;
  pair: string;           // normalized "BTC/USD"
  exchange: Exchange;
  side: "buy" | "sell";
  type: "limit" | "market";
  price?: number;
  size: number;
  status: string;
  createdAt?: string;
}

export interface OrderParams {
  pair: string;           // normalized
  side: "buy" | "sell";
  type: "limit" | "market";
  price?: number;         // required for limit
  size: number;
}

export interface OrderResult {
  orderId: string;
}

export interface OrderEvent {
  type: "order_event";
  exchange: Exchange;
  pair: string;
  orderId: string;
  status: string;
  side: string;
  price: number;
  size: number;
  timestamp: string;
}

export interface StatusEvent {
  type: "status";
  exchange: Exchange;
  connectionStatus: "connected" | "reconnecting" | "disconnected";
}

export type BackendWsMessage = OrderEvent | StatusEvent;
```

### 3. React Query Setup

Configure `QueryClient` in `main.tsx`:

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

// Wrap App:
<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

### 4. OrderEventsProvider (contexts/OrderEventsContext.tsx)

A React context provider that:

- Receives the set of active exchanges (derived from row config — which exchanges have at least one pair configured)
- For each active exchange, opens a WebSocket to the FastAPI backend at `ws://<backend>/orders/{exchange}`
- On incoming `order_event` messages: pushes the affected pair into a ref (`Map<Exchange, Set<string>>`)
- On incoming `status` messages: updates a connection status state map
- Every 500ms, reads the event ref, calls `queryClient.invalidateQueries({ queryKey: ["orders", exchange, pair] })` for each accumulated pair, clears the ref
- When an exchange is removed from the active set (user removed all pairs for it): closes that WS connection
- Exposes via context:
  ```typescript
  interface OrderEventsContextValue {
    orderEventsStatus: Record<Exchange, "connected" | "reconnecting" | "disconnected" | "idle">;
  }
  ```
  Components read status to show connection health. The actual order data flows through React Query, not this context.

### 5. React Query Hooks (hooks/useOrders.ts, hooks/usePlaceOrder.ts, hooks/useCancelOrder.ts)

**useOrders(exchange, pair)**:
```typescript
useQuery({
  queryKey: ["orders", exchange, pair],
  queryFn: () => api.fetchOrders(exchange, pair),
})
```
- Returns open orders for that exchange/pair
- Automatically refetches when `OrderEventsProvider` invalidates the query key
- If the component is not mounted (user hasn't opened the OrderPanel for this pair), no refetch happens on invalidation

**usePlaceOrder(exchange)**:
```typescript
useMutation({
  mutationFn: (params: OrderParams) => api.placeOrder(exchange, params),
  onSuccess: (_data, variables) => {
    queryClient.invalidateQueries({ queryKey: ["orders", exchange, variables.pair] });
    toast.success("Order placed");
  },
  onError: (error) => {
    // 4xx: toast immediately
    // 5xx/timeout: invalidate orders first, then toast with uncertainty message
  },
})
```

**useCancelOrder(exchange)**:
```typescript
useMutation({
  mutationFn: ({ orderId, pair }) => api.cancelOrder(exchange, orderId, pair),
  onSuccess: (_data, variables) => {
    queryClient.invalidateQueries({ queryKey: ["orders", exchange, variables.pair] });
    toast.success("Order cancelled");
  },
  onError: (error) => {
    // 5xx/timeout: invalidate first (cancel may have succeeded), then toast
    // 4xx: toast immediately
  },
})
```

No optimistic updates for any mutation. Wait for confirmed REST response.

### 6. API Client (api/orders.ts)

Thin fetch wrapper for REST calls to the FastAPI backend:

```typescript
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchOrders(exchange: Exchange, pair: string): Promise<Order[]>
async function placeOrder(exchange: Exchange, params: OrderParams): Promise<OrderResult>
async function cancelOrder(exchange: Exchange, orderId: string, pair: string): Promise<void>
```

### 7. Orderbook WebSocket Context Providers

Refactor the existing `useOkxOrderbook` and `useKrakenOrderbook` hooks into context providers per the spec.

**OKXWsProvider** / **KrakenWsProvider**:
- Own the WebSocket connection lifecycle (one connection per exchange)
- Support dynamic subscribe/unsubscribe per pair (driven by row config changes)
- Use the existing ref + 500ms interval flush pattern for batched UI updates
- Expose the `ExchangeContextValue` interface:
  ```typescript
  interface ExchangeContextValue {
    connectionStatus: "connecting" | "connected" | "reconnecting" | "disconnected" | "failed";
    lastUpdated: Date | null;
    orderbook: Record<string, OrderbookSnapshot>;  // keyed by normalized pair
    subscribe(pair: string): void;
    unsubscribe(pair: string): void;
    subscribedPairs: string[];
  }
  ```
- Reconnection with exponential backoff, max 3 retries, status set to `"failed"` on exhaustion with toast error

### 8. Row Configuration (hooks/useRowConfig.ts)

Manages which exchange/pair combinations the user wants to see.

```typescript
interface RowConfig {
  version: number;
  exchanges: {
    kraken: string[];   // normalized pairs: ["BTC/USD", "ETH/USD"]
    okx: string[];
  };
}
```

- Persisted to `localStorage` under key `terminal_bear_config`
- On load: read from localStorage, validate version, migrate or reset if stale
- Exposes: `config`, `addPair(exchange, pair)`, `removePair(exchange, pair)`
- **Adding a pair**: triggers orderbook WS subscribe for that pair, triggers initial order fetch via React Query. If one fails, the other still proceeds — graceful degradation with inline error.
- **Removing a pair**: triggers orderbook WS unsubscribe, evicts from React Query cache via `queryClient.removeQueries({ queryKey: ["orders", exchange, pair] })`, removes the dashboard row.

### 9. Component Tree

```
<QueryClientProvider>
  <OrderEventsProvider activeExchanges={derivedFromConfig}>
    <KrakenWsProvider>
      <OKXWsProvider>
        <Toaster />                          // react-hot-toast
        <Dashboard>
          <DashboardHeader />                // connection status for orderbook WS + order events WS
          <RowConfigPanel />                 // add/remove pairs per exchange
          <OrderbookTable>
            <OrderbookRow />                 // one per exchange/pair, click to open OrderPanel
          </OrderbookTable>
          <OrderPanel>                       // slides in on row click
            <OrderList>
              <OrderItem />                  // cancel button per order
            </OrderList>
            <OrderPlacementForm />           // place new order
          </OrderPanel>
        </Dashboard>
      </OKXWsProvider>
    </KrakenWsProvider>
  </OrderEventsProvider>
</QueryClientProvider>
```

**DashboardHeader** — reads `connectionStatus` from both orderbook WS contexts AND `orderEventsStatus` from `OrderEventsProvider`. Shows a colored dot per exchange for each connection type.

**OrderbookRow** — consumes the exchange's WS context to read `orderbook[pair]`. Renders bid/ask levels and spread. On click, opens `OrderPanel` for that exchange/pair.

**OrderPanel** — mounts `useOrders(exchange, pair)`. Renders `OrderList` and `OrderPlacementForm`. This is where React Query's automatic refetch on invalidation becomes visible — when the order events provider invalidates the query key, this component's data refreshes.

**OrderList** — maps over orders from `useOrders`. Each `OrderItem` shows order details and a cancel button wired to `useCancelOrder`.

**OrderPlacementForm** — controlled form with client-side validation (inline errors, no toast). Calls `usePlaceOrder` on submit. Disabled during pending mutation. Toasts on REST errors per the error taxonomy.

### 10. Error Handling

**Connection Errors (WebSocket)**:
- Orderbook WS: per-exchange status indicator in `DashboardHeader`. Auto-reconnect with backoff. Toast on final failure after 3 retries.
- Order events WS: separate status indicator in `DashboardHeader`. If the backend's connection to the exchange drops, the backend pushes a `status` event with `"disconnected"`, and the frontend shows a stale-feed warning. The user should know their order updates may be delayed.

**Request Errors (REST)**:
- 4xx: toast error immediately with message ("Insufficient balance", "Order not found", etc.)
- 5xx / timeout: refetch orders silently first (the operation may have succeeded), then toast with uncertainty message
- This applies to both place and cancel operations

**Validation Errors**:
- Client-side, in `OrderPlacementForm`
- Inline field errors, no toast
- Validated before any API call is made

---

## Implementation Order

Build in this sequence — each phase produces a testable increment:

### Phase 1: Backend — Private WS Relay
1. Implement OKX private WS client (auth, subscribe to orders channel, ping keepalive, reconnection)
2. Implement `OrderEventRelay` (client registry, reference counting, fan-out, status broadcasting)
3. Update `models.py` with event schemas
4. Rewrite `routes/orders.py` — WS endpoint wired to relay, REST endpoints cleaned up with proper per-pair fetching
5. Update `app.py` lifespan to wire everything together
6. **Test**: connect with a WS client tool, verify order events stream through

### Phase 2: Frontend — React Query + Order Events
1. Install `@tanstack/react-query` and `react-hot-toast`
2. Add order types (`types/orders.ts`)
3. Add API client (`api/orders.ts`)
4. Set up `QueryClientProvider` in `main.tsx`
5. Build `OrderEventsProvider` with batched invalidation
6. Build React Query hooks (`useOrders`, `usePlaceOrder`, `useCancelOrder`)
7. **Test**: verify order data fetches and events trigger refetches

### Phase 3: Frontend — Orderbook WS Context Providers
1. Refactor `useOkxOrderbook` into `OKXWsProvider` context with multi-pair support
2. Refactor `useKrakenOrderbook` into `KrakenWsProvider` context with multi-pair support
3. Both expose `ExchangeContextValue` interface
4. **Test**: verify multiple pairs can be subscribed simultaneously on one connection

### Phase 4: Frontend — Component Tree
1. `useRowConfig` hook with localStorage persistence
2. `Dashboard` shell layout
3. `DashboardHeader` with connection status indicators
4. `RowConfigPanel` for adding/removing pairs
5. `OrderbookTable` + `OrderbookRow` (consuming WS context)
6. `OrderPanel` + `OrderList` + `OrderItem` (consuming React Query)
7. `OrderPlacementForm` with validation
8. Toast setup
9. **Test**: full end-to-end flow

### Phase 5: Error Handling Polish
1. Reconnection logic for all WS connections
2. REST error classification (4xx vs 5xx/timeout)
3. Ambiguous failure handling (refetch before surfacing error)
4. Connection status indicators wired to all sources
5. Stale-feed warnings when order events WS is down
