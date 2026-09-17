#!/usr/bin/env bash
set -euo pipefail

echo "=== Deploying personal-edge-proxy scripts ==="
mkdir -p /opt/edge-reality /opt/edge-sub /usr/local/sbin /etc/systemd/system

cp scripts/edge-reality/gen_keys.sh /opt/edge-reality/gen_keys.sh
chmod 755 /opt/edge-reality/gen_keys.sh

cp scripts/edge-reality/render_config.py /opt/edge-reality/render_config.py
chmod 755 /opt/edge-reality/render_config.py

cp scripts/edge-sub/edge_sub.py /opt/edge-sub/edge_sub.py
chmod 755 /opt/edge-sub/edge_sub.py

cp scripts/edge-sub/mihomo.py /opt/edge-sub/mihomo.py
chmod 755 /opt/edge-sub/mihomo.py

cp scripts/warp/warp-watchdog.sh /usr/local/sbin/warp-watchdog.sh
chmod 700 /usr/local/sbin/warp-watchdog.sh

cp systemd/edge-sub.service /etc/systemd/system/edge-sub.service
cp systemd/warp-watchdog.service /etc/systemd/system/warp-watchdog.service
cp systemd/warp-watchdog.timer /etc/systemd/system/warp-watchdog.timer

systemctl daemon-reload

echo "=== Ensuring keys and rendering Xray config ==="
/opt/edge-reality/gen_keys.sh
/opt/edge-reality/render_config.py

echo "=== Testing Xray configuration ==="
/usr/local/bin/xray -test -config /usr/local/etc/xray/config.json

echo "=== Restarting services ==="
systemctl restart xray
systemctl restart edge-sub

echo "=== Deployment completed successfully ==="
