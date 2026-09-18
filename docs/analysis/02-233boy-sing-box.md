# 项目分析报告：233boy/sing-box

- 项目地址：https://github.com/233boy/sing-box
- 本地源码路径：`/root/code/233boy-sing-box`
- 分析基准：`personal-edge-proxy` 架构规范与 107.174.244.167 (1C2G) 运行环境

---

## 1. 项目架构与实现形态
- **技术栈**：模块化 Bash 自动化脚本 (`src/core.sh`, `download.sh`, `systemd.sh` 等) + 官方原版 sing-box 二进制。
- **运行模式**：原生 systemd 托管官方 sing-box 进程；管理操作通过终端交互式命令行 (`sing-box` CLI) 触发。
- **网络与服务设计**：
  - 严格遵循官方 sing-box 的 `config.json` 规范。
  - 纯后端代理服务，不包含任何内嵌 Web 守护进程或 HTTP 订阅服务器。

---

## 2. 核心优劣势对比（对比 personal-edge-proxy 需求）

### 优势
1. **纯净规范无残留**：脚本结构在所有 Shell 脚本中最为严谨规范，不注入非标二进制，不污染系统环境变量或 crontab。
2. **官方核心直接升级**：直接从 GitHub Release 拉取官方 sing-box 二进制，不受第三方内嵌二次修改限制。
3. **零空闲管理内存**：管理端仅在终端执行时短暂运行 Shell，日常运行时仅有 sing-box 自身常驻（RAM ~10-15MB）。
4. **标准 systemd 集成**：标准服务启停与日志输出 (`journalctl -u sing-box`)，无自造进程守护机制。

### 劣势
1. **缺失原生动态订阅服务**：不支持向外部客户端（如 Clash Verge）提供 HTTP 自动更新订阅 URL，只能生成静态单节点链接或导出 JSON。
2. **需要外挂订阅管道**：若要实现 Clash 自动更新，必须重新引入 Python/Subconverter/Nginx，重新加重系统负担。
3. **无 WebUI 与多用户管理**：完全依赖 SSH 命令行交互，缺乏针对多节点、多协议、多密钥的图形化管理界面。

---

## 3. 适用性评级
- **当前机器适配度**：★★★☆☆ (6.5/10)
- **结论**：核心运行非常干净规范，但因**缺乏原生动态订阅服务**，无法独立闭环满足 Clash Verge 订阅分发需求。
