# ADR 0001: 边缘代理服务核心与三阶中转抗灾矩阵选型

- **状态**：已采纳并实施 (Accepted & Implemented)
- **日期**：2026-09-18
- **决策者**：用户 & AI 维护者

## 上下文与约束
目标主机为 1 vCPU, 2.0GB RAM 的 Ubuntu 24.04 VPS（RackNerd 107.174.244.167），已承载 1Panel 与 AdGuard Home（内存硬限 512MB）。
物理铁律：境内客户端绝对无法直连该落地机，所有流量必须 100% 经由上一级中转（Transit Node）。
核心要求：落地机必须提供对抗中转抖动、长连接并发与中转机全死等极端场景的容灾能力，同时配合 WARP SOCKS5 (127.0.0.1:40000) 进行 AI 分流，并向 Clash Verge 提供免泄密的原生自动更新订阅。

## 架构裁决（三阶中转矩阵）
1. **方案 A（中转主干双模）**：
   - `ss2022-in` (端口 `2083`, Blake3-AES-128-GCM)：专线/优质中继主力，纯对称流，对中转链 100% 免疫，CPU < 3%。
   - `reality-in` (端口 `2053`, VLESS-Reality TCP)：普通公网中转伪装，借用 Oracle 真实 TLS 1.3 握手；**彻底清空 `flow` 字段（剔除 Vision）**，消除 dialer-proxy 嵌套下的 splice 崩溃与断连死锁。
2. **方案 B（长连接多路复用通道）**：
   - `reality-grpc-in` (端口 `2054`, VLESS-Reality gRPC, serviceName: `proxy-grpc`)：面向低配或高并发中转机，仅维持 1 条 HTTP/2 TCP 连接，内部承载上千路虚拟并发，大幅减轻中转机 Socket/握手开销。
3. **方案 C（公共 CDN 终极避难所）**：
   - `vless-ws-in` (端口 `8443`, VLESS-WebSocket + TLS, 路径 `/cf-ws`, 域名 `okkla.xyz`)：复用宿主机现有的 `okkla.xyz` 证书。当所有私有中转机宕机失联时，由 Cloudflare CDN 充当免费公共中转出海。
4. **出口分流矩阵**：
   - 普通流量 -> VPS Direct
   - AI 流量（OpenAI, Claude, Gemini, Cloudflare Turnstile, Auth0） -> TCP 路由至本地 WARP SOCKS5 (`127.0.0.1:40000`)，UDP 路由严格 `block` 熔断，强制降级为 TCP/TLS，杜绝宿主机原生机房 IP 泄漏。

## 实施与验证结果
- 全套入站 100% 遵照 `/root/code/s-ui` 原生源码驱动（零外挂脚本、零 Nginx、零 subconverter）。
- 端口 `2083`、`2053`、`2054`、`8443`、`2096` 全部在线监听。
- Clash Verge 订阅接口动态聚合输出 4 个中转节点与 Proxy / Auto 分组，实测解析正常。
