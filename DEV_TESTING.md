# Testing the terminal in dev (local, no Docker)

End-to-end local loop: a local CU Quants **gateway** in OKX-simulated mode, the
terminal **backend**, and the **dashboard** — all on `localhost`, no Docker for
the terminal, no real funds. OKX trading is routed through the gateway; Kraken
still calls direct.

```
dashboard :5173  ──HTTP/WS──▶  backend :8000  ──proxy_client──▶  gateway :8080  ──▶  OKX demo
```

## Prerequisites

- The **`trading-gateway`** repo checked out next to this one (`../trading-gateway`).
- **Docker running** — the *gateway* needs it for its throwaway Postgres. The
  terminal itself does not.
- **`uv`** and **Node.js 20+ / npm**.
- An **OKX demo** key/secret/passphrase in `../trading-gateway/.env.sandbox`
  (see that repo's `SANDBOX_INTEGRATION.md`).

## 1 — Start the gateway

```bash
cd ../trading-gateway
scripts/dev-gateway.sh up
```

Leave it running. It brings up Postgres, seeds a registry, issues credentials,
and runs the Proxy on `http://127.0.0.1:8080` with `OKX_SIMULATED=1` and the
OKX demo WebSocket host. Then, in another shell:

```bash
scripts/dev-gateway.sh creds        # prints .env.dev-credentials
```

## 2 — Configure the terminal backend

```bash
cd ../CU-Quants-Trading-Terminal
cp backend/.env.example backend/.env
```

Fill in `backend/.env` from the gateway's creds output. **The names differ** —
map them:

| `backend/.env` (terminal's name) | value / source |
|---|---|
| `CUQ_PROXY_URL` | `http://127.0.0.1:8080` |
| `CUQ_PROXY_API_KEY` | gateway's `CUQ_OPERATOR_API_KEY` |
| `CUQ_PROXY_SECRET` | gateway's `CUQ_OPERATOR_API_SECRET` |
| `CUQ_PROXY_OPERATOR_ID` | gateway's `CUQ_OPERATOR_ID` (`cuq-002`) |
| `CUQ_PROXY_OPERATOR_NAME` | gateway's `CUQ_OPERATOR_NAME` |

All five are mandatory — the backend builds `ServiceContainer` at startup and
won't boot without them. Leave `CUQ_PROXY_WS_URL` unset; the SDK derives
`ws://127.0.0.1:8080/v1/okx/ws` from `CUQ_PROXY_URL`.

Kraken still calls direct — set `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` if you'll
open a Kraken view; leave blank for OKX-only testing.

## 3 — Run backend + frontend

```bash
scripts/dev-local.sh
```

Runs both natively, no Docker, and tears both down on Ctrl-C:

- backend  — `http://127.0.0.1:8000` (reads `backend/.env`)
- dashboard — `http://127.0.0.1:5173`

The script checks `backend/.env` has the five `CUQ_PROXY_*` vars and pings the
gateway's `/healthz` first (warns if it's down). First run does `uv sync` and
`npm install`; `SKIP_INSTALL=1` skips that. Override ports with `BACKEND_PORT` /
`FRONTEND_PORT` (the frontend is pointed at the backend via `VITE_API_URL`
automatically).

## 4 — Smoke-test the chain

Before opening the UI:

```bash
curl -s localhost:8000/account/balances/okx | head -c 400
```

A balance JSON means the whole path works: SDK signing → gateway auth → action
allowlist → `x-simulated-trading: 1` → OKX demo → audit row.

## 5 — Place a test order

In the dashboard: select **OKX**, place a **limit** buy on BTC/USD well below
market (e.g. `0.001 @ 1000`) so it rests. Expect:

- it shows up in pending orders — order events arrive over
  `ws://localhost:8000/orders/okx`, which the backend relays from the gateway's
  `ws://127.0.0.1:8080/v1/okx/ws`
- cancelling it removes it
- the gateway shell logs one line per request

It's OKX's demo book — no real funds move.

## 6 — Query the audit log (optional)

The gateway's read-only audit-reporting API is a separate process on its
own port. In a third shell:

```bash
cd ../trading-gateway
scripts/dev-gateway.sh report
```

Add one line to `backend/.env` — the existing `CUQ_PROXY_*` operator
credential already has `admin_role='auditor'` (`dev-gateway.sh`'s
`seed_registry`), so no new credential is needed:

```
CUQ_REPORTING_URL=http://127.0.0.1:8090
```

Restart `scripts/dev-local.sh` (or just the backend) to pick it up, then:

```bash
curl -s localhost:8000/reporting/health | head -c 400
curl -s "localhost:8000/reporting/logs?limit=5"
```

A JSON body means the chain works end to end. Place an order (step 5) and
it shows up in `/reporting/logs` immediately, and in
`/reporting/unresolved` if OKX's ack/fill hasn't come back yet. In the
dashboard, open the **Reporting** tab for the same views with filters.
Leaving `CUQ_REPORTING_URL` unset is fine — trading still works, and
`/reporting/*` returns `503` instead.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ProxyConfigError: ... cannot start without: CUQ_PROXY_*` | `backend/.env` missing or misnamed vars (see the mapping table above), or uvicorn launched from outside `backend/` — bare `load_dotenv()` searches up from the cwd. `scripts/dev-local.sh` handles this. |
| backend 5xx on `/account/*` or `/orders/*`, gateway logs nothing | gateway not running — `cd ../trading-gateway && scripts/dev-gateway.sh up` |
| `EXCHANGE_ERROR`, OKX code `50119` / `60032` "API key doesn't exist" | the demo key is on the wrong OKX platform (US vs international) — see `trading-gateway/SANDBOX_INTEGRATION.md` |
| order rejected for size / price tick | adjust size or price; not a wiring problem |
| dashboard loads but OKX order status shows "disconnected" | backend order-event relay or the gateway's WS upstream is down — check both shells |
| `--strictPort` error on start | `5173` (or your `FRONTEND_PORT`) is in use — free it or set a different `FRONTEND_PORT` |

## What is NOT covered

For News contracts and its manual browser checklist, see
[News frontend and backend contract](docs/NEWS_API.md). The current backend does
not implement the news endpoints, so News displays an unavailable state until
integration. Frontend checks remain `npm run lint`, `npm run build`, and manual
browser verification; there are no news mocks or automated integration tests.

- `docker compose up` — that path still works for a containerised run, but a
  backend container can't reach a gateway on the host's `127.0.0.1:8080`
  without `host.docker.internal` rewiring. Use `scripts/dev-local.sh` for local
  gateway testing.
- Real (non-simulated) trading — that's a property of the gateway you point at,
  never a terminal setting.
