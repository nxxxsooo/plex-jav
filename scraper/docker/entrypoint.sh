#!/bin/bash
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}

# Create group if it doesn't exist
if ! getent group javsp > /dev/null 2>&1; then
    groupadd -g "$PGID" javsp
fi

# Create user if it doesn't exist
if ! getent passwd javsp > /dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" -d /app -s /bin/bash javsp
fi

# Fix ownership of working directories
chown -R "$PUID:$PGID" /app

# If /media exists, ensure it's accessible
if [ -d /media ]; then
    chown "$PUID:$PGID" /media 2>/dev/null || true
fi

# If /config exists, ensure it's accessible
if [ -d /config ]; then
    chown -R "$PUID:$PGID" /config 2>/dev/null || true
fi

# Copy default config to /config if user hasn't provided one
if [ ! -f /config/config.yml ]; then
    echo "[entrypoint] No config.yml found in /config, copying default..."
    cp /app/config.yml /config/config.yml
    chown "$PUID:$PGID" /config/config.yml
fi

# Start embedded MetaTube server if enabled
METATUBE_ENABLED=${METATUBE_ENABLED:-1}
if [ "$METATUBE_ENABLED" = "1" ]; then
    METATUBE_PORT=${METATUBE_PORT:-8080}
    METATUBE_DSN=${METATUBE_DSN:-metatube.db}
    METATUBE_TOKEN=${METATUBE_TOKEN:-}

    # MetaTube data directory (inside /config for persistence)
    METATUBE_DATA_DIR="/config/metatube"
    mkdir -p "$METATUBE_DATA_DIR"
    chown -R "$PUID:$PGID" "$METATUBE_DATA_DIR"

    echo "[entrypoint] Starting MetaTube server on port $METATUBE_PORT..."

    # Build MetaTube args
    MT_ARGS="-port $METATUBE_PORT -dsn $METATUBE_DATA_DIR/$METATUBE_DSN -db-auto-migrate"
    if [ -n "$METATUBE_TOKEN" ]; then
        MT_ARGS="$MT_ARGS -token $METATUBE_TOKEN"
    fi

    # Start MetaTube in background as the same user
    gosu "$PUID:$PGID" /usr/local/bin/metatube-server $MT_ARGS &
    MT_PID=$!

    # Wait for MetaTube to be ready (up to 15 seconds)
    for i in $(seq 1 30); do
        if curl -sf "http://localhost:$METATUBE_PORT/" > /dev/null 2>&1; then
            echo "[entrypoint] MetaTube server ready."
            break
        fi
        if ! kill -0 $MT_PID 2>/dev/null; then
            echo "[entrypoint] WARNING: MetaTube server failed to start. Continuing without it."
            break
        fi
        sleep 0.5
    done

    # Set metatube_url for JavSP if not already set
    export METATUBE_URL=${METATUBE_URL:-http://localhost:$METATUBE_PORT}
fi

# Run javsp as the specified user
exec gosu "$PUID:$PGID" /app/.venv/bin/javsp "$@"
