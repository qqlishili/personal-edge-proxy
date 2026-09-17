#!/usr/bin/env python3
"""幂等渲染 Xray config: SS-2022 (链式主力) + REALITY (双模通用) + HY2 (直连特化) + WARP AI 出口"""
import json, os, sys, warnings, base64, urllib.parse as up

CFG = '/usr/local/etc/xray/config.json'
EDGE = '/etc/edge'

with open(CFG) as f:
    d = json.load(f)

# 1. 加载凭据
UUID  = open(f'{EDGE}/reality_uuid').read().strip()
PRIV  = open(f'{EDGE}/reality_priv').read().strip()
SHORT = open(f'{EDGE}/reality_shortid').read().strip()
PUB   = open(f'{EDGE}/reality_pub').read().strip()
SS_KEY = open(f'{EDGE}/ss2022_key').read().strip()

for name, val, want in [('UUID', UUID, 36), ('PRIV', PRIV, 43), ('PUB', PUB, 43)]:
    if len(val) != want:
        warnings.warn(f'{name} len={len(val)} expected {want}', stacklevel=2)
if len(SHORT) > 16:
    raise ValueError(f'SHORT len={len(SHORT)} > 16 (REALITY 限制)')
if not SS_KEY:
    raise ValueError('SS_KEY is empty in /etc/edge/ss2022_key')

SERVER_IP = open(f'{EDGE}/server_ip').read().strip() if os.path.exists(f'{EDGE}/server_ip') else '107.174.244.167'

# 2. 清理旧 Inbounds（保持幂等）
d['inbounds'] = [i for i in d['inbounds'] if i.get('tag') not in ('reality-vision', 'ss2022-in')]

# 3. 注入 Shadowsocks-2022 Inbound (强制开启 sniffing 防止 AI 穿透)
ss2022_inbound = {
    "tag": "ss2022-in",
    "listen": "::",
    "port": int(os.environ.get("EDGE_SS_PORT", "10443")),
    "protocol": "shadowsocks",
    "settings": {
        "method": "2022-blake3-aes-128-gcm",
        "password": SS_KEY,
        "network": "tcp,udp"
    },
    "sniffing": {
        "enabled": True,
        "destOverride": ["http", "tls", "quic"],
        "metadataOnly": False,
        "routeOnly": True
    }
}
d['inbounds'].append(ss2022_inbound)

# 4. 注入 REALITY Inbound
reality_inbound = {
    "tag": "reality-vision",
    "listen": "::",
    "port": int(os.environ.get("EDGE_PORT", "8443")),
    "protocol": "vless",
    "settings": {
        "clients": [{"id": UUID, "flow": "xtls-rprx-vision"}],
        "decryption": "none"
    },
    "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "target": "www.oracle.com:443",
            "serverNames": ["www.oracle.com"],
            "privateKey": PRIV,
            "shortIds": [SHORT, ""]
        }
    },
    "sniffing": {
        "enabled": True,
        "destOverride": ["http", "tls", "quic"],
        "metadataOnly": False,
        "routeOnly": True
    }
}
d['inbounds'].append(reality_inbound)

# 5. 路由归一化：消除 inboundTag 限制，确保所有入口对 AI 流量无条件走 WARP，QUIC 强制拦截
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

for r in d.get('routing', {}).get('rules', []):
    # 私网阻断与 AI 规则一律解绑 inboundTag，实现全局自动覆盖
    if 'inboundTag' in r:
        del r['inboundTag']
    if r.get('outboundTag') == 'warp-official':
        curr = set(r.get('domain', []))
        for dom in ai_domains:
            if dom not in curr:
                r.setdefault('domain', []).append(dom)
    elif r.get('outboundTag') == 'block' and r.get('network') == 'udp':
        curr = set(r.get('domain', []))
        for dom in ai_domains:
            if dom not in curr:
                r.setdefault('domain', []).append(dom)

with open(CFG, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.chmod(CFG, 0o644)
print('OK render Xray config completed')
print('  inbounds :', [i['tag'] for i in d['inbounds']])

# 6. 生成规范 URI 文件
# 6.1 SS-2022
ss_userinfo = base64.b64encode(f"2022-blake3-aes-128-gcm:{SS_KEY}".encode()).decode()
ss_tag = up.quote("🇺🇸 美国-洛杉矶-SS-2022 [链式专属]")
ss_uri = f"ss://{ss_userinfo}@{SERVER_IP}:10443#{ss_tag}"
with open(f'{EDGE}/ss2022_uri', 'w') as f:
    f.write(ss_uri + '\n')
os.chmod(f'{EDGE}/ss2022_uri', 0o644)
print('  ss2022_uri written:', ss_uri)

# 6.2 REALITY
reality_tag = up.quote("🇺🇸 美国-洛杉矶-REALITY [双模通用]")
reality_uri = (
    f"vless://{UUID}@{SERVER_IP}:8443"
    f"?encryption=none&flow=xtls-rprx-vision&security=reality"
    f"&sni=www.oracle.com&fp=chrome&pbk={PUB}&sid={SHORT}&type=tcp"
    f"#{reality_tag}"
)
with open(f'{EDGE}/reality_uri', 'w') as f:
    f.write(reality_uri + '\n')
os.chmod(f'{EDGE}/reality_uri', 0o644)
print('  reality_uri written:', reality_uri)

# 6.3 HY2 标签语义更新
if os.path.exists(f'{EDGE}/hy2_uri'):
    raw_hy2 = open(f'{EDGE}/hy2_uri').read().strip()
    base_hy2 = raw_hy2.split('#')[0]
    hy2_tag = up.quote("🇺🇸 美国-洛杉矶-HY2 [直连专属·禁中转]")
    updated_hy2 = f"{base_hy2}#{hy2_tag}"
    with open(f'{EDGE}/hy2_uri', 'w') as f:
        f.write(updated_hy2 + '\n')
    os.chmod(f'{EDGE}/hy2_uri', 0o644)
    print('  hy2_uri updated:', updated_hy2)
