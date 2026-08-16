# CU Quants Trading Terminal

A web-based trading terminal for connecting to and trading on multiple crypto exchanges (OKX, Kraken, Gemini) from a single dashboard.

## Structure

```
.
├── backend/          FastAPI service — exchange integrations, orders, trades, account data
├── dashboard_v2/      React + Vite dashboard — the UI
├── docker-compose.yml
├── TRADER_GUIDE.md   Setup, environment variables, and Docker usage
└── docs/             Design notes and specs
```

## Quick Start

```bash
docker compose up --build
```

- Backend API: http://localhost:8000
- Dashboard: http://localhost:3000

See [TRADER_GUIDE.md](./TRADER_GUIDE.md) for exchange API credentials, environment variables, and troubleshooting.

## Running without Docker

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Dashboard**
```bash
cd dashboard_v2
npm install
npm run dev
```

## What it does

- Streams live order books and trades from OKX, Kraken, and Gemini
- Places and cancels orders, and tracks order status over a websocket relay
- Shows account balances and positions per exchange
- Supports simulated/demo trading mode for OKX
