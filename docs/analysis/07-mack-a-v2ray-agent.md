# 项目分析报告：mack-a/v2ray-agent (vasma)

- 项目地址：https://github.com/mack-a/v2ray-agent
- 本地源码路径：`/root/code/v2ray-agent`
- 分析基准：`personal-edge-proxy` 架构规范与 107.174.244.167 (1C2G) 运行环境

---

## 1. 项目架构与实现形态
- **技术栈**：超大型单体 Bash 脚本 (`install.sh`, 401KB, 6500+ 行代码) + Xray-core / sing-box 双内核支持 + Nginx 基础设施。
- **运行模式**：终端交互式菜单 (`vasma` CLI)；通过 systemd 管理 Xray/sing-box 与 Nginx 服务；自动申请并轮转 Let's Encrypt / ZeroSSL 证书。
- **订阅分发机制**：脚本生成本地静态订阅配置 (`/etc/v2ray-agent/subscribe_local/`)，通过配置独立的 Nginx `subscribe.conf` 虚拟主机提供 HTTP/HTTPS 订阅拉取。

---

## 2. 核心优劣势对比（对比 personal-edge-proxy 需求）

### 优势
1. **工程成熟度极高**：经过长达数年、海量用户的实际验证，协议配置模板规范，边界处理严密。
2. **TLS 证书生命周期闭环**：内置完善的 acme.sh 证书申请、续期与多域名自动化管理流程。
3. **双内核灵活兼容**：同时覆盖 Xray 生态与 sing-box 生态，对各类客户端协议兼容性极佳。

### 劣势
1. **组件开销重（依赖 Nginx 托管订阅）**：无法独立提供订阅服务，必须安装并常驻 Nginx 进程，在 2GB 内存物理机上额外消耗内存与端口资源。
2. **维护与排错成本高（TCO 高）**：超过 400KB 的超巨型 Shell 脚本缺乏模块化单元测试，配置逻辑散落在各类局部变量与文本替换中，一旦出现状态漂移难以定位。
3. **缺乏现代化 WebUI 与可编程接口**：仅支持终端人机交互，无法通过外部 RESTful API 自动化集成或在本地面板进行可视化监控。
4. **多进程并发内存偏高**：完整部署（sing-box/xray + nginx + 证书守护）总内存开销通常在 50~80MB，显著高于单一 Go 二进制方案。

---

## 3. 适用性评级
- **当前机器适配度**：★★★☆☆ (6.0/10)
- **结论**：虽然是 CLI 脚本中最稳定成熟的代表作之一，但**依赖 Nginx 托管订阅带来的架构冗余与超大 Shell 脚本的高维护成本**，使其在 1C2G 场景下明显逊色于 s-ui。
