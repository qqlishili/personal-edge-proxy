# 项目分析报告：yonggekkk/sing-box-yg

- 项目地址：https://github.com/yonggekkk/sing-box-yg
- 本地源码路径：`/root/code/sing-box-yg`
- 分析基准：`personal-edge-proxy` 架构规范与 107.174.244.167 (1C2G) 运行环境

---

## 1. 项目架构与实现形态
- **技术栈**：单体 Bash 脚本 (`sb.sh`, 148KB) + 仓库直带的 24MB 未知预编译已剥离二进制 (`sbwpph_amd64`, `sbwpph_arm64`)。
- **运行模式**：非标准进程守护，混用后台 nohup、crontab `@reboot` 唤醒 busybox httpd，或借助外部 GitLab 私有仓库拉取配置。
- **订阅分发机制**：通过临时拉起的 `busybox httpd` 本地静态目录托管 `clmi.yaml` / `sbox.json`，或者利用 GitLab API 远程中转。

---

## 2. 核心优劣势对比（对比 personal-edge-proxy 需求）

### 优势
1. **多重伪装与隧道方案**：针对封锁极其严重的 IP，集成了 Cloudflare Argo 临时/固定隧道穿透方案。
2. **多出站 WARP 预设组合**：提供了针对流媒体解锁的预设出站规则。

### 劣势（存在重大安全隐患与不合规项）
1. **严重供应链安全隐患**：代码仓库内直接包含体积高达 24MB 的二进制黑盒文件 (`sbwpph_amd64`)，缺乏可审计的开源构建链路，违反基本服务器安全合规准则。
2. **服务守护非正规化（Crontab/Busybox 游击进程）**：订阅服务不使用正规 systemd 管理，而是通过向 `/tmp/crontab.tmp` 注入 `@reboot ... busybox httpd` 并在后台野蛮执行，极易在系统维护或重启后失联。
3. **系统环境污染**：脚本执行过程中直接强制修改 `/etc/hosts`、反复探测并修改全局 sysctl，缺乏事务性与自动回滚机制。
4. **强行营销注入**：代码与终端交互中大量硬编码个人 YouTube 频道推广与订阅引流，非纯粹工程工具。

---

## 3. 适用性评级
- **当前机器适配度**：★☆☆☆☆ (1.5/10)
- **结论**：因**未经审计的二进制黑盒、非规范的 crontab 游击守护以及严重系统污染风险**，绝对禁止在生产环境中部署。
