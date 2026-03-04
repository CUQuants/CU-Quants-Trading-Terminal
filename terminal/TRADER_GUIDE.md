# Trader Guide: Running the QuantX Trading Terminal

This guide explains how to run the trading terminal, configure OKX credentials, and use Docker.

---

## Quick Start (Docker)

From the `terminal` directory:

```bash
docker compose up --build
```

- **Backend API**: http://localhost:8000  
- **Frontend dashboard**: http://localhost:3000  

---

## OKX Environment Variables

Create a `.env` file in `terminal/backend/` with the following keys.

### Live Trading

| Variable | Description |
|----------|-------------|
| `OKX_API_KEY` | Your OKX API key (live) |
| `OKX_API_SECRET` | Your OKX API secret (live) |
| `OKX_API_PASSPHRASE` | The passphrase you set when creating the API key |

### Simulated / Demo Trading

When `SIMULATED=True`, the backend uses these keys instead. Use OKX’s demo/simulated trading credentials.

| Variable | Description |
|----------|-------------|
| `OKX_API_KEY_SIMULATED` | OKX demo API key |
| `OKX_API_SECRET_SIMULATED` | OKX demo API secret |
| `OKX_API_PASSPHRASE_SIMULATED` | Passphrase for the demo API key |

### Dev Mode Flag: `SIMULATED`

| Value | Behavior |
|-------|----------|
| `SIMULATED=True` | Uses `*_SIMULATED` keys and OKX’s demo WebSocket (`wss://wsuspap.okx.com`). No real orders or funds. |
| `SIMULATED=False` | Uses live keys and live OKX endpoints. Real orders and real funds. |

**Example `.env`:**

```env
# Live credentials (used when SIMULATED=False)
OKX_API_KEY=your-live-api-key
OKX_API_SECRET=your-live-api-secret
OKX_API_PASSPHRASE=your-passphrase

# Demo credentials (used when SIMULATED=True)
OKX_API_KEY_SIMULATED=your-demo-api-key
OKX_API_SECRET_SIMULATED=your-demo-api-secret
OKX_API_PASSPHRASE_SIMULATED=your-demo-passphrase

# Set to True for paper trading, False for live
SIMULATED=True
```

**Security:** Never commit `.env` or share your keys. `.env` is in `.gitignore`.

---

## Docker Basics

### Installing Docker

1. **macOS / Windows:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. **Linux:** Use your package manager, e.g.:
   - Ubuntu/Debian: `sudo apt install docker.io docker-compose-plugin`
   - Fedora: `sudo dnf install docker docker-compose-plugin`

After install, start the Docker service and confirm it works:

```bash
docker --version
docker compose version
```

### Running the Terminal

You must be in the `terminal` directory when running Docker Compose, since it looks for `docker-compose.yml` in the current folder:

```bash
cd terminal
docker compose up --build
```

If you’re already in the project root, use `cd terminal` first. Once running, the frontend is at http://localhost:3000 and the backend at http://localhost:8000.

### Common Commands

| Command | Description |
|---------|-------------|
| `docker compose up --build` | Build images and start all services. Use `--build` when code or dependencies change. |
| `docker compose up -d` | Run in the background (detached). |
| `docker compose down` | Stop and remove containers. |
| `docker compose logs -f` | Stream logs from all services. |
| `docker compose logs -f backend` | Stream logs from the backend only. |

### How `docker compose up --build` Works

- Reads `docker-compose.yml` in the current directory.
- Builds images for `backend` and `frontend` from their `Dockerfile`s.
- Starts containers and maps ports (8000 for backend, 3000 for frontend).
- Loads `backend/.env` into the backend container.
- `--build` forces a rebuild of images before starting (needed after code changes).

---

## Frontend Environment (Optional)

The dashboard uses `VITE_API_URL` to reach the backend. Default: `http://localhost:8000`.

If your backend runs elsewhere (e.g. another host or port), create `dashboard_v2/.env`:

```env
VITE_API_URL=http://your-backend-host:8000
```

---

## Troubleshooting

- **Backend won’t start:** Ensure `backend/.env` exists and contains valid OKX keys.
- **Frontend can’t reach backend:** Check `VITE_API_URL` and that the backend is running on that URL.
- **Docker build fails:** Run `docker compose down` and `docker compose up --build` again.
- **Port already in use:** Stop other services on 3000 or 8000, or change ports in `docker-compose.yml`.
