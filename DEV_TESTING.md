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
- **`uv`** and **Node.js 22.12+ (or 20.19+) / npm** — see the README's install step.
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

In `backend/.env`, set only `CUQ_PROXY_URL=http://127.0.0.1:8080`. That is the
only required variable: the backend holds no trader credentials. Leave
`CUQ_PROXY_WS_URL` unset; the SDK derives `ws://127.0.0.1:8080/v1/okx/ws` from
`CUQ_PROXY_URL`.

The gateway's creds output is what you **type into the sign-in page**. The
names differ, so map them:

| Sign-in page field | gateway creds value |
|---|---|
| API key | `CUQ_OPERATOR_API_KEY` |
| API secret | `CUQ_OPERATOR_API_SECRET` |
| Operator ID | `CUQ_OPERATOR_ID` (`cuq-002`) |
| Operator name | `CUQ_OPERATOR_NAME` |

Kraken goes through the gateway too, as exchange `kraken_prime`. For the Kraken
view to place orders, the gateway needs `KRAKEN_PRIME_API_KEY`,
`KRAKEN_PRIME_API_SECRET` and `KRAKEN_PRIME_ACCOUNT_ID` set (see the gateway's
`.env.example`). Nothing Kraken-specific goes in the terminal's `.env`.

## 3 — Run backend + frontend

```bash
scripts/dev-local.sh
```

Runs both natively, no Docker, and tears both down on Ctrl-C:

- backend  — `http://127.0.0.1:8000` (reads `backend/.env`)
- dashboard — `http://localhost:5173` (Vite proxies `/api` to the backend, so
  the browser is same-origin with it, as it is through Caddy in production)

The script:
- checks that `backend/.env` sets `CUQ_PROXY_URL`, and warns about any leftover
  credential lines;
- pings the gateway's `/healthz` first and warns if it's down;
- runs the backend with `TERMINAL_COOKIE_SECURE=false`, since local dev is
  plain http.

The first run does `uv sync` and `npm install`; `SKIP_INSTALL=1` skips that.
Override ports with `BACKEND_PORT` / `FRONTEND_PORT`; the Vite proxy follows
`BACKEND_PORT` automatically.

## 4 — Smoke-test the chain

Before opening the UI, sign in with curl (the values come from the gateway's
creds output), then call a route using the session cookie:

```bash
curl -s -c /tmp/terminal.jar -H 'Content-Type: application/json' \
  -d '{"api_key":"cuq_op_…","api_secret":"…","operator_id":"cuq-002","operator_name":"Dev"}' \
  localhost:8000/auth/login
curl -s -b /tmp/terminal.jar localhost:8000/account/balances/okx | head -c 400
```

`/tmp/terminal.jar` now holds a live session cookie. Delete it when you're
done (`rm /tmp/terminal.jar`), or sign out with
`curl -s -b /tmp/terminal.jar -X POST localhost:8000/auth/logout`.

A balance JSON means the whole path works: sign-in → SDK signing (with your
credential) → gateway auth → action allowlist → `x-simulated-trading: 1` → OKX
demo → audit row. Without the cookie, every trading route answers `401
NOT_SIGNED_IN`.

## 5 — Place a test order

In the dashboard: select **OKX**, place a **limit** buy on BTC/USD well below
market (e.g. `0.001 @ 1000`) so it rests. Expect:

- it shows up in pending orders — order events arrive over
  `ws://localhost:5173/api/orders/okx` (Vite → backend `/orders/okx`, authenticated
  by your session cookie), which the backend relays from the gateway's
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
curl -s -b /tmp/terminal.jar localhost:8000/reporting/health | head -c 400   # after signing in as in step 4
curl -s -b /tmp/terminal.jar "localhost:8000/reporting/logs?limit=5"
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
| `RuntimeError: CUQ_PROXY_URL is not set` | `backend/.env` is missing, or uvicorn was launched from outside `backend/`. A bare `load_dotenv()` searches up from the current directory; `scripts/dev-local.sh` handles this. |
| sign-in "did not accept these credentials" | wrong value in a field (see the mapping table above), or the gateway's DB was reset. Re-run `scripts/dev-gateway.sh creds`. |
| every route `401 NOT_SIGNED_IN` | no session cookie: sign in first. Opening the backend on :8000 directly in a browser won't carry the dashboard's cookie. |
| backend 5xx on `/account/*` or `/orders/*`, gateway logs nothing | gateway not running — `cd ../trading-gateway && scripts/dev-gateway.sh up` |
| `EXCHANGE_ERROR`, OKX code `50119` / `60032` "API key doesn't exist" | the demo key is on the wrong OKX platform (US vs international) — see `trading-gateway/SANDBOX_INTEGRATION.md` |
| order rejected for size / price tick | adjust size or price; not a wiring problem |
| dashboard loads but OKX order status shows "disconnected" | backend order-event relay or the gateway's WS upstream is down — check both shells |
| `--strictPort` error on start | `5173` (or your `FRONTEND_PORT`) is in use — free it or set a different `FRONTEND_PORT` |

## What is NOT covered

- `docker compose up` — that path still works for a containerised run, but a
  backend container can't reach a gateway on the host's `127.0.0.1:8080`
  without `host.docker.internal` rewiring. Use `scripts/dev-local.sh` for local
  gateway testing.
- Real (non-simulated) trading — that's a property of the gateway you point at,
  never a terminal setting.
