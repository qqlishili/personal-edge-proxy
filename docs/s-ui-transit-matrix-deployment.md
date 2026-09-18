# `s-ui` 三阶中转落地矩阵部署与复用指南 (Transit Matrix Deployment Guide)

> 本文档归档于 **`personal-edge-proxy`** 仓库 (`/root/code/personal-edge-proxy/docs/s-ui-transit-matrix-deployment.md`)。
> 专门解决：**客户端无法直连落地机，必须通过前置商业跳板（Chain Proxy / `dialer-proxy`）链式转发，同时要求 128MB ~ 2GB 内存小鸡稳定承载、零外部胶水守护进程、AI 流量无感分流不泄漏宿主 IP** 的场景。
> 对抗性审查报告归档：[`docs/analysis/11-antigravity-deployment-guide-review.md`](./analysis/11-antigravity-deployment-guide-review.md)。

---

## 架构概览与第一性原理 (Architecture & Principles)

```text
+-------------------------------------------------------------------------------+
| 本地客户端 (Clash Verge / Mihomo)                                            |
|   [Fake-IP: 198.18.0.1/16]                                                    |
|   [规则引擎]: 域名规则优先匹配 + 私网规则 no-resolve 强隔离                   |
+-------------------------------------------------------------------------------+
                                  |
                                  | 流量中继 (dialer-proxy: 前置选择)
                                  v
+-------------------------------------------------------------------------------+
| 商业中转前置跳板 (Upstream Transit Node: <TRANSIT_IP>)                        |
+-------------------------------------------------------------------------------+
                                  |
          +-----------------------+-----------------------+
          | (方案 A: 绝对主力)    | (方案 B: 次选拟态)    | (方案 C: 保底容灾)
          | Shadowsocks-2022      | VLESS-Reality         | VLESS-WS-TLS
          | :2083 (TCP+UDP)       | :2053 (TCP) / :2054   | :8443 (TCP)
          v                       v                       v
+-------------------------------------------------------------------------------+
| 落地机 (Landing VPS: <LANDING_IP>) [s-ui 单二进制，内存占用 ~13MB]             |
|   [系统依赖]: 强制 NTP 时钟对齐 (±30s 内)，杜绝 SS-2022 重放误杀              |
|                                                                               |
|   ┌─ 普通流量 ───────────> Direct 出口                                       |
|   ├─ AI 流量 (TCP) ─────> Cloudflare WARP 出口 (分级: 原生 WG 或 SOCKS5)       |
|   └─ AI 流量 (UDP) ─────> Block 丢弃 (防止 QUIC 绕过导致落地真实 IP 泄漏)     |
+-------------------------------------------------------------------------------+
```

### 1. 协议梯队设计原则
1. **方案 A (绝对主力工作马 - Shadowsocks-2022 `2022-blake3-aes-128-gcm`)**：
   - **原理**：无握手往返（0-RTT 加密报文头）、抗乱序、内存和 CPU 消耗极低。
   - **在中转链优势**：在中转跳板已具备 TLS/加密外层时，SS-2022 是性能最高、最不容易触发中转端重连异常的内层承载协议。
   - **关键前置**：必须保证宿主机 NTP 时钟同步误差 < 30 秒，否则协议防重放机制将静默丢弃所有合法连接。
2. **方案 B (次选拟态 - VLESS-Reality TCP + gRPC)**：
   - **TCP 节点关键准则**：必须**置空 `flow`**（严禁配置 `xtls-rprx-vision`）。Vision 流控强依赖底层原始 OS Socket 调用 Linux `splice()` 实现零拷贝加速，在中转链 (`dialer-proxy`) 的 TCP-in-TCP 嵌套环境下无法获取物理套接字，会导致连接持续重置。
   - **gRPC 节点警示**：开启 gRPC 多路复用（Multiplexing）在中转链网络抖动或丢包时存在 HTTP/2 队头阻塞风险，仅作为拟态备用，严禁充当高并发主力。
3. **方案 C (保底容灾 - VLESS-WS-TLS)**：
   - **原理**：标准 HTTP/1.1 WebSocket + TLS，绑定合规证书（`<YOUR_DOMAIN>`）及回源路径。
   - **闭环方案**：推荐直接采用 **Cloudflare 15年 Origin CA 证书**，无需开通 80 端口，无需外部 Let's Encrypt 续期守护进程，彻底实现自闭环。

