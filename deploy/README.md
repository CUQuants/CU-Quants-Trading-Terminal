# Deploying the terminal to 178.105.55.5

The terminal runs on the same box as the CU Quants Trading Gateway. It follows
the gateway's conventions from `trading-gateway/PROXY.md`, "On 178.105.55.5":
user `admin`, a systemd **user** unit, a loopback-only port, and Caddy in front
for TLS.

```
browser ──https──▶ Caddy (:443)
                   terminal.178-105-55-5.sslip.io
                   ├─ /api/*  ──▶ 127.0.0.1:8100  cuq-terminal (uvicorn, 1 worker)
                   │                              │  signs as the signed-in trader
                   │                              ▼
                   │                          127.0.0.1:8080  cuq-proxy (gateway)
                   └─ else    ──▶ /srv/cuq-terminal/frontend  (built SPA)

                   178-105-55-5.sslip.io  ──▶ gateway (unchanged)
```

| | |
|---|---|
| Public URL | `https://terminal.178-105-55-5.sslip.io` |
| Code | `/srv/cuq-terminal/app/{backend,deploy}` (rsync; no `.git`, no `.env`) |
| SPA | `/srv/cuq-terminal/frontend` (the `frontend/dist` build) |
| Environment | `/srv/cuq-terminal/.env`, mode 600 ([template](terminal.env.example)) |
| Unit | `~admin/.config/systemd/user/cuq-terminal.service` ([file](cuq-terminal.service)) |
| Bind | `127.0.0.1:8100` only. 8080 is the gateway, 8090 is reserved for reporting/RMU, and 2019 is Caddy's admin API. |
| Edge | the [`Caddyfile.terminal`](Caddyfile.terminal) block, appended to `/etc/caddy/Caddyfile` |

## How sign-in works on the server

- Traders sign in with the four `proxy:` values from their xlrts
  `config.yaml`. The backend checks those values against the gateway with one
  signed `get_server_time` call, the same check xlrts makes.
- After sign-in, the backend keeps the trader's secret **in memory only**, for
  that trader's session. The browser holds only an opaque HttpOnly,
  SameSite=Strict, Secure cookie.
- **Restarting `cuq-terminal` signs everyone out.** This is deliberate.
- **Run exactly one worker.** The session store lives in-process.
- **Every gateway request is attributed to the trader who made it**, in the
  gateway's `request_log`.
- **Failed sign-ins are throttled by the terminal**, both per IP and globally.
  All sign-ins reach the gateway from this box, so without the terminal's own
  throttle, one trader mistyping their secret could drain the gateway's
  per-IP auth-failure bucket and lock every trader out.
- **Each signed-in trader's open OKX order stream uses one of the gateway's
  `PROXY_WS_MAX_SESSIONS` slots.** The default is 8 per exchange, shared with
  xlrts and speedbyte. If people start seeing order-event `1013` closes, raise
  it in `/srv/cuq-proxy/.env` and run `make restart`.

## First-time setup (once, by hand)

1. **Install uv for `admin`.** The box has no pip, so uv takes its place. uv
   also fetches Python 3.12, per `backend/.python-version`, and needs `git` for
   the proxy-client SDK.
   ```bash
   ssh cuq-proxy
   curl -LsSf https://astral.sh/uv/install.sh | sh     # installs to ~/.local/bin, no root
   git --version                                        # needed by uv for proxy-client
   ```
2. **Create the directories and the env file:**
   ```bash
   sudo mkdir -p /srv/cuq-terminal/app /srv/cuq-terminal/frontend   # /srv is root-owned
   sudo chown -R admin:admin /srv/cuq-terminal
   # from your Mac:  scp deploy/terminal.env.example cuq-proxy:/srv/cuq-terminal/.env
   chmod 600 /srv/cuq-terminal/.env
   ```
3. **Do the first code push.** From your Mac, run `deploy/deploy.sh`. It will
   stop at the restart step because the unit isn't installed yet. That's
   expected.
4. **Install the unit.** The commands are in the header of
   [`cuq-terminal.service`](cuq-terminal.service). Then confirm the backend is
   up:
   ```bash
   systemctl --user status cuq-terminal
   curl -s http://127.0.0.1:8100/     # {"status":"ok"}
   ```
5. **Add the Caddy block, on the staging CA first.** Production Let's Encrypt
   allows 5 certificates per hostname set per week, so get everything working
   on staging before switching.
   ```bash
   sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak.$(date +%F)
   sudo sh -c 'cat /srv/cuq-terminal/app/deploy/Caddyfile.terminal >> /etc/caddy/Caddyfile'
   sudo -u caddy caddy validate --config /etc/caddy/Caddyfile   # as caddy, never root
   sudo systemctl reload caddy
   curl -k https://terminal.178-105-55-5.sslip.io/api/          # {"status":"ok"}
   ```
   Once the site works, move it to the production CA:
   1. Comment out the `tls { ca …staging… }` lines.
   2. Delete the staging certificate for `terminal.178-105-55-5.sslip.io` under
      `/var/lib/caddy/.local/share/caddy/certificates/`.
   3. Restart Caddy with `sudo systemctl restart caddy`. A reload isn't enough,
      because it keeps the staging certificate.
6. **Check that the gateway is untouched:**
   ```bash
   curl -s https://178-105-55-5.sslip.io/healthz    # {"status":"ok"}
   cd /srv/cuq-proxy && make status
   ```

## Redeploying

```bash
DRY_RUN=1 deploy/deploy.sh    # see what would change
deploy/deploy.sh              # build, rsync, uv sync, restart, health check
```

This signs every trader out, so deploy outside trading hours or warn people
first. To see what the box is running, use `cat /srv/cuq-terminal/app/DEPLOYED`.

## Day to day

```bash
systemctl --user status  cuq-terminal
systemctl --user restart cuq-terminal     # signs everyone out
journalctl --user -u cuq-terminal -f      # sign-ins/outs are logged by operator_id
tail -f /var/log/caddy/terminal.log       # cookies are filtered out
```

## Checklist after a deploy

- [ ] `https://178-105-55-5.sslip.io/healthz` still answers (gateway unaffected).
- [ ] `https://terminal.178-105-55-5.sslip.io` shows the sign-in page.
- [ ] A wrong secret shows "did not accept these credentials", with a `request_id`.
- [ ] Real values reach the dashboard, with your name in the header.
- [ ] The gateway's `request_log` shows your `operator_id` on the terminal's requests.
- [ ] `systemctl --user restart cuq-terminal` sends the browser back to sign-in.
