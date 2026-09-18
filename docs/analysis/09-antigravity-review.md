# Antigravity 对抗性审查裁决报告

- 审查方：Google Antigravity (`agy_acp_server`) / `docs-reviewer`
- 审查任务 ID：`9c5d747d-ba78-4f76-a2f1-cbc9707aac35`
- 裁决结论：**VERDICT: [RETHINK]**
- 缺陷定级统计：P0 = 1, P1 = 2, P2 = 2

---

## 核心反思与对抗性证伪点

### 1. 稻草人基准与排他性断言偏差 (P0-1)
- 原推论将对比范围限定在低质 Shell 脚本（233boy, eooce, fscarmen, yonggekkk 等）之间，得出“s-ui 为全局绝对最优解”犯了排他性与稻草人偏差。
- **第一性原理反例**：在单人专用的 1C2G 落地机上，节点拓扑极度固定（SS-2022 + REALITY），最稳固且内存最小的方案不是带 SQLite 状态机的 Web 面板，而是：
  **官方原生 sing-box (GitOps 声明式单一 config.json) + 宿主机已有的 1Panel (OpenResty) 静态托管 40 行 clash.yaml 订阅**。

### 2. S-UI 内部状态机与 sing-box 核心版本耦合风险 (P1-1)
- s-ui 并非单进程一体化，底层通过脚本或子进程调用外部独立编译的 sing-box 核心。
- 当 sing-box 语法或协议发生破坏性演进时，s-ui 的 SQLite ORM 映射易导致 Crash Loop（如 Issue #1199, #234）。

### 3. 公网暴露 2096 订阅端口的安全盲区 (P1-2)
- 2096 端口直面公网，由 Go 标准库 HTTP Server 提供动态查表与模板渲染。
- 宿主机已运行 1Panel，却未将 2096 经由 OpenResty 进行安全加固（反代、防枚举、WAF、限流）。

### 4. 生态成熟度对比项目
- 若确实需要 Web 面板，`3x-ui` (MHSanaei, 22k+ stars) 在社区规模、双核心维护、跨版本兼容测试上是 s-ui 的数倍。

---

## 落地改进路线建议
1. **短期加固（维持 s-ui）**：
   - 将 2096 端口修改为仅监听 `127.0.0.1:2096`。
   - 通过宿主机 1Panel (OpenResty) 反向代理并配置 Rate Limiting、高强度 Token 路径及 SSL 证书。
2. **长期架构演化（终极极简）**：
   - 原生 sing-box systemd + 1Panel 静态托管 `clash.yaml`。
