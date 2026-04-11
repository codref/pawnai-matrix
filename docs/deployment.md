# Deployment Guide

This guide deploys pawnai-matrix on a Linux server using **Docker Compose** for the runtime, **systemd** for service management, and a **self-hosted GitHub Actions runner** for automated updates on every push to `main`.

## Architecture

```
push to main
  → deploy.yml fires on the self-hosted runner (on the server)
  → git pull + docker compose build bob
  → alembic upgrade head
  → docker compose up -d bob
```

The `db` container stays running across deploys — only the `bob` container is rebuilt and restarted.

---

## Server layout

| Path | Purpose |
|---|---|
| `/opt/pawnai-matrix/` | Git clone of the repository |
| `/opt/pawnai-matrix/config/config.yaml` | Runtime config — secrets, not in git |
| `/opt/pawnai-matrix/config/store/` | Matrix E2EE key store — persisted, not in git |
| `/opt/pawnai-matrix/config/tmp/` | Temp files (audio, images) |
| `/opt/actions-runner/` | GitHub Actions runner installation |
| `/etc/systemd/system/pawnai-matrix.service` | systemd unit (copied from `deploy/`) |

---

## Phase 1 — Server prerequisites

```bash
# Install Docker (official script)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify Compose v2 is available
docker compose version
```

---

## Phase 2 — Clone the repository

```bash
sudo mkdir -p /opt/pawnai-matrix
sudo chown $USER:$USER /opt/pawnai-matrix

# Public repo:
git clone https://github.com/YOUR_ORG/YOUR_REPO.git /opt/pawnai-matrix

# Private repo (SSH deploy key recommended):
git clone git@github.com:YOUR_ORG/YOUR_REPO.git /opt/pawnai-matrix
```

---

## Phase 3 — Create config.yaml

The config file is never committed. Create it from the sample:

```bash
cp /opt/pawnai-matrix/config/sample.config.yaml /opt/pawnai-matrix/config/config.yaml
nano /opt/pawnai-matrix/config/config.yaml
```

Minimum values to set:

```yaml
matrix:
  user_id: "@bob:your.homeserver.org"
  user_password: "your-matrix-password"
  homeserver_url: https://your.homeserver.org
  device_id: ABCDEFGHIJ          # any unique string
  device_name: matrix-bob
  command_prefix: "!bob"
  inviters:
    - "@you:your.homeserver.org"
  power_users:
    - "@you:your.homeserver.org"

storage:
  # Use the db service hostname, not localhost
  database: "postgresql://bob:bob@db/bob"
  store_path: ./store             # resolves to /config/store inside the container
  temp_path: ./tmp                # resolves to /config/tmp inside the container

openai:
  url: http://your-ollama-or-llm-host:4000
  api_key: ""
  default_llm_model: your-model-name
```

Create the runtime directories:

```bash
mkdir -p /opt/pawnai-matrix/config/store
mkdir -p /opt/pawnai-matrix/config/tmp
```

---

## Phase 4 — Install the systemd unit

```bash
sudo cp /opt/pawnai-matrix/deploy/pawnai-matrix.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pawnai-matrix
```

Do **not** start it yet — run the first deploy manually first (Phase 6).

---

## Phase 5 — Install the GitHub Actions self-hosted runner

Go to your GitHub repo → **Settings → Actions → Runners → New self-hosted runner**.
Select **Linux / x64** and follow the commands shown. They look like:

```bash
mkdir -p /opt/actions-runner && cd /opt/actions-runner
curl -o runner.tar.gz -L https://github.com/actions/runner/releases/download/vX.Y.Z/actions-runner-linux-x64-X.Y.Z.tar.gz
tar xzf runner.tar.gz

# Register (token is generated in the GitHub UI, valid for 1 hour)
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# Install and start as a systemd service
sudo ./svc.sh install
sudo ./svc.sh start
```

The runner user needs access to Docker and to the repo directory:

```bash
# If the runner runs as a dedicated user (e.g. "actions-runner"):
sudo usermod -aG docker actions-runner
sudo chown -R actions-runner:actions-runner /opt/pawnai-matrix
```

Verify the runner appears as **Idle** in GitHub → Settings → Actions → Runners.

---

## Phase 6 — First manual deploy

Run through the full deploy sequence once by hand to verify everything works before trusting the CI pipeline.

```bash
cd /opt/pawnai-matrix/docker

# Pull base image and build the bot
docker compose pull db
docker compose build bob

# Start the database
docker compose up -d db

# Wait for Postgres to be ready, then run migrations
sleep 5
docker compose run --rm bob alembic upgrade head

# Start the bot
docker compose up -d bob

# Tail logs to confirm it connects
docker compose logs bob -f
```

You should see the bot log in to the Matrix homeserver. Invite it to a room to confirm it responds.

Once the stack is healthy, hand it over to systemd:

```bash
docker compose down
sudo systemctl start pawnai-matrix
sudo systemctl status pawnai-matrix
```

---

## Phase 7 — Verify automated deploys

Push any commit to `main`:

```bash
git push origin main
```

Watch it in GitHub → **Actions → Deploy to server**. The runner will:

1. Pull the latest code
2. Rebuild the `bob` image
3. Run any pending migrations
4. Restart only the `bob` container (`db` keeps running)

On the server you can follow along with:

```bash
docker compose -f /opt/pawnai-matrix/docker/docker-compose.yaml logs bob -f
journalctl -u pawnai-matrix -f
```

---

## Useful commands

```bash
# Service control
sudo systemctl start pawnai-matrix
sudo systemctl stop pawnai-matrix
sudo systemctl restart pawnai-matrix
sudo systemctl status pawnai-matrix

# Container status
docker compose -f /opt/pawnai-matrix/docker/docker-compose.yaml ps

# Live bot logs
docker compose -f /opt/pawnai-matrix/docker/docker-compose.yaml logs bob -f

# Manual migration only (e.g. after a hotfix)
docker compose -f /opt/pawnai-matrix/docker/docker-compose.yaml run --rm bob alembic upgrade head

# Open a shell in the bot container
docker compose -f /opt/pawnai-matrix/docker/docker-compose.yaml run --rm bob bash
```

---

## Troubleshooting

**Bot exits immediately on start**
Check logs: `docker compose logs bob`. Most likely causes: config.yaml not mounted correctly, wrong database URL (use `db` not `localhost`), or missing Matrix credentials.

**`alembic upgrade head` fails with connection error**
The `db` container may not be ready. Wait a few seconds and retry, or add a `healthcheck` to the db service in `docker-compose.yaml`.

**Runner does not pick up jobs**
Check runner status: `sudo /opt/actions-runner/svc.sh status`. The runner must be **Idle** in GitHub Settings → Runners. Ensure the `runs-on: self-hosted` label in `deploy.yml` matches the runner's configured labels.

**E2EE messages not decrypted**
The `/config/store` volume must be persisted across restarts. Do not delete it. If the store is lost the bot must be re-verified in each encrypted room.
