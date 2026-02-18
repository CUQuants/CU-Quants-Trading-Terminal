# CU Quants Terminal Bear — Project Specification

## Overview

A React-based trading dashboard that displays live orderbook data from Kraken and OKX via WebSocket subscriptions. Users can view top-of-book data for configured ticker pairs, manage open orders, place new orders, and cancel existing ones.

---

## Tech Stack

- **React + TypeScript**
- **React Query** — REST state management (orders, placement, cancellation)
- **React Context** — Live orderbook state per exchange
- **WebSocket** — Live orderbook subscriptions (one connection per exchange)
- **localStorage** — Row configuration persistence
- **Toast notifications** — Error and status feedback

---

## Pair Normalization

All ticker pairs are represented internally in `BASE/QUOTE` format (e.g. `BTC/USD`, `ETH/USD`).

Each exchange adapter is responsible for translating to and from its native format:

| Internal Format | Kraken Native | OKX Native |
| --------------- | ------------- | ---------- |
| `BTC/USD`       | `XBT/USD`     | `BTC-USDT` |
| `ETH/USD`       | `ETH/USD`     | `ETH-USDT` |

Translation happens within each specific exchange service. The rest of the app only ever sees the normalized format.

---

## Row Configuration

Row configuration is persisted to `localStorage` under the key `terminal_bear_config`. This way, when a user logs on another time, the browser will remember which rows and exchanges a user wants to view.

### Schema

```ts
interface RowConfig {
  version: number; // increment on schema changes for migration
  exchanges: {
    kraken: string[]; // normalized pair strings e.g. ["BTC/USD", "ETH/USD"]
    okx: string[];
  };
}
```

Users can add or remove pairs per exchange. The dashboard renders one row per pair per exchange based on this config.

---

## Architecture

### WebSocket Connection Managers

One connection manager per exchange, implemented as React context providers. They own the WebSocket lifecycle and expose a common interface to the rest of the app.

**Placement in component tree:**

```
<KrakenWsProvider>
  <OKXWsProvider>
    <App />
  </OKXWsProvider>
</KrakenWsProvider>
```

#### Reconnection Strategy

- On disconnect, attempt reconnect with exponential backoff
- Maximum of **3 retries**
- On all retries exhausted, set `connectionStatus` to `'failed'` and toast an error to the user
- Connection status is visible in the UI per exchange

#### Timed UI Updates

Raw WebSocket messages update an internal ref immediately. The React context state (and therefore UI) is updated on a **500ms interval**. This is done to prevent issues from highly frequent re-rendering.

```ts
// Pseudocode
const orderbookRef = useRef<Record<string, OrderbookSnapshot>>({});

useEffect(() => {
  const interval = setInterval(() => {
    setOrderbook({ ...orderbookRef.current });
  }, 500);
  return () => clearInterval(interval);
}, []);
```

---

## Exchange Context Interface

Both `KrakenWsContext` and `OKXWsContext` expose the same interface:

```ts
interface ExchangeContextValue {
  // Connection
  connectionStatus:
    | "connecting"
    | "connected"
    | "reconnecting"
    | "disconnected"
    | "failed";
  lastUpdated: Date | null;

  // Orderbook
  orderbook: Record<string, OrderbookSnapshot>;

  // Subscription management
  subscribe(pair: string): void;
  unsubscribe(pair: string): void;
  subscribedPairs: string[];
}
```

There will be one Webocket connection per exchange. Within each exchange connection, you are able to dynamically subscribe and unsubscribe from tickers.

### Shared Types

```ts
interface OrderbookSnapshot {
  bids: PriceLevel[];
  asks: PriceLevel[];
  timestamp: Date;
}

interface PriceLevel {
  price: number;
  size: number;
}
```

The contexts expose **only** WebSocket concerns, which involve displaying live data to the UI. REST operations (order placement, cancellation, fetching) live exclusively in React Query hooks.

---

## Exchange Adapter Interface

Each exchange implements a common adapter contract. This is the boundary between exchange-specific logic and the rest of the app.

```ts
interface ExchangeAdapter {
  // Pair normalization
  toNativePair(pair: string): string;
  fromNativePair(nativePair: string): string;

  // WebSocket
  buildSubscribeMessage(pairs: string[]): unknown;
  buildUnsubscribeMessage(pairs: string[]): unknown;
  parseOrderbookMessage(
    raw: unknown,
  ): { pair: string; snapshot: OrderbookSnapshot } | null;

  // REST (used by React Query hooks)
  fetchOrders(pair: string): Promise<Order[]>;
  placeOrder(params: OrderParams): Promise<OrderResult>;
  cancelOrder(orderId: string, pair: string): Promise<void>;
}
```

Exchange-specific logic (auth, signing, message format) is fully contained within each adapter. The context providers and React Query hooks program against this interface only. The specific implementations for authentication and subscribing are still to be figured out.

---

## REST — React Query Hooks

