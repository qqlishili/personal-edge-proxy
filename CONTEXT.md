# Domain Model & Context: Personal Edge Proxy

## 核心物理边界与铁律 (Physical Invariants)

- **物理直连不可达 (No Direct Client Egress)**: 本地物理机（境内客户端）受限于网络路由与 GFW 阻断，**绝对无法直连** 107.174.244.167 落地机。
- **全链路中转依赖 (100% Transit Invariant)**: 所有客户端请求必须 100% 经由“上一级中转节点”（Transit Node）中继转达落地机。
- **直连协议完全无效化**: 严禁在落地机部署任何假设客户端能直连的协议（如单端 Hysteria 2 / TUIC），任何入站必须 100% 兼容中转链路（dialer-proxy / realm / iptables 虚拟流）。

## 核心定义与术语表 (Glossary)

- **Landing Node (落地节点)**: 境外代理边缘服务器（本物理机 107.174.244.167），负责终结境内中转节点的加密流量，并将特定流量转发出境。
- **Transit/Relay Node (上一级中转节点)**: 位于客户端与落地机之间的中继服务器（如 IPLC 专线、国内高带宽 VPS、海外反代机），核心瓶颈为跨国出海段的抗抖动与防阻断能力。
- **Chain Proxy (链式代理)**: 境内客户端 -> 境内中转节点 -> 境外落地节点（SS-2022 / VLESS-Reality）的网络拓扑结构。
- **AI Egress (AI 出口分流)**: 落地机通过本地 WARP SOCKS5 (`127.0.0.1:40000`) 路由特定 AI 厂商流量（OpenAI, Gemini, Claude），隐藏原生机房数据中心 IP。
- **Subscription Engine (订阅分发引擎)**: 负责向客户端（如 Clash Verge）分发动态配置的 HTTP 端点，必须支持 Token 鉴权与安全隔离。
- **SS-2022 Inbound (中转专线主力)**: 纯对称流加密，不依赖 TLS 握手，对中转虚拟流与 NAT 转发 100% 免疫，千兆满载 CPU < 3%。
- **REALITY Standard Inbound (公网中转伪装)**: 借用外部真实 TLS 证书但**彻底剔除 Vision 流控**的标准 TCP 流，确保在中转虚拟流中顺畅完成 TLS 1.3 握手。
- **Public CDN Fallback (公共中转兜底)**: 当私有上一级中转机全盘故障时，借助 Cloudflare CDN 充当公共中转跳板（Client -> CDN -> 落地机）的紧急通道。
