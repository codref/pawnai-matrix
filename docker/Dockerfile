FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libolm-dev libpq5 libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

# Config is injected at runtime via volume mount.
# store_path and temp_path resolve relative to this file.
ENV BOB_CONFIG_FILE=/config/config.yaml

CMD ["bob"]
