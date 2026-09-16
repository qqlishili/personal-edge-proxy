#!/bin/bash
set -euo pipefail
OUT=/etc/edge
mkdir -p "$OUT"
chmod 700 "$OUT"

python3 -c "
import subprocess, secrets
uuid = subprocess.check_output(['/usr/local/bin/xray', 'uuid']).decode().strip()
lines = subprocess.check_output(['/usr/local/bin/xray', 'x25519']).decode().splitlines()
priv, pub, h32 = '', '', ''
for line in lines:
    if 'PrivateKey:' in line: priv = line.split(':', 1)[1].strip()
    elif 'PublicKey' in line: pub = line.split(':', 1)[1].strip()
    elif 'Hash32:' in line: h32 = line.split(':', 1)[1].strip()
shortid = secrets.token_hex(8)

for name, val in [('reality_uuid', uuid), ('reality_priv', priv), ('reality_pub', pub), ('reality_hash32', h32), ('reality_shortid', shortid)]:
    with open(f'/etc/edge/{name}', 'w') as f:
        f.write(val + '\n')
"

chmod 600 "$OUT"/reality_*
echo "OK keys written"
ls -l "$OUT"/reality_* | awk '{print $1,$3,$4,$9}'
