# Deploying the terminal

The terminal runs on the same box as the CU Quants Trading Gateway, under its
own Unix account (`cuqterm`). It is deployed from GitHub Actions with a button.

```
                         GitHub Actions
   PR / push to main ──▶ CI: backend tests · frontend build · deploy config
   "Deploy" button ────▶ CI again ─▶ build bundle ─▶ ssh cuqterm@box deploy < bundle
   "Rollback" button ──▶ ssh cuqterm@box rollback

   box ─ Caddy (:443) terminal.178-105-55-5.sslip.io
          ├─ /api/* ──▶ 127.0.0.1:8100  cuq-terminal (uvicorn, 1 worker, user cuqterm)
          │                               └─ signs as the signed-in trader ─▶ 127.0.0.1:8080 gateway
          └─ else   ──▶ /srv/cuq-terminal/frontend ─▶ current/frontend
```

## What runs where

| | |
|---|---|
| **CI** (`.github/workflows/ci.yml`) | On every PR and every push to `main`. Runs the backend tests, the frontend typecheck and build, shellcheck on the scripts, and a Caddy syntax check. Lint runs but doesn't block yet, because of existing errors. |
| **Deploy** (`.github/workflows/deploy.yml`) | Manual only: **Actions → Deploy → Run workflow** on `main`. It reruns CI, builds the bundle, ships it, checks the public site serves *this* build, and **signs every trader out**. |
| **Rollback** (`.github/workflows/rollback.yml`) | Manual only. Switches back to the previous release. Running it a second time undoes the rollback. |
| Receiver | `/usr/local/bin/cuq-terminal-receive-deploy` (root-owned), a copy of [`receive-deploy.sh`](receive-deploy.sh). The deploy key can run this and nothing else. |
| Releases | `/srv/cuq-terminal/releases/<utc>-<sha7>/`, with the newest 5 kept. `current` and `previous` are symlinks. |
| Settings | `/srv/cuq-terminal/.env`, mode 600 ([template](terminal.env.example)) |
| Service | the `cuqterm` user's systemd unit [`cuq-terminal.service`](cuq-terminal.service). It is installed and updated automatically by each deploy. |
| Edge | the [`Caddyfile.terminal`](Caddyfile.terminal) block in `/etc/caddy/Caddyfile` (unchanged by this pipeline) |

### What a deploy does on the box

All of this is in `receive-deploy.sh`.

1. Unpacks the bundle into a new release folder.
2. Runs `uv sync --frozen`.
3. Checks the app can at least be imported. If it can't, it stops here and nothing is switched.
4. Switches `current` to the new release, reinstalls the unit file, and restarts the service.
5. Polls the health check for up to 20 s.
6. If the new release isn't healthy, it **switches back to the previous release automatically** and the workflow fails.

Order-event logs go in `/srv/cuq-terminal/logs`, which all releases share. Only one deploy or rollback can run at a time.

### What a leaked deploy key could do

GitHub holds an SSH key for `cuqterm`. In `authorized_keys` it is marked
`restrict` (no shell, no PTY, no forwarding) and forced to run the receiver.

**The real boundary is the account, not the key restriction.** A deploy runs
the code it ships, so whoever holds the key can run code as `cuqterm`. That
account owns only `/srv/cuq-terminal`. It **cannot read `/srv/cuq-proxy`**,
which holds the gateway's `.env` and exchange-key vault. It *can* see what the
terminal sees: the credentials of traders signed in at that moment.

Three things keep the key out of reach:
- It lives in a GitHub environment that only `main` may use.
- Workflows on PR branches and forks can't read it.
- Deploying needs write access to the repo.

## One-time setup

This works the same on a fresh box and on one where the terminal currently
runs as `admin`. Steps 1–3 cause no outage. The terminal is down from step 4
until the first deploy in step 5 finishes, a few minutes, so pick a quiet
time. Run box commands as `admin` (`ssh cuq-proxy`) unless noted.

**Before you start, merge the PR that adds these workflows into `main`.**
GitHub only shows the Deploy button for workflows that exist on the default
branch.

### 1. Create the `cuqterm` account (box)

```bash
sudo useradd --create-home --shell /bin/bash cuqterm
sudo loginctl enable-linger cuqterm          # its service runs without a login, survives reboots
sudo -iu cuqterm bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'   # uv in ~cuqterm/.local/bin
sudo -iu cuqterm bash -c '~/.local/bin/uv --version && git --version'
```

Install the receiver. Copy it up from your Mac first:
`scp deploy/receive-deploy.sh cuq-proxy:/tmp/`

```bash
sudo install -o root -g root -m 755 /tmp/receive-deploy.sh /usr/local/bin/cuq-terminal-receive-deploy
rm /tmp/receive-deploy.sh
```

### 2. Make the deploy key

On your Mac:

```bash
ssh-keygen -t ed25519 -N '' -C github-actions-cuq-terminal -f ~/.ssh/cuq_terminal_gha
scp ~/.ssh/cuq_terminal_gha.pub cuq-proxy:/tmp/
```

On the box, authorize the key for the receiver only:

```bash
sudo -u cuqterm install -d -m 700 /home/cuqterm/.ssh
echo "restrict,command=\"/usr/local/bin/cuq-terminal-receive-deploy\" $(cat /tmp/cuq_terminal_gha.pub)" \
  | sudo -u cuqterm tee -a /home/cuqterm/.ssh/authorized_keys >/dev/null
sudo chmod 600 /home/cuqterm/.ssh/authorized_keys
rm /tmp/cuq_terminal_gha.pub
```

