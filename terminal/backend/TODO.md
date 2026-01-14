# Backend TODO - Trading Terminal API Server

## Overview
Build a backend API server to handle all Kraken API interactions, WebSocket connections, and business logic. The frontend should communicate with this backend via REST/WebSocket rather than directly with Kraken.

---

## Architecture Requirements

### 1. **API Server Framework**
- [ ] Set up a Python FastAPI or Flask server
- [ ] Configure CORS for frontend communication
- [ ] Set up environment-based configuration (.env file)
- [ ] Implement proper error handling and logging
- [ ] Add request/response validation using Pydantic models

### 2. **Kraken API Integration**
- [ ] **REST API Wrapper**
  - [ ] Implement authenticated Kraken REST API client
  - [ ] Handle HMAC-SHA512 signature generation
  - [ ] Manage API key/secret securely (environment variables)
  - [ ] Implement rate limiting (15 calls per 3 seconds)
  - [ ] Add retry logic with exponential backoff
  - [ ] Cache public data (ticker, order book) appropriately

- [ ] **WebSocket Integration**
  - [ ] Manage Kraken public WebSocket connections
  - [ ] Manage Kraken private (authenticated) WebSocket connections
  - [ ] Handle WebSocket reconnection logic
  - [ ] Multiplex WebSocket subscriptions (multiple clients, single connection)
  - [ ] Implement heartbeat/ping-pong mechanism

### 3. **API Endpoints to Implement**

#### Public Endpoints (No Authentication Required)
- [ ] `GET /api/ticker/{pair}` - Get ticker information for a pair
- [ ] `GET /api/orderbook/{pair}` - Get order book for a pair
- [ ] `GET /api/trades/{pair}` - Get recent trades for a pair
- [ ] `GET /api/pairs` - Get list of available trading pairs
- [ ] `GET /api/assets` - Get list of available assets

#### Private Endpoints (Require API Key Authentication)
- [ ] `GET /api/orders/open` - Get open orders
- [ ] `POST /api/orders` - Place a new order
  - Request body: `{ pair, type, ordertype, volume, price? }`
- [ ] `DELETE /api/orders/{txid}` - Cancel specific order
- [ ] `DELETE /api/orders` - Cancel all orders
- [ ] `GET /api/balance` - Get account balance
- [ ] `GET /api/trades/history` - Get trade history
- [ ] `GET /api/ledger` - Get ledger info

#### WebSocket Endpoints
- [ ] `WS /ws/ticker` - Real-time ticker updates
  - Subscribe/unsubscribe to pairs via WebSocket messages
- [ ] `WS /ws/orderbook` - Real-time order book updates
- [ ] `WS /ws/trades` - Real-time trade feed
- [ ] `WS /ws/orders` - Real-time order updates (private, authenticated)

### 4. **Authentication & Security**
- [ ] Implement API key management
  - [ ] Store user API keys securely (encrypted in database or session)
  - [ ] Never expose Kraken API keys in responses
- [ ] Add authentication middleware for private endpoints
- [ ] Implement session management or JWT tokens
- [ ] Add input validation and sanitization
- [ ] Implement rate limiting per client
- [ ] Add HTTPS/TLS support for production

### 5. **Data Management**
- [ ] **Caching Strategy**
  - [ ] Cache public market data (ticker, order book) with TTL
  - [ ] Use Redis or in-memory cache
  - [ ] Implement cache invalidation logic

- [ ] **Database** (Optional but Recommended)
  - [ ] Store user preferences
  - [ ] Store API credentials (encrypted)
  - [ ] Log order history
  - [ ] Store watchlist pairs

### 6. **WebSocket Server**
- [ ] Set up WebSocket server (Socket.IO or native WebSockets)
- [ ] Manage client subscriptions
- [ ] Broadcast Kraken updates to subscribed clients
- [ ] Handle client disconnection/reconnection
- [ ] Implement subscription management (add/remove pairs)

### 7. **Business Logic**
- [ ] **Order Management**
  - [ ] Validate order parameters before sending to Kraken
  - [ ] Track order status
  - [ ] Provide order analytics (fill rate, execution price, etc.)

- [ ] **Risk Management** (Future Enhancement)
  - [ ] Position size limits
  - [ ] Maximum order size validation
  - [ ] Daily loss limits

- [ ] **Portfolio Management** (Future Enhancement)
  - [ ] Calculate total portfolio value
  - [ ] Track P&L
  - [ ] Position tracking

### 8. **Error Handling & Logging**
- [ ] Implement comprehensive error handling
- [ ] Log all API requests/responses
- [ ] Log WebSocket events
- [ ] Create error response standardization
- [ ] Add monitoring/alerting for critical errors

### 9. **Testing**
- [ ] Unit tests for API endpoints
- [ ] Integration tests with Kraken API (using test credentials)
- [ ] WebSocket connection tests
- [ ] Load testing for concurrent clients
- [ ] Mock Kraken API for testing without real API calls

### 10. **Documentation**
- [ ] API documentation (OpenAPI/Swagger)
- [ ] WebSocket protocol documentation
- [ ] Setup and deployment guide
- [ ] Environment configuration guide
- [ ] Error code reference

---

## File Structure Suggestion

