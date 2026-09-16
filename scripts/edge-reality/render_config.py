#!/usr/bin/env python3
"""幂等渲染 Xray config: hy2 (A/C) + reality-vision (B) + WARP AI 出口 (C)"""
import json, os, sys, warnings
CFG = '/usr/local/etc/xray/config.json'
EDGE = '/etc/edge'

with open(CFG) as f:
    d = json.load(f)

UUID  = open(f'{EDGE}/reality_uuid').read().strip()
PRIV  = open(f'{EDGE}/reality_priv').read().strip()
SHORT = open(f'{EDGE}/reality_shortid').read().strip()
PUB   = open(f'{EDGE}/reality_pub').read().strip()

for name, val, want in [('UUID',UUID,36),('PRIV',PRIV,43),('PUB',PUB,43)]:
    if len(val) != want:
        warnings.warn(f'{name} len={len(val)} expected {want}', stacklevel=2)
if len(SHORT) > 16:
    raise ValueError(f'SHORT len={len(SHORT)} > 16 (REALITY 限制)')

# --- 清理(幂等去重) ---
d['inbounds']  = [i for i in d['inbounds']  if i.get('tag') != 'reality-vision']
d['outbounds'] = [o for o in d['outbounds'] if o.get('tag') != 'static-socks']

clean_rules = []
for r in d['routing']['rules']:
    if r.get('outboundTag') == 'static-socks':
        continue
    if 'inboundTag' in r:
        r['inboundTag'] = [t for t in r['inboundTag'] if t != 'reality-vision']
    clean_rules.append(r)
d['routing']['rules'] = clean_rules

# --- 注入 REALITY Inbound ---
reality_inbound = {
    "tag": "reality-vision",
    "listen": "::",
    "port": 4430,
    "protocol": "vless",
    "settings": {"clients": [{"id": UUID, "flow": "xtls-rprx-vision"}], "decryption": "none"},
    "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "target": "www.microsoft.com:443",
            "serverNames": ["www.microsoft.com"],
            "privateKey": PRIV,
            "shortIds": [SHORT]
        }
    },
    "sniffing": {"enabled": True, "destOverride": ["http","tls","quic"], "metadataOnly": False}
}
d['inbounds'].append(reality_inbound)

for r in d['routing']['rules']:
    if 'inboundTag' in r and 'reality-vision' not in r['inboundTag']:
        r['inboundTag'].append('reality-vision')

# --- 确保 AI 路由 (warp-official) 包含 Claude/Anthropic ---
ai_domains = [
    "domain:openai.com",
    "domain:chatgpt.com",
    "domain:oaistatic.com",
    "domain:oaiusercontent.com",
    "domain:gemini.google.com",
    "domain:aistudio.google.com",
    "domain:generativelanguage.googleapis.com",
    "domain:anthropic.com",
    "domain:claude.ai",
    "domain:claude.site",
    "domain:anthropicusercontent.com"
]
for r in d['routing']['rules']:
    if r.get('outboundTag') == 'warp-official':
        curr = set(r.get('domain', []))
        for dom in ai_domains:
            if dom not in curr:
                r['domain'].append(dom)

with open(CFG, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.chmod(CFG, 0o644)
print('OK render completed')
print('  inbounds :', [i['tag'] for i in d['inbounds']])
print('  outbounds:', [o['tag'] for o in d['outbounds']])

HOST_FILE = f"{EDGE}/reality_host"
HOST = open(HOST_FILE).read().strip() if os.path.exists(HOST_FILE) else os.environ.get("EDGE_HOST", "YOUR_DOMAIN_OR_IP")
NODE_NAME = os.environ.get("EDGE_NODE_NAME", "edge-reality-vision")
URI = (
    f"vless://{UUID}@{HOST}:4430"
    f"?encryption=none&flow=xtls-rprx-vision&security=reality"
    f"&sni=www.microsoft.com&fp=chrome&pbk={PUB}&sid={SHORT}&type=tcp"
    f"#{NODE_NAME}"
)
with open(f'{EDGE}/reality_uri', 'w') as f:
    f.write(URI + chr(10))
os.chmod(f'{EDGE}/reality_uri', 0o644)
print('  reality_uri written:', URI)
