# 项目分析报告：eooce/Sing-box

- 项目地址：https://github.com/eooce/Sing-box
- 本地源码路径：`/root/code/eooce-sing-box`
- 分析基准：`personal-edge-proxy` 架构规范与 107.174.244.167 (1C2G) 运行环境

---

## 1. 项目架构与实现形态
- **技术栈**：单体 Bash 脚本 (`sing-box.sh`, 97KB) + 混合多语言 PaaS 适配器 (Go/Node/Python/PHP 目录用于 Serv00, Koyeb, Render 等免费容器平台)。
- **运行模式**：主脚本通过 Shell 组装 JSON 配置文件，调用 systemd 或后台运行 sing-box；安装独立 Nginx 实例用于托管订阅静态文件。
- **订阅分发机制**：将节点信息输出到 `url.txt`，Base64 编码为 `sub.txt`，经由 Nginx 暴露 HTTP 端口，并通过第三方公网转换服务 (`https://sublink.eooce.com`) 拼装 Clash 订阅。

---

## 2. 核心优劣势对比（对比 personal-edge-proxy 需求）

### 优势
1. **多平台通用性强**：兼顾 Serv00、免费容器及常规 VPS，覆盖非 root 环境的运行需求。
2. **快速开箱多协议**：支持 VLESS-Reality、Hysteria2、TUIC、AnyTLS 等主流协议一键部署。

### 劣势（存在重大安全与架构缺陷）
1. **致命安全隐患（节点凭据公网泄露）**：其 Clash 订阅生成逻辑直接硬编码调用第三方公网 Subconverter：
   `https://sublink.eooce.com/clash?config=http://${server_ip}:${nginx_port}/${password}`
   将本机的 IP、端口、密码与节点私密参数完全暴露给未受信任的第三方公共转换服务器，严重违反安全准则。
2. **组件臃肿冗余**：仅为了暴露一个静态 `sub.txt`，脚本强行安装并配置一套 Nginx，增加系统攻击面与约 15~25MB 额外内存开销。
3. **架构杂乱、维护性差**：仓库中混杂多种语言 PaaS 部署文件，缺乏清晰的组件边界与配置隔离。
4. **缺乏正交路由控制**：出站规则与 WARP 分流高度耦合在脚本交互中，无法灵活实现目标域名级别的精密 AI 出口分流。

---

## 3. 适用性评级
- **当前机器适配度**：★☆☆☆☆ (2.0/10)
- **结论**：因**第三方公网订阅转换导致的严重私密凭据泄露风险**以及依赖额外 Nginx 的冗余架构，绝对不可用于生产落地机。
