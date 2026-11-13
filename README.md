# CU Quants Trading Terminal

A web-based trading terminal for trading on OKX and Kraken (the club's Kraken
Prime account) from a single dashboard. All trading goes through the CU Quants
Trading Gateway, so the terminal itself holds no exchange keys.

---

## Getting started (traders)

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

### 2. Clone the repos side by side

The terminal depends on the club's `proxy-client` SDK, which must be checked out
**in the same parent folder** as this repo:

```bash
mkdir cuquants && cd cuquants
git clone https://github.com/CUQuants/CU-Quants-Trading-Terminal.git
git clone https://github.com/CUQuants/proxy-client.git
cd CU-Quants-Trading-Terminal
```

You should end up with:

```
cuquants/
├── CU-Quants-Trading-Terminal/   ← you run things from here
└── proxy-client/
```

### 3. Get your credentials

Ask the club liaison, or whoever runs the gateway, for an **operator
credential**. You'll get five values:

| Put this in `backend/.env` | What it is |
|---|---|
| `CUQ_PROXY_URL` | The gateway's URL |
| `CUQ_PROXY_API_KEY` | Your operator API key (`cuq_op_...`) |
| `CUQ_PROXY_SECRET` | The secret paired with that key |
| `CUQ_PROXY_OPERATOR_ID` | Your operator id, e.g. `cuq-014` |
| `CUQ_PROXY_OPERATOR_NAME` | Your name, shown in the audit log |

### 4. Run it

```bash
scripts/dev-local.sh
```

On the first run the script creates `backend/.env` from the template and stops.
Open `backend/.env`, paste in the five values from step 3, and run the script
again.

From then on it checks your setup, installs dependencies (this takes a minute
the first time), and starts everything. Open the dashboard at
**http://localhost:5173**.

Press **Ctrl-C** to stop. To update later: `git pull` in both repos, then run
the script again.

### If something goes wrong

The script checks your setup before it starts. If something is missing (uv,
Node, `proxy-client`, or a value in `.env`), it stops and prints the command
that fixes it. Other common issues:

| Symptom | Fix |
|---|---|
| `warning: gateway ... did not answer /healthz` | Check `CUQ_PROXY_URL`, your network/VPN, or ask whoever issued your credential whether the gateway is up. |
| `command not found` right after installing something | Open a new terminal window. |
| `--strictPort` / port in use | Something is already on 5173 or 8000. Close it, or run `FRONTEND_PORT=5174 BACKEND_PORT=8001 scripts/dev-local.sh`. |
| Reporting tab says "not configured" | Expected. It's optional; see [TRADER_GUIDE.md](./TRADER_GUIDE.md#audit-reporting-optional). |
| `401` / auth errors in the backend log | A credential value is wrong or has extra spaces. Re-copy it into `backend/.env`. |

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
├── proxy-client/
└── trading-gateway/
```

`scripts/dev-local.sh` options:

```bash
SKIP_INSTALL=1 scripts/dev-local.sh                 # skip uv sync / npm install
BACKEND_PORT=9000 FRONTEND_PORT=5000 scripts/dev-local.sh
```

Running the two halves by hand, without the script:

```bash
cd backend  && uv sync && uv run uvicorn app:app --reload --port 8000
cd frontend && npm install && npm run dev            # http://localhost:5173
```

> **Docker (`docker compose up`) is currently not supported.** The backend
> installs `proxy-client` from a sibling folder outside the Docker build
> context, so the image build fails. Use `scripts/dev-local.sh`. Docker will
> work again once `proxy-client` is pinned to a git revision in
> `backend/pyproject.toml`.

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
