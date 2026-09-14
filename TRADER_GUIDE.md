# Trader Guide: Running the QuantX Trading Terminal

This guide explains how to run the trading terminal, configure OKX credentials, and use Docker.

---

## Quick Start (Docker)

From the repo root:

```bash
docker compose up --build
```

- **Backend API**: http://localhost:8000  
- **Frontend dashboard**: http://localhost:3000  

---

## Environment Variables

Create a `.env` file in `backend/` (see `backend/.env.example` for a template).

### OKX — through the CU Quants Proxy

The terminal holds **no OKX keys**. Every OKX call goes through the CU Quants
Trading Gateway ("the Proxy"), which holds the club's vaulted OKX key, enforces
the action allowlist, and audits every request. You need an **operator
credential** from the Proxy (see `trading-gateway/NEW-USER.md`).

| Variable | Description |
|----------|-------------|
| `CUQ_PROXY_URL` | Base URL of the gateway, e.g. `https://your-gateway-host.example` |
| `CUQ_PROXY_API_KEY` | Your operator API key (`cuq_op_...`) |
| `CUQ_PROXY_SECRET` | The secret paired with that key — read at startup, never stored |
| `CUQ_PROXY_OPERATOR_ID` | Your operator id, e.g. `cuq-014` |
| `CUQ_PROXY_OPERATOR_NAME` | Your name, for the audit log |
| `CUQ_PROXY_WS_URL` | *(optional)* explicit `wss://` base; omit to derive it from `CUQ_PROXY_URL` |

### Audit reporting (optional)

The **Reporting** tab reads the gateway's read-only audit-log API
(`proxy_admin.reporting` — a separate process from the Proxy, its own port,
no reverse-proxy route). It reuses the same `CUQ_PROXY_*` operator
credential above; only the URL is new, and your operator needs
`admin_role='auditor'` on the gateway (ask whoever issued your credential).

| Variable | Description |
|----------|-------------|
| `CUQ_REPORTING_URL` | *(optional)* base URL of the reporting API, e.g. `https://your-reporting-host.example` |

Leave it unset and the backend still starts normally — the Reporting tab
just shows "not configured" instead of data.

### Simulated vs. live

There is **no `SIMULATED` flag in the terminal any more.** Whether an order
reaches OKX's demo environment or the real one is decided by `OKX_SIMULATED` on
the gateway that `CUQ_PROXY_URL` points at, with demo credentials vaulted there.
To test against OKX's simulated environment, run a local gateway in that mode
(`OKX_SIMULATED=1` + OKX demo keys — see `trading-gateway/SANDBOX_INTEGRATION.md`)
and point `CUQ_PROXY_URL` at it.

### Kraken

Still called directly with `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` until its own
migration onto the Proxy.

**Example `.env`:**

```env
CUQ_PROXY_URL=http://localhost:8100
CUQ_PROXY_API_KEY=cuq_op_...
CUQ_PROXY_SECRET=...
CUQ_PROXY_OPERATOR_ID=cuq-014
CUQ_PROXY_OPERATOR_NAME=J. Rivera

KRAKEN_API_KEY=...
KRAKEN_API_SECRET=...
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

Run Docker Compose from the repo root, since it looks for `docker-compose.yml` in the current folder:

```bash
docker compose up --build
```

Once running, the frontend is at http://localhost:3000 and the backend at http://localhost:8000.

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

If your backend runs elsewhere (e.g. another host or port), create `frontend/.env`:

```env
VITE_API_URL=http://your-backend-host:8000
```

---

## Troubleshooting

- **Backend won’t start:** Ensure `backend/.env` exists and sets all five `CUQ_PROXY_*` variables. A missing one aborts startup with a message naming it. Also confirm the gateway at `CUQ_PROXY_URL` is reachable.
- **Reporting tab shows "not configured" (`503`):** `CUQ_REPORTING_URL` is unset — this is expected until you add it; it does not stop the rest of the terminal from working.
- **Reporting tab / API returns `403 ACTION_NOT_PERMITTED`:** your operator authenticated fine but isn't authorized to view the audit log — ask whoever issued your credential to grant `admin_role='auditor'`.
- **Frontend can’t reach backend:** Check `VITE_API_URL` and that the backend is running on that URL.
- **Docker build fails:** Run `docker compose down` and `docker compose up --build` again.
- **Port already in use:** Stop other services on 3000 or 8000, or change ports in `docker-compose.yml`.