```
backend/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── README.md              # Backend setup instructions
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── public.py      # Public endpoints (ticker, orderbook, etc.)
│   │   ├── orders.py      # Order management endpoints
│   │   ├── account.py     # Account/balance endpoints
│   │   └── websocket.py   # WebSocket endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py    # Pydantic request models
│   │   └── responses.py   # Pydantic response models
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py        # Authentication middleware
│       └── rate_limit.py  # Rate limiting middleware
├── services/
│   ├── __init__.py
│   ├── kraken_rest.py     # Kraken REST API client
│   ├── kraken_ws.py       # Kraken WebSocket client
│   ├── cache.py           # Caching service
│   └── websocket_manager.py  # WebSocket connection manager
├── utils/
│   ├── __init__.py
│   ├── logger.py          # Logging configuration
│   ├── crypto.py          # Cryptographic utilities (HMAC signing)
│   └── validators.py      # Input validation utilities
└── tests/
    ├── __init__.py
    ├── test_api.py
    ├── test_kraken_rest.py
    └── test_websocket.py
```

---

## Dependencies (requirements.txt)

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-dotenv==1.0.0
pydantic==2.5.0
requests==2.31.0
cryptography==41.0.7
redis==5.0.1
aioredis==2.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

---

## Frontend Changes Required

Once the backend is implemented, the frontend needs to:

1. **Remove Direct Kraken Integration**
   - Delete or stub out `krakenAPI.ts` and `krakenWebSocket.ts`
   
2. **Create Backend API Client**
   - Create `backendAPI.ts` to communicate with the new backend
   - All API calls go to `http://localhost:8000/api/*` instead of Kraken directly

3. **Update WebSocket Connection**
   - Connect to `ws://localhost:8000/ws/*` instead of Kraken WebSocket
   - Update subscription/unsubscription logic

4. **Remove Crypto Dependencies**
   - No need for CryptoJS in frontend
   - API key/secret handled by backend only

5. **Update Configuration**
   - Remove API key/secret from frontend localStorage
   - Only store backend session token or JWT

---

## Priority Order

### Phase 1 - Core Infrastructure (Week 1)
1. Set up FastAPI server
2. Implement Kraken REST API client with authentication
3. Create basic public endpoints (ticker, orderbook)
4. Add error handling and logging

### Phase 2 - Private Endpoints (Week 2)
1. Implement authentication middleware
2. Create private endpoints (orders, balance)
3. Add order placement and cancellation
4. Implement rate limiting

### Phase 3 - WebSocket (Week 3)
1. Set up WebSocket server
2. Integrate Kraken WebSocket client
3. Implement subscription management
4. Add real-time data broadcasting

### Phase 4 - Polish & Deploy (Week 4)
1. Add caching layer
2. Write tests
3. Create API documentation
4. Deploy to production server

---

## Notes

- **Security**: Never commit API keys to git. Use .env files and .gitignore.
- **Rate Limiting**: Kraken has strict rate limits. Implement proper queuing and caching.
- **WebSocket**: Consider using Socket.IO for easier client reconnection handling.
- **Monitoring**: Add health check endpoints for production monitoring.
- **Scalability**: Design for horizontal scaling if needed (multiple backend instances).

---

## Current Frontend Services to Replace

### `krakenAPI.ts` - Currently Handles:
- Direct REST API calls to Kraken
- HMAC-SHA512 signature generation
- Rate limiting (client-side)
- Credential management in localStorage
- Public endpoints: ticker, orderbook, trades
- Private endpoints: orders, balance, add/cancel orders

**Action**: All of this moves to backend. Frontend will call backend API instead.

### `krakenWebSocket.ts` - Currently Handles:
- WebSocket connection to Kraken (public and private)
- Subscription management
- Reconnection logic
- Heartbeat/ping-pong
- Real-time data parsing and distribution

**Action**: Backend will manage Kraken WebSocket. Frontend connects to backend WebSocket.

### Hooks to Update:
- `useOpenOrders.ts` - Call backend `/api/orders/open` instead
- `usePlaceOrder.ts` - Call backend `POST /api/orders` instead
- `useMarketTicker.ts` - Connect to backend `WS /ws/ticker` instead
- `useOrderBook.ts` - Connect to backend `WS /ws/orderbook` instead
- `useTrades.ts` - Connect to backend `WS /ws/trades` instead

---

## Questions to Answer

- [ ] Where should the backend be deployed? (Local, VPS, Cloud)
- [ ] Should we use a database or just in-memory state?
- [ ] How should API credentials be stored? (Session, encrypted DB, JWT claims)
- [ ] What authentication mechanism? (Session cookies, JWT, API keys)
- [ ] Should we implement user accounts or single-user mode?
- [ ] What caching strategy? (Redis, in-memory, hybrid)
- [ ] How to handle multiple users with different API keys?

---

## Success Criteria

✅ Backend can authenticate with Kraken API
✅ Frontend can place/cancel orders via backend
✅ Real-time ticker data flows from Kraken → Backend → Frontend
✅ Order updates are pushed to frontend in real-time
✅ API rate limiting prevents Kraken API errors
✅ Proper error handling and logging throughout
✅ No API keys stored in frontend
✅ All tests passing
✅ API documentation complete
