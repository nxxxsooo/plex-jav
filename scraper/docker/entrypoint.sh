#!/bin/bash
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}
UMASK=${UMASK:-000}
APP_DIR=${APP_DIR:-/app}
CONFIG_DIR=${CONFIG_DIR:-/config}
MEDIA_DIR=${MEDIA_DIR:-/media}
JAVSP_USER=${JAVSP_USER:-javsp}
JAVSP_BIN=${JAVSP_BIN:-$APP_DIR/.venv/bin/javsp}
METATUBE_BIN=${METATUBE_BIN:-/usr/local/bin/metatube-server}
PROCESS_STOP_TIMEOUT=${PROCESS_STOP_TIMEOUT:-5}

MT_PID=""
JAVSP_PID=""

stop_process() {
    local pid=$1
    local name=$2

    if [ -z "$pid" ]; then
        return
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
        wait "$pid" 2>/dev/null || true
        return
    fi

    echo "[entrypoint] Stopping $name..."
    kill -TERM "$pid" 2>/dev/null || true

    # Reap the child immediately when it exits while a bounded watchdog
    # enforces shutdown for a process that ignores SIGTERM. Polling with
    # kill -0 alone mistakes an unreaped zombie for a live process.
    (
        sleep "$PROCESS_STOP_TIMEOUT"
        if kill -0 "$pid" 2>/dev/null; then
            echo "[entrypoint] $name did not stop in time; killing it."
            kill -KILL "$pid" 2>/dev/null || true
        fi
    ) &
    local watchdog_pid=$!
    wait "$pid" 2>/dev/null || true
    kill "$watchdog_pid" 2>/dev/null || true
    wait "$watchdog_pid" 2>/dev/null || true
}

cleanup() {
    local status=$?
    trap - EXIT INT TERM
    stop_process "$JAVSP_PID" "JavSP"
    stop_process "$MT_PID" "MetaTube"
    exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

umask "$UMASK"

# Create group if GID doesn't exist
if ! getent group "$PGID" > /dev/null 2>&1; then
    groupadd -g "$PGID" "$JAVSP_USER"
fi

# Resolve group name for the GID
GROUP_NAME=$(getent group "$PGID" | cut -d: -f1)

# Create user if it doesn't exist
if ! getent passwd "$JAVSP_USER" > /dev/null 2>&1; then
    useradd -u "$PUID" -g "$GROUP_NAME" -d "$APP_DIR" -s /bin/bash -M "$JAVSP_USER" 2>/dev/null || true
fi

# Fix ownership of working directories
chown -R "$PUID:$PGID" "$APP_DIR"

# If the media directory exists, ensure its mount point is accessible
if [ -d "$MEDIA_DIR" ]; then
    chown "$PUID:$PGID" "$MEDIA_DIR" 2>/dev/null || true
fi

# If the config directory exists, ensure it's accessible
if [ -d "$CONFIG_DIR" ]; then
    chown -R "$PUID:$PGID" "$CONFIG_DIR" 2>/dev/null || true
fi

# Copy default config to /config if user hasn't provided one
if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    echo "[entrypoint] No config.yml found in $CONFIG_DIR, copying default..."
    cp "$APP_DIR/config.yml" "$CONFIG_DIR/config.yml"
    chown "$PUID:$PGID" "$CONFIG_DIR/config.yml"
fi

# Start embedded MetaTube server if enabled
METATUBE_ENABLED=${METATUBE_ENABLED:-1}
if [ "$METATUBE_ENABLED" = "1" ]; then
    METATUBE_PORT=${METATUBE_PORT:-8080}
    METATUBE_DSN=${METATUBE_DSN:-metatube.db}
    METATUBE_TOKEN=${METATUBE_TOKEN:-}

    # MetaTube data directory (inside /config for persistence)
    METATUBE_DATA_DIR="$CONFIG_DIR/metatube"
    mkdir -p "$METATUBE_DATA_DIR"
    chown -R "$PUID:$PGID" "$METATUBE_DATA_DIR"

    echo "[entrypoint] Starting MetaTube server on port $METATUBE_PORT..."

    # Build MetaTube args
    MT_ARGS=(-port "$METATUBE_PORT" -dsn "$METATUBE_DATA_DIR/$METATUBE_DSN" -db-auto-migrate)
    if [ -n "$METATUBE_TOKEN" ]; then
        MT_ARGS+=(-token "$METATUBE_TOKEN")
    fi

    # Start MetaTube in background as the same user
    gosu "$PUID:$PGID" "$METATUBE_BIN" "${MT_ARGS[@]}" &
    MT_PID=$!

    # Wait for MetaTube to be ready (up to 15 seconds)
    METATUBE_READY=0
    for _ in $(seq 1 30); do
        if curl -sf "http://localhost:$METATUBE_PORT/" > /dev/null 2>&1; then
            echo "[entrypoint] MetaTube server ready."
            METATUBE_READY=1
            break
        fi
        if ! kill -0 "$MT_PID" 2>/dev/null; then
            echo "[entrypoint] ERROR: MetaTube server exited before becoming ready." >&2
            break
        fi
        sleep 0.5
    done

    if [ "$METATUBE_READY" != "1" ]; then
        echo "[entrypoint] ERROR: MetaTube server failed its readiness check; JavSP will not run." >&2
        exit 1
    fi

    # Point JavSP at the embedded server unless explicitly overridden.
    export METATUBE_URL=${METATUBE_URL:-http://localhost:$METATUBE_PORT}
fi

# JavSP is deliberately a one-shot job. Start the container manually whenever
# completed media has been placed in the configured input directory.
echo "[entrypoint] Starting one-shot JavSP scan..."
gosu "$PUID:$PGID" "$JAVSP_BIN" "$@" &
JAVSP_PID=$!

set +e
wait "$JAVSP_PID"
JAVSP_STATUS=$?
set -e
JAVSP_PID=""

if [ "$JAVSP_STATUS" -ne 0 ]; then
    echo "[entrypoint] ERROR: JavSP failed with exit code $JAVSP_STATUS." >&2
    exit "$JAVSP_STATUS"
fi

if [ "$METATUBE_ENABLED" = "1" ] && ! kill -0 "$MT_PID" 2>/dev/null; then
    echo "[entrypoint] ERROR: MetaTube stopped while JavSP was running." >&2
    exit 1
fi

echo "[entrypoint] JavSP completed successfully."
