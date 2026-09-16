#!/usr/bin/env bash
set -u

# 1. Exclusive flock to prevent concurrent execution races
exec 200>/run/warp-watchdog.lock
flock -n 200 || exit 0

PRIMARY_URL="https://api4.ipify.org"
SECONDARY_URL="https://www.cloudflare.com/cdn-cgi/trace"
MAX_TIME=6

check_probe() {
    local url="$1"
    curl --proxy socks5h://127.0.0.1:40000         --silent --fail --max-time "$MAX_TIME"         "$url" >/dev/null 2>&1
}

# Healthy if either primary or secondary succeeds
if check_probe "$PRIMARY_URL" || check_probe "$SECONDARY_URL"; then
    exit 0
fi

# Anti-jitter: sleep 2 seconds and re-check once before taking action
sleep 2
if check_probe "$PRIMARY_URL" || check_probe "$SECONDARY_URL"; then
    exit 0
fi

logger -t warp-watchdog "WARP dual probe check failed; attempting reconnect..."

warp-cli --accept-tos disconnect >/dev/null 2>&1 || true
sleep 2
warp-cli --accept-tos connect >/dev/null 2>&1 || true
sleep 3

if check_probe "$PRIMARY_URL" || check_probe "$SECONDARY_URL"; then
    logger -t warp-watchdog "WARP recovered via reconnect"
    exit 0
fi

logger -t warp-watchdog "WARP still failing; restarting warp-svc service..."
systemctl restart warp-svc >/dev/null 2>&1 || true
sleep 5

if check_probe "$PRIMARY_URL" || check_probe "$SECONDARY_URL"; then
    logger -t warp-watchdog "WARP recovered via service restart"
else
    logger -t warp-watchdog "WARP recovery FAILED"
fi