---

## 阶段一：宿主机环境初始化

### 1. 系统、NTP 时钟与防火墙配置
在落地机执行（以 Ubuntu 22.04 / 24.04 为例）：
```bash
# 1. 开启 BBR 拥塞控制
echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
sysctl -p

# 2. 强制开启 NTP 时钟对齐（P1-3: 绝对关键基石，防止 SS-2022 握手误杀）
timedatectl set-ntp true || (apt update && apt install -y chrony && systemctl enable --now chrony)

# 3. 配置防火墙（严禁开放 2096 明文 HTTP 订阅端口）
ufw allow 22/tcp comment 'SSH'
ufw allow 2053/tcp comment 'VLESS-Reality-TCP'
ufw allow 2054/tcp comment 'VLESS-Reality-gRPC'
ufw allow 2083/tcp comment 'Shadowsocks-2022-TCP'
ufw allow 2083/udp comment 'Shadowsocks-2022-UDP'
ufw allow 8443/tcp comment 'VLESS-WS-TLS'
# 关闭公网明文订阅端口（P1-1: 消除攻击面与指纹探测）
ufw delete allow 2096/tcp 2>/dev/null || true
ufw --force enable
```

### 2. 本地 WARP AI 出口配置（硬件分级）
> [!IMPORTANT]
> **硬件分级指南（P1-2: 彻底防止 128MB 小鸡 OOM）**：
> - **128MB ~ 256MB 极小内存 VPS**：严禁安装官方 `cloudflare-warp` 包（`warp-svc` 守护进程常驻需 50~100MB，必定引发 OOM）。请直接在 `s-ui` 中配置 sing-box 原生的 `wireguard` outbound，单进程通吃出口，常驻内存锁定在 < 20MB。
> - **512MB ~ 2GB 内存 VPS**：可部署官方 `cloudflare-warp` 本地代理模式：

```bash
# （仅适用于 >= 512MB 内存机器）
apt install -y curl gpg
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflare-warp.list
apt update && apt install -y cloudflare-warp

# 切换为本地 SOCKS5 代理模式 (端口 40000)
warp-cli --accept-tos registration new
warp-cli --accept-tos mode proxy
warp-cli --accept-tos proxy port 40000
warp-cli --accept-tos connect

# 验证 WARP 出口
curl -x socks5://127.0.0.1:40000 https://cloudflare.com/cdn-cgi/trace
```

---

## 阶段二：`s-ui` 服务端部署

```bash
# 创建部署目录
mkdir -p /usr/local/s-ui/db

# 部署 s-ui 官方编译二进制至 /usr/local/s-ui/sui，并赋予执行权限
chmod +x /usr/local/s-ui/sui

# 注册服务文件 /etc/systemd/system/s-ui.service
cat <<'EOF' > /etc/systemd/system/s-ui.service
[Unit]
Description=s-ui Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/s-ui
ExecStart=/usr/local/s-ui/sui
Restart=on-failure
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable s-ui
```

---

## 阶段三：数据库与规则编排自动化脚本

> [!WARNING]
> **关键陷阱 (Gotcha)**：`inbounds` 表中的 `addrs`、`out_json`、`options` 列在 Go GORM 模型中定义为 `*json.RawMessage`，底层 SQLite 驱动严格要求写入 `BLOB` 二进制类型。若以普通字符串插入，启动时会报错：`sql: Scan error on column index 4, name "addrs": unsupported Scan, storing driver.Value type string into type *json.RawMessage` 并导致进程闪退崩溃。

在落地机创建脚本 `/root/setup_sui_matrix.py`（内置 SQLite 自动快照备份机制）：

