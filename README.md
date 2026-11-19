# CU Quants Trading Terminal

A web-based trading terminal for trading on OKX and Kraken (the club's Kraken
Prime account) from a single dashboard. All trading goes through the CU Quants
Trading Gateway, so the terminal itself holds no exchange keys.

---

## Signing in

Whether you use the hosted terminal or run it yourself, you sign in the same
way. The first page asks for your **CU Quants gateway credential**: the four
`proxy:` values already in your xlrts `config.yaml`.

| On the sign-in page | In `speedbyte/xlrts/config.yaml` |
|---|---|
| API key | `proxy.api_key` (`cuq_op_...`) |
| API secret | `proxy.api_secret` |
| Operator ID | `proxy.operator_id` (e.g. `cuq-016`) |
| Operator name | `proxy.operator_name` |

- **What the terminal checks.** It verifies the API key, the secret, and that
  the operator ID owns that key, using one signed call to the gateway (the same
  check xlrts makes at startup). The operator name isn't checked; it is
  recorded as you type it.
- **Where your secret goes.** The terminal server keeps it in memory only, for
  as long as you're signed in. It is never written to disk and never stored in
  your browser. The browser remembers the other three fields so you don't
  retype them.
- **Attribution.** Every order and request the terminal sends is signed with,
  and attributed in the gateway's audit log to, *your* credential.
- **When you get signed out.** After 12 hours idle or 24 hours at most, when
  you click **Sign out**, or whenever the terminal server restarts.

**Hosted:** https://terminal.178-105-55-5.sslip.io (see
[deploy/README.md](./deploy/README.md)).

---

## Getting started (running it yourself)

About 10 minutes, once you have your credentials. These steps assume macOS or
Linux. On Windows, run everything inside [WSL](https://learn.microsoft.com/windows/wsl/install).

### 1. Install the tools

You need **git**, **Node.js 22**, and **uv** (a Python tool manager; it
installs the right Python version for you).

**macOS** (with [Homebrew](https://brew.sh)):

```bash
brew install git node@22 uv
```

**Linux / WSL:**

```bash
# Node 22 via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# open a new terminal, then:
nvm install 22

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a **new terminal** after installing, then check:

```bash
node -v   # v22.12 or newer (v20.19+ also works)
uv --version
```

> Already have Node through nvm? Run `nvm install && nvm use` inside
> `frontend/` and it picks up the pinned version from `frontend/.nvmrc`.

### 2. Clone the repo

```bash
git clone https://github.com/CUQuants/CU-Quants-Trading-Terminal.git
cd CU-Quants-Trading-Terminal
```

The club's `proxy-client` SDK is installed automatically from GitHub when the
backend's dependencies are installed. It's pinned to a commit in
`backend/pyproject.toml`, so you don't need to clone it.

### 3. Get your credentials

You need an **operator credential** for the gateway. If you use xlrts, you
already have one: the `proxy:` section of your `config.yaml`. If you don't,
ask the club liaison or whoever runs the gateway.

`backend/.env` holds only **where the gateway is** (`CUQ_PROXY_URL`, which is
the `proxy.url` in your xlrts config). Your four credential values go into the
sign-in page, not into any file.

### 4. Run it

```bash
scripts/dev-local.sh
```

On the first run the script creates `backend/.env` from the template and stops.
Open `backend/.env`, set `CUQ_PROXY_URL`, and run the script again.

From then on it checks your setup, installs dependencies (this takes a minute
the first time), and starts everything. Open the dashboard at
**http://localhost:5173** and sign in (see [Signing in](#signing-in)).

Press **Ctrl-C** to stop. To update later, run `git pull` and then the script
again.

### If something goes wrong

The script checks your setup before it starts. If something is missing (uv,
Node, git, or a value in `.env`), it stops and prints the command
that fixes it. Other common issues:

| Symptom | Fix |
|---|---|
| `warning: gateway ... did not answer /healthz` | Check `CUQ_PROXY_URL`, your network/VPN, or ask whoever issued your credential whether the gateway is up. |
| `command not found` right after installing something | Open a new terminal window. |
| `--strictPort` / port in use | Something is already on 5173 or 8000. Close it, or run `FRONTEND_PORT=5174 BACKEND_PORT=8001 scripts/dev-local.sh`. |
| Reporting tab says "not configured" | Expected. It's optional; see [TRADER_GUIDE.md](./TRADER_GUIDE.md#audit-reporting-optional). |
| Sign-in says "did not accept these credentials" | The API key, secret or operator ID is wrong. Re-copy them from your xlrts `config.yaml`. The gateway gives the same answer for all three, and also for a computer clock that is more than 5 s off. |
| Sign-in says "Too many failed sign-ins" | Wait out the countdown. The terminal limits failed attempts so one mistyped secret can't lock everyone out at the gateway. |
| Sent back to the sign-in page | Your session ended (idle, expired, signed out, or the server restarted). Sign in again. |

More detail (all environment variables, Kraken limitations, simulated vs. live
trading) is in [TRADER_GUIDE.md](./TRADER_GUIDE.md).

---

## Developers: running against a local gateway

To test end to end without a shared gateway (local gateway in OKX-simulated
mode, no real funds), also clone `trading-gateway` next to this repo and follow
[DEV_TESTING.md](./DEV_TESTING.md). That setup additionally needs Docker
running, for the gateway's Postgres.

```
cuquants/
├── CU-Quants-Trading-Terminal/
└── trading-gateway/
```

`scripts/dev-local.sh` options:

```bash
SKIP_INSTALL=1 scripts/dev-local.sh                 # skip uv sync / npm install
BACKEND_PORT=9000 FRONTEND_PORT=5000 scripts/dev-local.sh
```

Running the two halves by hand, without the script:

```bash
cd backend  && uv sync && TERMINAL_COOKIE_SECURE=false uv run uvicorn app:app --reload --port 8000
cd frontend && npm install && npm run dev            # http://localhost:5173, proxies /api -> :8000
```

The browser always reaches the backend same-origin under `/api`: through Vite's
proxy in dev, and through Caddy in production. That is what lets the HttpOnly
session cookie work. Open the dashboard on the Vite port, not on :8000.

Docker also works: `docker compose up --build` (dashboard on :3000).

Deploying to the gateway's box: [deploy/README.md](./deploy/README.md).

### Working on proxy-client itself

The SDK is pinned in `backend/pyproject.toml` under `[tool.uv.sources]`. To pick
up a new release, change `rev` to the new commit and run `cd backend && uv lock`.
To develop against a local checkout, temporarily swap that line for
`cuq-proxy-client = { path = "../../proxy-client", editable = true }`, then
switch it back before committing.

## Repo layout

```
.
├── backend/          FastAPI service: gateway client, orders, trades, account data
├── frontend/         React + Vite dashboard
├── scripts/          dev-local.sh (one-command local run)
├── TRADER_GUIDE.md   Environment variables, exchanges, troubleshooting
├── DEV_TESTING.md    End-to-end testing against a local gateway
└── docs/             Design notes and specs
```

## What it does

- Streams live order books and trades from OKX, Kraken, and Gemini
- Places and cancels orders on OKX and Kraken Prime, and tracks OKX order status live over a websocket relay
- Shows account balances and positions per exchange
- Routes all trading through the CU Quants Gateway; simulated vs. live is a property of the gateway it points at, never a terminal setting
- Optional **Reporting** tab: browse and filter the gateway's audit log