Back on your Mac, check that the key works and that it can't do anything else:

```bash
ssh -i ~/.ssh/cuq_terminal_gha -o IdentitiesOnly=yes -o ClearAllForwardings=yes cuqterm@178.105.55.5 status
# expect: [receive-deploy] current : (none)
ssh -i ~/.ssh/cuq_terminal_gha -o IdentitiesOnly=yes -o ClearAllForwardings=yes cuqterm@178.105.55.5 bash
# expect: [receive-deploy] error: refused: only 'deploy', 'rollback' or 'status'
```

### 3. Configure GitHub

Go to **Settings → Environments → New environment** and name it `production`.

- **Deployment branches and tags:** choose *Selected branches and tags* and add `main`.
- **Environment secrets:**
  - `DEPLOY_SSH_KEY`: the whole private key, from `cat ~/.ssh/cuq_terminal_gha`.
  - `DEPLOY_KNOWN_HOSTS`: the box's host key, which your Mac already trusts, from
    `ssh-keygen -F 178.105.55.5 | grep -v '^#'`. This pins the server's identity,
    so a runner never trusts a host key on first use.
- **Environment variables:**
  - `DEPLOY_HOST` = `178.105.55.5`
  - `TERMINAL_URL` = `https://terminal.178-105-55-5.sslip.io`

Once the secrets are saved, delete the private key from your Mac
(`rm ~/.ssh/cuq_terminal_gha`). To rotate it, repeat steps 2–3 with a new key
and remove the old line from `authorized_keys`.

**Recommended:** under **Settings → Branches**, add a rule for `main` that
requires the checks *Backend tests*, *Frontend build* and *Deploy config*.
That keeps `main` deployable.

### 4. Move the files to `cuqterm` (box) — the outage starts here

If the terminal currently runs as `admin`, stop it and remove its unit:

```bash
systemctl --user disable --now cuq-terminal
rm -f ~/.config/systemd/user/cuq-terminal.service && systemctl --user daemon-reload
sudo rm -rf /srv/cuq-terminal/app /srv/cuq-terminal/frontend
```

Then, on any box:

```bash
sudo install -d -o cuqterm -g cuqterm -m 755 /srv/cuq-terminal /srv/cuq-terminal/releases /srv/cuq-terminal/logs
# Fresh box only — create the settings file (on your Mac:
#   scp deploy/terminal.env.example cuq-proxy:/tmp/terminal.env), then:
#   sudo install -o cuqterm -g cuqterm -m 600 /tmp/terminal.env /srv/cuq-terminal/.env
sudo chown cuqterm:cuqterm /srv/cuq-terminal/.env && sudo chmod 600 /srv/cuq-terminal/.env
sudo ls -la /srv/cuq-terminal        # .env 600 cuqterm; releases/ logs/ owned by cuqterm
```

Caddy's site root is still `/srv/cuq-terminal/frontend`, which becomes a
symlink on the first deploy. The Caddy config doesn't change.

### 5. First deploy — the outage ends here

In GitHub, go to **Actions → Deploy → Run workflow**, choose `main`, and run it.
When it goes green, the site is back. Sign in to check it.

## Every day

| To… | Do |
|---|---|
| deploy `main` | **Actions → Deploy → Run workflow** (signs everyone out) |
| undo the last deploy | **Actions → Rollback → Run workflow** |
| see what's running | `ssh cuqterm@178.105.55.5 status` with a deploy key (or the last Deploy run's log) |
| read the service log | on the box: `sudo journalctl _UID=$(id -u cuqterm) _SYSTEMD_USER_UNIT=cuq-terminal.service -f` |
| restart without deploying | on the box: `sudo systemctl --user -M cuqterm@ restart cuq-terminal` |
| read the edge log | `tail -f /var/log/caddy/terminal.log` (cookies are filtered out) |

## Break-glass: deploying from a laptop

If GitHub is down, [`deploy.sh`](deploy.sh) builds the same bundle and ships it
to the same receiver.

1. Make a personal key: step 2 again, with a different file name.
2. Add this to `~/.ssh/config`:

   ```
   Host cuq-terminal
       HostName 178.105.55.5
       User cuqterm
       IdentityFile ~/.ssh/cuq_terminal_deploy
       IdentitiesOnly yes
       ClearAllForwardings yes
   ```

3. Run it:

   ```bash
   deploy/deploy.sh            # refuses unless you're on a clean main that matches origin/main
   deploy/deploy.sh status
   deploy/deploy.sh rollback
   DRY_RUN=1 deploy/deploy.sh  # build and list the bundle only
   FORCE=1 deploy/deploy.sh    # deploy something other than origin/main, on purpose
   ```

## Updating the receiver

Changes to `receive-deploy.sh` in the repo **don't reach the box by
themselves**. That's on purpose, so a deploy can't rewrite its own gate. After
merging a change, re-run the `install` line from step 1.

## Other notes

- **The WebSocket session limit.** Each signed-in trader's OKX order stream
  uses one of the gateway's `PROXY_WS_MAX_SESSIONS` slots. The default is 8 per
  exchange, shared with xlrts and speedbyte. If traders see order-event
  closes with code `1013`, raise it in `/srv/cuq-proxy/.env`.
- **The Caddy block.** If you ever re-add it from scratch, use the staging CA
  first. The steps are in the comments in
  [`Caddyfile.terminal`](Caddyfile.terminal).
