FROM python:3.12-slim AS builder

WORKDIR /app

ENV PATH=/root/.local/bin:$PATH
RUN pip install pipx && \
    pipx ensurepath && \
    pipx install poetry
RUN apt update && apt install -y git

COPY . .

ENV POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.0
RUN poetry self add poetry-dynamic-versioning && \
    poetry config virtualenvs.in-project true && \
    rm -f poetry.lock && \
    poetry lock && \
    touch README.md && \
    poetry install && \
    rm -rf /app/.git


# Copy MetaTube server binary from official image
FROM ghcr.io/metatube-community/metatube-server:latest AS metatube


FROM python:3.12-slim AS runner

WORKDIR /app

# Install gosu for running as arbitrary uid/gid (Unraid compatibility)
# Install ca-certificates for MetaTube HTTPS requests
RUN apt-get update && \
    apt-get install -y --no-install-recommends gosu ca-certificates curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/ /app/
COPY --from=metatube /metatube-server /usr/local/bin/metatube-server
RUN chmod +x /usr/local/bin/metatube-server

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default uid/gid for Unraid (nobody:users = 99:100)
ENV PUID=99
ENV PGID=100

# MetaTube configuration (embedded server)
ENV METATUBE_ENABLED=1
ENV METATUBE_PORT=8080
ENV METATUBE_TOKEN=""
ENV METATUBE_DSN="metatube.db"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["-c", "/config/config.yml"]
