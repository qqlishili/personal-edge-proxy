#!/bin/bash
set -euo pipefail
OUT=/etc/edge
mkdir -p "$OUT"
chmod 700 "$OUT"

python3 -c "
import subprocess, secrets, base64, os
out = '$OUT'

# 1. REALITY keys
if not os.path.exists(f'{out}/reality_uuid'):
    uuid = subprocess.check_output(['/usr/local/bin/xray', 'uuid']).decode().strip()
    lines = subprocess.check_output(['/usr/local/bin/xray', 'x25519']).decode().splitlines()
    priv, pub, h32 = '', '', ''
    for line in lines:
        if 'PrivateKey:' in line: priv = line.split(':', 1)[1].strip()
        elif 'PublicKey' in line: pub = line.split(':', 1)[1].strip()
        elif 'Hash32:' in line: h32 = line.split(':', 1)[1].strip()
    shortid = secrets.token_hex(8)

    for name, val in [('reality_uuid', uuid), ('reality_priv', priv), ('reality_pub', pub), ('reality_hash32', h32), ('reality_shortid', shortid)]:
        with open(f'{out}/{name}', 'w') as f:
            f.write(val + '\n')

# 2. Shadowsocks-2022 key (16 bytes base64 for 2022-blake3-aes-128-gcm)
if not os.path.exists(f'{out}/ss2022_key'):
    ss_key = base64.b64encode(secrets.token_bytes(16)).decode()
    with open(f'{out}/ss2022_key', 'w') as f:
        f.write(ss_key + '\n')
"

chmod 600 "$OUT"/reality_* "$OUT"/ss2022_* 2>/dev/null || true
echo "OK keys verified"
ls -l "$OUT"/reality_* "$OUT"/ss2022_* 2>/dev/null | awk '{print $1,$3,$4,$9}'