```python
#!/usr/bin/env python3
"""
s-ui 三阶中转矩阵自动化配置注入脚本
适用：Ubuntu 22.04 / 24.04，Python 3
"""
import sqlite3
import json
import base64
import os
import shutil
import uuid

DB_PATH = "/usr/local/s-ui/db/s-ui.db"

# ==================== 占位符与配置参数 ====================
LANDING_DOMAIN = "<YOUR_DOMAIN>"        # 例: example.com
CERT_FILE = f"/etc/xray/certs/{LANDING_DOMAIN}/fullchain.pem"
KEY_FILE = f"/etc/xray/certs/{LANDING_DOMAIN}/privkey.pem"
FALLBACK_SNI = "www.oracle.com"         # Reality 伪装域名

# 动态生成密钥材料
USER_UUID = str(uuid.uuid4())
SS_KEY = base64.b64encode(os.urandom(16)).decode('utf-8')
REALITY_PRIVATE_KEY = "<YOUR_REALITY_PRIVATE_KEY>"
REALITY_PUBLIC_KEY = "<YOUR_REALITY_PUBLIC_KEY>"
REALITY_SHORT_ID = os.urandom(8).hex()

# ==================== 1. Sing-box 全局路由配置 ====================
GLOBAL_CONFIG = {
    "log": {"level": "info"},
    "dns": {
        "servers": [
            {"tag": "dns-remote", "type": "tls", "server": "1.1.1.1"},
            {"tag": "dns-direct", "type": "local", "detour": "direct"}
        ],
        "rules": []
    },
    "route": {
        "rules": [
            {"action": "sniff"},
            {"protocol": "dns", "action": "hijack-dns"},
            # 阻断私有地址防回环
            {
                "ip_cidr": [
                    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                    "127.0.0.0/8", "169.254.0.0/16", "fc00::/7", "fe80::/10"
                ],
                "outbound": "block"
            },
            # AI 域名分流至 WARP 出口
            {
                "domain_suffix": [
                    "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com",
                    "gemini.google.com", "aistudio.google.com", "generativelanguage.googleapis.com",
                    "anthropic.com", "claude.ai", "claude.site", "anthropicusercontent.com",
                    "challenges.cloudflare.com", "auth0.com"
                ],
                "network": "tcp",
                "outbound": "warp-official"
            },
            # 严格阻断 AI 域名的 UDP 流量，阻止浏览器通过 QUIC 绕过 SOCKS5 泄漏宿主真实 IP
            {
                "domain_suffix": [
                    "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com",
                    "gemini.google.com", "aistudio.google.com", "generativelanguage.googleapis.com",
                    "anthropic.com", "claude.ai", "claude.site", "anthropicusercontent.com",
                    "challenges.cloudflare.com", "auth0.com"
                ],
                "network": "udp",
                "outbound": "block"
            }
        ],
        "final": "direct",
        "auto_detect_interface": True
    },
    "experimental": {}
}

def to_blob(data: dict) -> sqlite3.Binary:
    """确保 GORM RawMessage 字段以 BLOB 存储"""
    return sqlite3.Binary(json.dumps(data).encode('utf-8'))

def main():
    # 自动快照备份 (P2-2: 防操作失误)
    if os.path.exists(DB_PATH):
        shutil.copyfile(DB_PATH, DB_PATH + ".bak")
        print(">> 已生成数据库安全快照备份")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. 注入 settings (订阅仅绑定本地，防止公网直连扫描)
    c.execute("UPDATE settings SET value = ? WHERE key = 'config'", (json.dumps(GLOBAL_CONFIG, indent=2),))
    c.execute("UPDATE settings SET value = '127.0.0.1' WHERE key = 'subListen'")

    # 2. 注入 outbounds
    c.execute("DELETE FROM outbounds")
    c.execute("INSERT INTO outbounds (id, type, tag, out_json) VALUES (1, 'direct', 'direct', ?)", (to_blob({}),))
    c.execute("INSERT INTO outbounds (id, type, tag, out_json) VALUES (2, 'socks', 'warp-official', ?)", 
              (to_blob({"server": "127.0.0.1", "server_port": 40000}),))
    c.execute("INSERT INTO outbounds (id, type, tag, out_json) VALUES (3, 'block', 'block', ?)", (to_blob({}),))

    # 3. 注入 inbounds (四路矩阵)
    c.execute("DELETE FROM inbounds")

    # 方案 B-1: VLESS-Reality-TCP (客户端必须置空 flow)
    reality_tcp_opts = {
        "users": [{"name": "personal", "uuid": USER_UUID, "flow": ""}],
        "tls": {
            "enabled": True,
            "server_name": FALLBACK_SNI,
            "reality": {
                "enabled": True,
                "handshake": {"server": FALLBACK_SNI, "server_port": 443},
                "private_key": REALITY_PRIVATE_KEY,
                "short_id": [REALITY_SHORT_ID]
            }
        }
    }
    c.execute("INSERT INTO inbounds (id, tag, protocol, listen, port, options, addrs, out_json) VALUES "
              "(2, 'reality-in', 'vless', '::', 2053, ?, ?, ?)",
              (to_blob(reality_tcp_opts), to_blob([]), to_blob({})))

    # 方案 A: Shadowsocks-2022 (绝对主力)
    ss2022_opts = {
        "network": "tcp,udp",
        "method": "2022-blake3-aes-128-gcm",
        "password": SS_KEY
    }
    c.execute("INSERT INTO inbounds (id, tag, protocol, listen, port, options, addrs, out_json) VALUES "
              "(3, 'ss2022-in', 'shadowsocks', '::', 2083, ?, ?, ?)",
              (to_blob(ss2022_opts), to_blob([]), to_blob({})))

    # 方案 B-2: VLESS-Reality-gRPC (应急备用)
    reality_grpc_opts = {
        "users": [{"name": "personal", "uuid": USER_UUID}],
        "transport": {"type": "grpc", "service_name": "proxy-grpc"},
        "tls": {
            "enabled": True,
            "server_name": FALLBACK_SNI,
            "reality": {
                "enabled": True,
                "handshake": {"server": FALLBACK_SNI, "server_port": 443},
                "private_key": REALITY_PRIVATE_KEY,
                "short_id": [REALITY_SHORT_ID]
            }
        }
    }
    c.execute("INSERT INTO inbounds (id, tag, protocol, listen, port, options, addrs, out_json) VALUES "
              "(4, 'reality-grpc-in', 'vless', '::', 2054, ?, ?, ?)",
              (to_blob(reality_grpc_opts), to_blob([]), to_blob({})))

    # 方案 C: VLESS-WS-TLS (CDN 兜底)
    vless_ws_opts = {
        "users": [{"name": "personal", "uuid": USER_UUID}],
        "transport": {"type": "ws", "path": "/cf-ws", "headers": {"Host": LANDING_DOMAIN}},
        "tls": {
            "enabled": True,
            "server_name": LANDING_DOMAIN,
            "certificate_path": CERT_FILE,
            "key_path": KEY_FILE
        }
    }
    c.execute("INSERT INTO inbounds (id, tag, protocol, listen, port, options, addrs, out_json) VALUES "
              "(5, 'vless-ws-in', 'vless', '::', 8443, ?, ?, ?)",
              (to_blob(vless_ws_opts), to_blob([]), to_blob({})))

    conn.commit()
    conn.close()
    print(">> s-ui 三阶中转矩阵数据库编排写入成功！")

if __name__ == "__main__":
    main()
```

