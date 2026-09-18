# 项目分析报告：juewuy/ShellCrash

- 项目地址：https://github.com/juewuy/ShellCrash
- 本地源码路径：`/root/code/ShellCrash`
- 分析基准：`personal-edge-proxy` 架构规范与 107.174.244.167 (1C2G) 运行环境

---

## 1. 项目架构与实现形态
- **技术栈**：面向嵌入式设备与路由器的 Shell 脚本管理套件 + Mihomo (Clash Meta) / sing-box 客户端核心。
- **运行模式**：透明代理网关模式（基于 iptables/nftables 的 TProxy、TUN 或 Redir 重定向）。
- **设计定位**：针对 OpenWrt 路由器、软路由及内网 Linux 客户端设备的**透明代理网关工具**。

---

## 2. 核心优劣势对比（对比 personal-edge-proxy 需求）

### 优势
1. **优秀的客户端分流引擎**：在路由器或局域网设备上能够极好地实现全局或局部设备的透明翻墙与 DNS 分流。
2. **丰富的 Clash 规则集支持**：支持直接加载 Clash YAML 订阅与复杂 Rule-Provider。

### 劣势（架构层级根本性错位）
1. **错置的架构角色（客户端 ≠ 服务端）**：
   - 当前 VPS（107.174.244.167）的角色是**境外边缘代理服务端（Landing Inbound Node）**，负责在公网监听端口（如 REALITY、SS-2022），为境内客户端提供安全接入。
   - ShellCrash 的本质是**客户端分流代理网关（Client Gateway/Router Redirector）**，其作用是“消费”订阅并劫持局域网流量，**它完全不具备服务端协议入站监听（VLESS-Reality Server, SS-2022 Server）的管理与下发能力**。
2. **协议与订阅角色倒置**：ShellCrash 自身需要向外部订阅节点，无法作为节点生产者为移动端或桌面端（Clash Verge）提供订阅下发服务。
3. **网络栈冲突隐患**：其内置的 TProxy/TUN 路由劫持会严重破坏 VPS 现有的网络转发、Docker 容器桥接以及 SSH 远端访问路由。

---

## 3. 适用性评级
- **当前机器适配度**：☆☆☆☆☆ (0/10 - 架构层级完全错配)
- **结论**：**定位完全相反**。ShellCrash 是局域网路由器“出站客户端”，而本项目需要的是境外边缘“入站服务端”，绝对不适用。
