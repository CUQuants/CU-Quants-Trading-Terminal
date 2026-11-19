# Trader Guide: Running the CU Quants Trading Terminal

This guide covers configuration in detail: environment variables, exchanges,
and troubleshooting. **To install and run the terminal, follow
[Getting started in the README](./README.md#getting-started-traders)** (one
command: `scripts/dev-local.sh`, dashboard at http://localhost:5173).

---

## Signing in

The terminal's first page asks for your gateway operator credential: the four
`proxy:` values from your xlrts `config.yaml` (`api_key`, `api_secret`,
`operator_id`, `operator_name`).
- Each trader signs in with their own credential, so every request is
  attributed to that trader in the gateway's audit log.
- The secret is held only in the terminal server's memory while you're signed
  in.

See [Signing in](./README.md#signing-in) for details.

## Environment Variables

`backend/.env` holds **server settings only**; there are no trader credentials
in it. See `backend/.env.example` for a template.

### OKX — through the CU Quants Proxy

The terminal holds **no OKX keys**. Every OKX call goes through the CU Quants
Trading Gateway ("the Proxy"). The gateway holds the club's vaulted OKX key,
enforces the action allowlist, and audits every request, signed with the
credential of whichever trader is signed in.

| Variable | Description |
|----------|-------------|
| `CUQ_PROXY_URL` | Base URL of the gateway, e.g. `https://178-105-55-5.sslip.io` (on the gateway's own box: `http://127.0.0.1:8080`) |
| `CUQ_PROXY_WS_URL` | *(optional)* explicit `wss://` base; omit to derive it from `CUQ_PROXY_URL` |
| `TERMINAL_COOKIE_SECURE` | *(default `true`)* mark the session cookie Secure; `false` only for plain-http local dev |
| `TERMINAL_SESSION_IDLE_HOURS` / `TERMINAL_SESSION_MAX_HOURS` | *(default 12 / 24)* sign-out after idle / absolute |
| `TERMINAL_ALLOWED_ORIGINS` | *(optional)* extra browser origins, comma-separated; same-origin is always allowed |

### Audit reporting (optional)

The **Reporting** tab reads the gateway's read-only audit-log API
(`proxy_admin.reporting` — a separate process from the Proxy, its own port,
no reverse-proxy route). It is signed with the credential you signed in with;
only the URL is server config, and your operator needs `admin_role='auditor'`
on the gateway (ask whoever issued your credential).

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

Goes through the Proxy too, to the club's **Kraken Prime** account (gateway
exchange `kraken_prime`). The terminal holds no Kraken keys; your sign-in
credential covers it.

What works for now: placing and cancelling orders, open orders, and balances.
Not yet: fill history (the Trades view is empty for Kraken) and live order
updates. Open orders and balances refresh after each order you place or cancel
in the terminal; anything that changes outside it (a fill, an order cancelled
elsewhere) shows up on the next refresh.

**Example `.env`:**

```env
CUQ_PROXY_URL=http://localhost:8100
```

**Security:** Never commit `.env` or share your keys. `.env` is in `.gitignore`.
If an old `backend/.env` still has `CUQ_PROXY_API_KEY` / `CUQ_PROXY_SECRET` /
`CUQ_PROXY_OPERATOR_*` lines, delete them. They're no longer read.

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

Once running, open the dashboard at http://localhost:3000 and sign in. (It
reaches the backend through the Vite server's `/api` proxy; the backend's own
:8000 is not meant to be opened in a browser.)

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

The dashboard calls the backend at `/api` on its own origin. Vite proxies that
to `BACKEND_URL` (default `http://localhost:8000`) in dev, and Caddy proxies it
in production. Same-origin is what makes the HttpOnly session cookie work, so
there is normally nothing to set.

`VITE_API_URL` still overrides the base at build time, but pointing it at
another origin also needs that origin in the backend's
`TERMINAL_ALLOWED_ORIGINS`, and a cookie setup that works cross-site. Avoid it.

---

## Troubleshooting

- **Backend won’t start:** Ensure `backend/.env` exists and sets `CUQ_PROXY_URL`. Without it, startup aborts with a message saying so.
- **Sign-in rejected ("did not accept these credentials"):** the API key, secret or operator ID is wrong, or your computer's clock is more than 5 s off. The gateway gives the same answer for all of these. The message includes the gateway's `request_id` for whoever runs it.
- **"Can't reach the trading gateway" at sign-in:** the backend can't reach `CUQ_PROXY_URL`. Check it, and check that the gateway's `/healthz` answers.
- **Reporting tab shows "not configured" (`503`):** `CUQ_REPORTING_URL` is unset — this is expected until you add it; it does not stop the rest of the terminal from working.
- **Reporting tab / API returns `403 ACTION_NOT_PERMITTED`:** your operator authenticated fine but isn't authorized to view the audit log — ask whoever issued your credential to grant `admin_role='auditor'`.
- **Frontend can’t reach backend:** Check that the backend is running where Vite's `BACKEND_URL` points (default `http://localhost:8000`), and that you opened the dashboard on the Vite port.
- **Docker build fails:** Run `docker compose down` and `docker compose up --build` again.
- **Port already in use:** Stop other services on 3000 or 8000, or change ports in `docker-compose.yml`.