---

## 阶段四：客户端配置与规则避坑

### 1. 节点导入与链式代理配置 (Clash Verge / Mihomo)
鉴于客户端无法直连落地机，建议将生成的 4 个节点直接写入本地 YAML 文件（`providers/vps.yaml`），在增强配置中设置 `dialer-proxy` 链式代理：

```yaml
# providers/vps.yaml (由本地离线配置生成，杜绝公网明文拉取)
proxies:
  - name: US-LA-ss2022-in
    type: ss
    server: <LANDING_IP>
    port: 2083
    cipher: 2022-blake3-aes-128-gcm
    password: <YOUR_SS2022_KEY>
    dialer-proxy: 前置选择 # 核心绑定：第一跳走中转跳板

  - name: US-LA-reality-in
    type: vless
    server: <LANDING_IP>
    port: 2053
    uuid: <YOUR_UUID>
    tls: true
    flow: "" # 必须留空！严禁开启 xtls-rprx-vision
    servername: www.oracle.com
    reality-opts:
      public-key: <YOUR_REALITY_PUBLIC_KEY>
      short-id: <YOUR_SHORT_ID>
    client-fingerprint: chrome
    dialer-proxy: 前置选择

  - name: US-LA-reality-grpc-in
    type: vless
    server: <LANDING_IP>
    port: 2054
    uuid: <YOUR_UUID>
    tls: true
    network: grpc
    grpc-opts:
      grpc-service-name: proxy-grpc
    servername: www.oracle.com
    reality-opts:
      public-key: <YOUR_REALITY_PUBLIC_KEY>
      short-id: <YOUR_SHORT_ID>
    client-fingerprint: chrome
    dialer-proxy: 前置选择

  - name: US-LA-vless-ws-in
    type: vless
    server: <YOUR_DOMAIN>
    port: 8443
    uuid: <YOUR_UUID>
    tls: true
    network: ws
    ws-opts:
      path: /cf-ws
      headers:
        Host: <YOUR_DOMAIN>
    dialer-proxy: 前置选择
```

