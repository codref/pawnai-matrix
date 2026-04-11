# Matrix BOB

A [Matrix](https://matrix.org/) **bot** to experiment with autoregressive LLMs.  
Bob integrates with any OpenAI-compatible API (e.g. Ollama, LiteLLM) and can:

* carry on conversations in Matrix rooms
* transcribe audio messages and use them as input
* describe and process images
* scrape the web and summarize content

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

## Development

```bash
pip install --editable .
```

## Configuration

Copy the sample config and fill in your values:

```bash
cp config/sample.config.yaml config/config.yaml
```

Minimum fields to set: Matrix credentials (`user_id`, `user_password`, `homeserver_url`, `device_id`),
`inviters`, `power_users`, and the `openai.url` pointing at your LLM backend.

## Run

Bob requires a PostgreSQL database. The `docker/` directory contains a `docker-compose.yaml`
that starts the database and the bot together:

```bash
cd docker
docker compose up -d
```

Or run locally after starting PostgreSQL separately:

```bash
bob [config/config.yaml]
```

Config file defaults to `config/config.yaml`.

## Database migrations

```bash
alembic upgrade head
```

Run this once on first setup and after any update that includes new migrations.

## Deployment

See [docs/deployment.md](docs/deployment.md) for a full production deployment guide (Docker Compose + systemd + GitHub Actions CI).

## Open source and contributing

Contributions are welcome — please open an issue or discussion before starting significant work.
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Thanks to

* [matrix-nio](https://github.com/matrix-nio/matrix-nio)
* [nio-template](https://github.com/anoadragon453/nio-template)
