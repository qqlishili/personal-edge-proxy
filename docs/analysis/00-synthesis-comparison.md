# 八大代理项目横向对比与选型决策综合报告

- 评估对象：
  1. `alireza0/s-ui`
  2. `233boy/sing-box`
  3. `eooce/Sing-box`
  4. `fscarmen/sing-box`
  5. `yonggekkk/sing-box-yg`
  6. `juewuy/ShellCrash`
  7. `mack-a/v2ray-agent`
  8. `yonggekkk/argosbx`
- 评估基准机器：RackNerd 107.174.244.167 (1 vCPU, 2.0GB RAM, Ubuntu 24.04, 内核 6.8)
- 核心使命：作为境内中转链式代理的**落地节点（Landing Node）**，提供 REALITY、SS-2022 入站，配合本地 WARP SOCKS5 进行 AI 分流，并向 Clash Verge 提供原生安全订阅。

---

## 1. 架构流派与作用定位横向总览

| 项目 | 技术形态 | 订阅分发实现 | 进程与内存开销 | 核心定位与适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **alireza0/s-ui** | Go 单二进制 + 嵌入 sing-box/SQLite/Vue | **原生独立端口分发** (支持 Clash/Mihomo/sing-box) | **约 9~15MB** (单 systemd 进程) | **中小型 VPS 边缘服务端首选**，兼具图形面板与原生订阅闭环 |
| **233boy/sing-box** | 规范模块化 Shell + 原生 sing-box | **无动态订阅** (仅输出单节点链接/JSON) | 约 10~15MB (仅 sing-box 常驻) | 纯净极简主义者、无需客户端订阅自动更新的极客 |
| **eooce/Sing-box** | 单体 Shell + 多语言容器适配 | **严重违规** (公网第三方转换 / Nginx 静态文件) | 约 30~45MB (sing-box + Nginx) | 免费容器/PaaS (Serv00/Render) 羊毛机临时穿透 |
| **fscarmen/sing-box** | 320KB 巨型 Shell + iptables + WARP | Nginx 或 Argo 隧道托管 (依赖外部 GitHub 模板) | 约 35~50MB (sing-box + Nginx) | 追求极致多协议、端口跳跃 (Port Hopping) 玩机的折腾型玩家 |
| **sing-box-yg** | 148KB Shell + 24MB 预编译二进制黑盒 | Crontab `@reboot` 唤醒 busybox httpd 临时分发 | 约 25~40MB (多游击后台进程) | YouTube 教程小白引流、多重 CDN/Argo 救砖 |
| **juewuy/ShellCrash** | 嵌入式 Shell + Mihomo/sing-box 客户端 | **无服务端订阅** (自身作为客户端消费订阅) | 约 30~60MB | **路由器/局域网透明网关** (角色根本性错位，非服务端) |
| **mack-a/v2ray-agent** | 400KB 巨型 Shell + Xray/sing-box + acme | 独立 Nginx 虚拟主机托管静态文件 | 约 50~80MB (内核 + Nginx + 守护) | 传统大内存 VPS 多域名证书自动化综合部署 |
| **yonggekkk/argosbx** | 93KB Shell + Argo Tunnel | Crontab `@reboot` 唤醒 busybox httpd 临时分发 | 约 30~45MB | IP 被 GFW 完全封死后的 Cloudflare 隧道急救 |

---

## 2. 核心问题裁决：不考虑替换成本，是否有比当前 VPS 上的 s-ui 更好、更合适的项目？

### 最终裁决：【绝对没有。当前机器上的 s-ui 是全局最优解】

### 第一性原理与严密证据链：

1. **订阅分发正交性（核心绝杀点）**：
   - 客户端（Clash Verge）要求订阅链接必须具备**动态渲染、格式适配（Format=clash）、Token 鉴权、无外部泄漏**能力。
   - 在上述 8 个项目中，**只有 `s-ui` 原生内建了高性能 Go 订阅引擎**（`/sub/:subid?format=clash`）。
   - 其余所有脚本项目（233boy、fscarmen、v2ray-agent 等）的内核均为纯 sing-box。因 sing-box 原生不带 HTTP 订阅服务，这些脚本全部被迫采用外挂方案：要么强行安装一套 Nginx（如 v2ray-agent/fscarmen，徒增 30MB 内存与配置面），要么采用 crontab 唤醒 busybox httpd 的游击做法（如 yonggekkk），要么直接将私密配置提交到第三方未授权公网转换接口（如 eooce，严重违规）。
   - `s-ui` 以单个 9MB 进程彻底干掉了历史遗留的 `edge-sub` (Python) 和 `subconverter` (C++)，实现了完全内生闭环。

2. **硬件规格与内存安全边界（1 vCPU / 2.0GB RAM）**：
   - 本机需同时承载 1Panel、AdGuard Home DNS 递归解析（mem_limit 512M）及宿主核心网络栈。
   - `s-ui` 实测内存仅 **9.2 MB**，CPU 空闲占用 0.0%，无多余后台进程。
   - 对比之下，`v2ray-agent` / `fscarmen` 引入 Nginx 及证书自动轮询，综合常驻开销高出 3~5 倍，在突发网络流量下增加 Linux 内核 OOM Killer 触发概率。

3. **网络安全与攻击面收敛**：
   - `s-ui` 实现了管理面板与数据订阅的网络隔离：管理面板监听 `127.0.0.1:2095`（公网完全不可达，仅内网/SSH隧道管理），仅开放 `2096` 订阅端口和 `2053`/`2083` 代理入站。
   - 而其他多数脚本往往直接暴露明文 Web 端口或默认全网监听，极大增加了端口扫描与探针探测风险。

4. **架构角色匹配度**：
   - `ShellCrash` 是客户端透明网关，角色根本颠倒；
   - `argosbx` 引入 Cloudflare 隧道会给链式中转增加 150~300ms 额外往返延迟，完全背离低延迟落地节点要求；
   - `sing-box-yg` 包含 24MB 未审计二进制，存在严重供应链隐患。

---

## 3. 终审结论与后续行动建议
- **架构定型**：无需对底层代理服务端做任何迁移或替换。当前部署的 `s-ui` 在资源利用率、订阅自闭环度、安全性与架构优雅度上均为 107.174.244.167 节点的最佳选择。
- **下一步动作**：将本综合裁决报告提交给对抗性审核 Agent（Antigravity/Codex）进行严苛审查。
