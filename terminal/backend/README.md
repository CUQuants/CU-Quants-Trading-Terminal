# Trading Terminal Backend

## Status: NOT IMPLEMENTED ⚠️

This backend server needs to be built to handle all Kraken API interactions for the trading terminal frontend.

## What This Backend Should Do

The frontend currently has stubbed-out API calls that return mock data. This backend server should:

1. **Handle Kraken API Authentication**
   - Store user API keys securely
   - Sign requests with HMAC-SHA512
   - Manage rate limiting (15 calls per 3 seconds)

2. **Provide REST API Endpoints**
   - Public: ticker data, order book, trades
   - Private: orders, balance, trade history

3. **Manage WebSocket Connections**
   - Connect to Kraken WebSocket feeds
   - Multiplex subscriptions for multiple clients
   - Push real-time data to frontend clients

4. **Security**
   - Never expose Kraken API keys to frontend
   - Implement authentication (session/JWT)
   - Validate all inputs

## Quick Start (Once Implemented)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python main.py
```

## Implementation Guide

See **[TODO.md](./TODO.md)** for the complete implementation checklist and architecture details.

## Current Status

- ✅ TODO.md created with full implementation plan
- ❌ Backend server not implemented
- ❌ Frontend uses stub services that return mock data

## Why This Separation?

**Security**: API keys should never be in the frontend/browser.  
**Rate Limiting**: Centralized rate limiting prevents API errors.  
**Caching**: Backend can cache public data to reduce API calls.  
**Scalability**: Multiple frontend clients can share one backend connection.