### 2. Merge.yaml 关键避坑：Fake-IP 与 `lancidr` 规则拦截死锁
> [!CAUTION]
> **极其隐蔽的高频生产 Bug (P2-3)**：
> - Clash / Mihomo 在开启 Fake-IP 模式时分配 `198.18.0.1/16`。
> - 许多维护规则集（如 Loyalsoldier `lancidr.yaml`）包含 RFC 2544 基准测试网段 `198.18.0.0/15`。
> - 若将 `RULE-SET,lancidr,DIRECT` 置于 `RULE-SET,proxy` 之前，任何未提前硬编码的境外域名（如 `api.openai.com`、`x.com`）解析出 Fake-IP 后，都会**优先命中 `lancidr` 走本地 DIRECT**，导致连接阻断且报 421/超时错误。

**正确规则顺序基准（Merge.yaml）**：
```yaml
rules:
  # 1. 专用业务直连
  - DOMAIN-SUFFIX,superboss.cc,DIRECT
  - DOMAIN-SUFFIX,dingtalk.com,DIRECT

  # 2. 境外规则集【必须置顶于 lancidr 之前】
  - RULE-SET,google,节点选择
  - RULE-SET,proxy,节点选择
  - RULE-SET,telegramcidr,节点选择,no-resolve
  - GEOIP,google,节点选择

  # 3. 国内与私网直连规则集【必须置后，且私网规则强制附加 no-resolve】
  - GEOIP,CN,DIRECT,no-resolve
  - RULE-SET,direct,DIRECT
  - RULE-SET,apple,DIRECT
  - RULE-SET,lancidr,DIRECT,no-resolve   # 必须附加 no-resolve
  - RULE-SET,cncidr,DIRECT,no-resolve    # 必须附加 no-resolve

  # 4. 兜底
  - MATCH,节点选择
```

---

## 阶段五：端到端验证与健康排查

### 1. 客户端延迟测定 (通过 Mihomo REST API)
在客户端执行以下 PowerShell 检查 Provider 中各节点的连通性与延迟：
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:9097/providers/proxies/VPS/healthcheck" `
  -Headers @{ Authorization = "Bearer <YOUR_SECRET>" }

$res = Invoke-RestMethod -Uri "http://127.0.0.1:9097/providers/proxies/VPS" `
  -Headers @{ Authorization = "Bearer <YOUR_SECRET>" }

$res.proxies | Select-Object name, type, alive, @{N='Delay';E={$_.history[-1].delay}}, dialer-proxy
```
**合格标准**：
- 四个节点均为 `alive: True`。
- `dialer-proxy` 显示为 `前置选择`。
- 延迟通常在 280ms ~ 350ms 之间（取决于中转跳板物理距离）。

### 2. 落地机分流审计
在落地机执行：
```bash
journalctl -u s-ui -f
```
发起请求时观察：
1. 普通流量：
   ```text
   INFO - inbound/shadowsocks[ss2022-in] inbound connection from <TRANSIT_IP>:11254
   INFO - outbound/direct[direct] outbound connection to www.google.com:443
   ```
2. AI 请求（如访问 `api.openai.com`）：
   ```text
   INFO - inbound/vless[vless-ws-in] [personal] inbound connection to api.openai.com:443
   INFO - outbound/socks[warp-official] outbound connection to api.openai.com:443
   ```
- 入站来源必须为 `<TRANSIT_IP>`（无客户端直连）。
- AI 域名出站必须为 `warp-official`，落地宿主真实 IP 零泄漏。