All REST operations use React Query. The WebSocket is never used as the source of truth for order state.

### `useOrders(exchange, pair)`

Fetches open orders for a given exchange and pair.

```ts
function useOrders(
  exchange: "kraken" | "okx",
  pair: string,
): UseQueryResult<Order[]>;
```

- Fetches on mount
- Exposes a `refetch()` function which will be called after the responses from placing and cancelling orders. This helps prevent the issue of stale data
- When a websocket receives that an order has been filled, `refetch()` is called rather than mutating local state directly

### `usePlaceOrder(exchange)`

```ts
function usePlaceOrder(
  exchange: "kraken" | "okx",
): UseMutationResult<OrderResult, Error, OrderParams>;
```

- No optimistic updates — waits for confirmed REST response
- On success: triggers `useOrders` refetch for that exchange/pair combination
- On ambiguous failure (timeout, 5xx): refetches orders before surfacing error to user
- On clear failure (4xx): surfaces error immediately via toast

### `useCancelOrder(exchange)`

```ts
function useCancelOrder(
  exchange: "kraken" | "okx",
): UseMutationResult<void, Error, { orderId: string; pair: string }>;
```

- No optimistic updates
- On success: triggers `useOrders` refetch
- On ambiguous failure: refetches orders before surfacing error — cancel may have succeeded
- On clear failure: surfaces error immediately via toast

### Shared Types

```ts
interface Order {
  id: string;
  pair: string; // normalized BASE/QUOTE
  side: "buy" | "sell";
  type: "limit" | "market";
  price?: number;
  size: number;
  status: string;
  createdAt: Date;
}

interface OrderParams {
  pair: string; // normalized BASE/QUOTE
  side: "buy" | "sell";
  type: "limit" | "market";
  price?: number; // required for limit orders
  size: number;
}

interface OrderResult {
  orderId: string;
}
```

---

## Error Taxonomy

Errors are categorized into three types with distinct UX handling:

### Connection Errors (WebSocket)

- Source: WebSocket disconnect, failed reconnect
- UX: Per-exchange status indicator in dashboard header updates to `reconnecting` or `failed`; toast on final failure after 3 retries
- Recovery: Automatic reconnect with backoff; manual retry option in UI

### Request Errors (REST 4xx / 5xx)

- Source: Order placement, cancellation, or fetch API calls
- **4xx (clear failure):** Toast error immediately with message (e.g. "Insufficient balance", "Order not found")
- **5xx / timeout (ambiguous failure):** Refetch orders silently first, then toast with message indicating the outcome is uncertain
- Recovery: User-initiated retry

### Validation Errors

- Source: Client-side form validation before API call is made
- UX: Inline form field errors, no toast
- Recovery: User corrects input

---

## UI Component Tree

```
<App>
  <KrakenWsProvider>
    <OKXWsProvider>
      <ToastProvider>
        <Dashboard>
          <DashboardHeader>         // exchange connection status indicators
          <RowConfigPanel>          // add/remove pairs per exchange
          <OrderbookTable>
            <OrderbookRow>          // one per exchange/pair combination
              // displays: pair, exchange, bid levels, ask levels, spread
              // click to open OrderPanel
          <OrderPanel>              // slides in on row click
            <OrderList>
              <OrderItem>           // cancel button per order
            <OrderPlacementForm>    // place new order for this exchange/pair
```

### Key Component Responsibilities

**`OrderbookRow`** — Consumes exchange context to read the orderbook. Renders bid/ask levels. On click, opens `OrderPanel` for that exchange/pair.

**`OrderPanel`** — Renders `OrderList` and `OrderPlacementForm` for a specific exchange/pair. Mounts `useOrders` hook. Passes `refetch` down to child components.

**`OrderList`** — Displays open orders. Each `OrderItem` has a cancel button that calls `useCancelOrder` and triggers refetch on success.

**`OrderPlacementForm`** — Controlled form with client-side validation. Calls `usePlaceOrder` on submit. Disabled during pending mutation. Shows inline validation errors and toasts REST errors.

**`DashboardHeader`** — Reads `connectionStatus` from both exchange contexts and renders a visible indicator per exchange.

---

## Authentication & API Keys

API keys are never stored or used in the browser. All authenticated REST requests (order fetch, placement, cancellation) are proxied through a FastAPI server that holds keys in environment variables and handles the specific exchange request signing. 

The flow would be: The frontend sends requests to the proxy. The proxy attaches credentials and forwards to the exchange. In other words, when placing order and cancelling them, there is an intermediate FastAPI server that handles user authentication.

The exact implementation details for this will be specified later. In the meantime, think about any other approache that might be better.

---

## localStorage Schema Versioning

The `RowConfig` schema includes a `version` field. On app load, if the stored version does not match the current expected version, the stored config is migrated or reset with a user-facing notice.

---

## Out of Scope for now

- Order history / trade history
- P&L tracking
- Charting
- Mobile layout
- Multiple accounts per exchange
