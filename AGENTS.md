# AGENTS.md — AI maintainer / deployer guide

Read this file before editing, procuring, or deploying this repository.

## 1. Core model

Keep the architecture separated into two independent layers:

```text
Inbound  = how the client reaches the VPS
Outbound = how the VPS reaches a destination
```

Do not confuse inbound redundancy with outbound identity/reputation.

Typical inbound roles:

```text
Hysteria2                    primary daily entry
VLESS + REALITY + Vision     optional TCP backup
VLESS + WS + CF Tunnel       optional emergency entry
```

Typical outbound roles:

```text
VPS direct       ordinary traffic
WARP             preferred selected-AI egress
fixed SOCKS5     optional stable egress for selected services
block            explicit deny / fail-closed
```

### 1.1 Execution principle — minimize human manual work

The project should require as little manual work from the human as reasonably possible.

Use this order of preference:

```text
AI can safely do it with available tools
        -> AI does it

AI cannot do it, but can inspect/interpret the result
        -> give the human the smallest necessary action
        -> human runs/clicks it
        -> AI interprets the result and decides the next step

Action inherently requires the human
(payment / MFA / CAPTCHA / provider acceptance / physical-local-network action)
        -> explain exactly what the human must do and why
        -> continue immediately after the result is available
```

Rules:

1. **Do not make the human copy and run commands that the agent can already execute itself.**
2. If local shell, SSH, browser, connector, or other authorized tools are available, use them directly when the action is safe and within the user's request.
3. Do not ask the human to manually read traceroute, ping, logs, JSON, or configuration output if the agent can read and interpret it.
4. If a test must originate from the human's real home/campus/mobile network and the agent cannot run there, give a short copy-paste command and ask for the raw output; the agent should do the analysis.
5. Keep manual steps small and sequential. Do not dump twenty commands on a beginner and ask them to diagnose the result themselves.
6. Never ask the human to paste SSH private keys, payment-card details, root passwords, provider passwords, or other secrets into chat or the repository.
7. Use existing authenticated/local access paths where possible: local `ssh`, SSH Agent, `~/.ssh/config`, provider console already opened by the user, or connected tools.
8. When the only available environment is a normal chat interface with no shell/browser access to the user's machine, **act as the operator's guide**: tell the human exactly what to run/click, what output to send back, and then continue the reasoning yourself.
9. State capability boundaries plainly. Do not pretend a command was run when it was only suggested.

The human should make decisions that genuinely require judgment or consent; the AI should absorb routine execution and technical interpretation.

---

## 2. Deployment profiles — recommended interpretation

Profiles are not strictly cumulative. Use the profile that matches the user's real goal.

### Profile A — minimum viable

```text
Client -> HY2 -> VPS -> Direct
```

Use when the user only wants a simple working personal node.

Trade-off: AI services see the VPS data-center egress directly. Depending on region, IP reputation, and provider history, users may encounter availability challenges, CAPTCHAs, regional mismatches, or account-security checks.

Do **not** claim that this guarantees account suspension or that data-center IPs are universally unusable.

### Profile B — inbound-resilient direct egress

```text
HY2 primary
+
REALITY backup
+
VPS Direct egress
```

This reduces **inbound protocol failure risk** when UDP is poor or unavailable.

It does **not** materially improve the final egress identity versus Profile A, because destinations still see the VPS Direct IP.

### Profile C — WARP-selected AI egress

```text
HY2 -> VPS
        |- ordinary traffic -> Direct
        `- selected AI      -> WARP Local Proxy
```

Use when the user wants to reduce dependence on the VPS's raw data-center egress for AI/SaaS traffic.

This is the preferred starting profile for an AI-heavy use case.

REALITY is optional here; do not force it if HY2 is stable.

### Profile D — recommended practical AI profile

```text
HY2 -> VPS
        |- ordinary traffic          -> Direct
        |- OpenAI / ChatGPT / Codex  -> WARP
        |- Gemini / Google AI        -> WARP
        `- Claude / Anthropic        -> trusted fixed SOCKS5 (optional by policy)
```

This is the repository maintainer's **preferred practical profile** when the user primarily uses AI services and also wants a deliberately stable Claude/Anthropic egress.

Do not claim:

- that WARP is residential;
- that Claude requires residential IPs;
- that this profile guarantees avoiding bans or risk checks;
- that any service must use these exact routes.

### Profile E — extra inbound resilience

Start from Profile D, then optionally add:

```text
VLESS + REALITY + Vision
Cloudflare Tunnel / VLESS WS
```

Use only when the user actually wants more inbound fallback paths.

This is an **availability enhancement**, not an egress-reputation enhancement.

### Default deployment rule

If the user says only "set this up for AI use" and provides no contrary preference:

1. prefer **Profile C** as the default balanced target;
2. upgrade to **Profile D** if the user has/provides a trusted fixed egress and wants Claude/Anthropic pinned to it;
3. add REALITY only when the user wants TCP fallback or the network has real UDP problems;
4. add Cloudflare Tunnel only as an extra emergency entry.

Do not overbuild simply because example files exist.

---

## 3. VPS procurement guidance — understand first, search second

If the user has **not bought a VPS yet**, do not jump directly to installation commands.

First read and follow:

- [`docs/vps-selection.md`](./docs/vps-selection.md)

The agent's job is to help the human make a procurement decision, not merely repeat VPS marketing specs.

### 3.1 Use the project's “impossible triangle”

Treat VPS selection as a balance between:

```text
                 route / speed
        latency · loss · peak hour
          UDP · stable throughput
                       ▲
                      / \
                     /   \
                    /     \
             config ─────── price
       CPU/RAM/disk/traffic  real long-term cost
```

This is not a literal mathematical impossibility. It is a decision framework:

> **Understand the user's real need first, set minimum acceptable thresholds for all three corners, then find the best balance inside the budget.**

For the repository's default **daily HY2 / AI relay** scenario, use this unified top-level weighting:

```text
route / stability  50%
price              30%
configuration      20%
```

This must stay synchronized with `docs/vps-selection.md` Section 5 and its sub-score tables.

AUP, UDP permission, public-address requirements, provider recovery capability, and other essential constraints are **hard eligibility gates**, not a fourth weighted corner. A candidate that fails a hard requirement is removed before scoring.

Do not assume that a larger CPU/RAM package is better for a personal relay. Once the workload crosses its practical minimum, better routing and stability may be more valuable than unused compute.

### 3.2 Ask high-leverage questions first

Do **not** start with:

```text
“你对 VPS 有什么需求？”
```

That often produces “要快、要稳、要便宜”, which does not define a trade-off.

Prefer one variable per question, 2–4 understandable choices, and briefly explain why it matters.

Use information already present in the conversation. Never ask the user to repeat a known ISP, location, budget, or use case.

For a normal personal HY2 relay, baseline technical assumptions can usually be inferred and then stated for confirmation rather than consuming early questions:

```text
Linux VPS
root / sudo
public IPv4 preferred
UDP required for HY2
reinstall / console recovery preferred
personal authenticated use, not a public open proxy
```

### 3.3 Four-question fast path

If almost nothing is known, begin with these four human-facing questions.

#### 1. Local carrier / ISP — highest leverage for mainland-China routing

> **你平时主要用哪家网络连这台 VPS？** 这个会决定我优先看哪一类线路。
>
> - 中国电信
> - 中国联通
> - 中国移动
> - 其他 / 境外网络

Use the answer only as a **shortlisting direction**:

```text
China Telecom
  focus first on CN2 / AS4809
  if a vendor claims CN2 GIA, verify the real route and peak-hour behavior

China Unicom
  focus first on AS9929 + AS10099 / CUP / China Unicom Premium

China Mobile
  focus first on CMIN2 / AS58807

Other / overseas
  choose according to that network's actual peering and tests
```

Do not say “China Telecom = must buy CN2 GIA”. A route label is not a performance guarantee.

If province/city is not already known and would materially change route evaluation, ask it as a follow-up rather than making it a universal first question.

#### 2. Main use case — determines the triangle weights

> **这台 VPS 主要拿来干什么？** 我会按用途决定线路、价格、配置哪个更重要。
>
> - AI / ChatGPT / Claude / Gemini 为主
> - 日常网页 + 视频 / 流媒体
> - 游戏 / 对延迟很敏感
> - 综合都要
> - 还要跑网站、Docker、数据库或其他服务

Translate internally:

```text
AI / chat
  -> route stability, loss, connection success, UDP > oversized CPU/RAM

web + streaming
  -> sustained throughput + peak-hour stability

gaming / latency-sensitive
  -> RTT + jitter + loss + UDP receive very high weight

mixed use
  -> balanced triangle

hosting additional services
  -> raise CPU/RAM/disk requirements
```

#### 3. Budget — use long-term effective price

> **你每个月大概愿意花多少钱？** 我会按长期续费价算，不拿首月促销价冒充长期价格。

Use the user's currency. For a mainland-China consumer, a simple optional range is:

```text
<= ¥30
¥30–60
¥60–100
> ¥100
```

Always distinguish first-purchase price, renewal price, recurring discount, one-time coupon, and mandatory IPv4/location/setup/tax fees.

#### 4. Region preference — optional

> **机房地区有偏好吗？** 没概念也没关系，我可以按你的运营商和用途推荐。
>
> - 日本
> - 香港
> - 韩国 / 新加坡
> - 没概念，听你推荐

Do not force a beginner to choose a region they do not understand.

### 3.4 Ask expectations in human language, then translate them into metrics

Users should not need to know `P95 jitter`, `MTR`, or target Mbps before asking for help.

Ask about experience, for example:

```text
你最不能接受哪种情况？
- AI 聊着聊着断掉 / 请求经常失败
- 视频老转圈
- 游戏延迟乱跳
- 下载太慢
- 偶尔晚高峰抖一下可以接受
```

Useful follow-ups only when they can change the recommendation:

- **Latency sensitivity:** 游戏 / 语音 / 视频会议，还是纯网页和 AI？
- **Good-enough throughput:** 需要稳定看 4K，还是 AI 对话和普通网页顺畅就够？
- **Testing tolerance:** 愿意测试两三台挑一台，还是想尽量一次选稳？
- **Price-risk preference:** 愿意等促销 / 年付换低价，还是宁可月付贵一点？
- **Availability tolerance:** 偶尔晚高峰抖一下能接受，还是主节点必须很稳？

The agent translates those answers into route weights and test thresholds. Do not ask the human to invent engineering thresholds they do not understand.

### 3.5 Build a procurement brief before vendor research

Before searching vendors, summarize the requirement in a small brief, for example:

```text
Use case: personal HY2 relay, mainly AI
Local network: China Telecom home broadband
Budget: <= ¥80/month
Triangle: route > price > config
Default score: route 50 / price 30 / config 20
Minimum config: 1C1G, public IPv4, UDP required
Traffic: >= 500 GB/month
Regions: Tokyo first, Seoul acceptable
Purchase preference: monthly first, refundable preferred
Experience goal: stable AI sessions; occasional small latency variation is acceptable
```

If a missing detail could materially reverse the recommendation, ask before searching. Otherwise state the assumption and proceed.

### 3.6 Explain route labels instead of blindly ranking them

For mainland-China users, use these as **reference labels only**:

```text
China Telecom
  ordinary: ChinaNet / 163 / commonly AS4134
  higher-quality candidate: CN2 / AS4809; marketing may say CN2 GIA

China Unicom
  ordinary: 169 / commonly AS4837
  higher-quality candidate: AS9929 + AS10099 / CUP / China Unicom Premium

China Mobile
  ordinary international: CMI / commonly AS58453
  higher-quality candidate: CMIN2 / AS58807
```

For Japan and other overseas segments:

```text
SoftBank / AS17676
IIJ / AS2497
NTT / AS2914
```

These usually describe an overseas backbone/transit segment. They are **not the same category** as CN2 / 9929 / CMIN2. One end-to-end path may contain both.

Never tell the user that a label alone proves quality. “CN2”, “9929”, “CMIN2”, “SoftBank”, “IIJ”, “NTT”, “three-network optimized”, “premium network”, “native IP”, and similar phrases are shortlist clues, not evidence.

### 3.7 Search and shortlist like a procurement assistant

Only after the user's need is sufficiently understood should current vendor inventory, prices, and promotions be researched.

Use fresh public information rather than memory when current inventory/pricing matters.

For each candidate collect:

1. provider and exact plan;
2. datacenter city / region;
3. actual checkout price;
4. renewal price;
5. IPv4, location, setup, tax, and mandatory fees;
6. CPU / RAM / disk;
7. port bandwidth and monthly traffic;
8. public IPv4 / NAT status;
9. UDP policy;
10. AUP / ToS compatibility with the intended personal use;
11. Test IP / Looking Glass;
12. reinstall / console / recovery capabilities;
13. refund / cancellation / IP replacement rules;
14. current discount type and whether it recurs.

Prefer a shortlist of roughly 5–10 candidates, then reduce to 2–3 after hard requirements and route tests.

### 3.8 Price and refund policy

Compare **effective long-term monthly cost**, not the largest promotional number:

```text
plan
+ IPv4
+ location surcharge
+ setup fee
+ taxes / mandatory add-ons
------------------------------
actual paid term
```

Explicitly distinguish:

- first-month discount;
- first-term / first-year discount;
- recurring discount;
- coupon code;
- anniversary / seasonal / Black Friday-style promotion;
- normal renewal price.

The key question is:

> **Does renewal keep the discount, or return to normal price?**

For an untested provider or route:

```text
monthly / short-term test first
      ↓
validate route + real instance
      ↓
then consider annual / long-term discount
```

Prefer a clearly refundable option when otherwise comparable. Read the current refund rules and exclusions; promotional plans, setup fees, IP fees, add-ons, or heavy traffic usage may be excluded.

### 3.9 Guide route testing; execute it yourself when possible

When a Test IP / Looking Glass exists, test from the network that will actually use the VPS.

If the AI has shell access on that local machine, **run the checks itself**. If it is chat-only and cannot originate traffic from the user's network, give the human the commands and ask for raw output.

Windows:

```powershell
ping TEST_IP -n 50
tracert -d TEST_IP
pathping TEST_IP
```

Linux/macOS:

```bash
ping -c 50 TEST_IP
mtr -rwzbc 50 TEST_IP
```

At minimum compare daytime and local peak hours such as `20:00–23:00`.

Evaluate:

- terminal packet loss;
- median / average / P95 latency where available;
- jitter / max spikes;
- route changes;
- repeated timeouts;
- sustained throughput;
- the user's real ISP/network.

Do not treat an intermediate traceroute hop that ignores/deprioritizes ICMP as automatic end-to-end loss.

Where possible inspect both directions because Internet routing can be asymmetric.

For HY2, do not infer UDP health from TCP/HTTPS success. On a purchased test instance validate the intended UDP port and, when useful, compare `UDP 443` with a high port such as `UDP 24443`.

### 3.10 Unified candidate scoring

For the default **daily HY2 / AI relay**, use exactly:

```text
route / stability  50%
price              30%
configuration      20%
```

Do not add a separate `operations/AUP` percentage for this default score. Those items are handled as hard gates / tie-breakers outside the triangle.

The detailed route, price, and configuration sub-scores must add up to the same `50 / 30 / 20` total used by `docs/vps-selection.md`.

For other workloads, weights may change. Examples:

```text
gaming              -> increase route / RTT / jitter weight
streaming            -> emphasize sustained throughput inside route score
app/database server  -> increase configuration weight
backup node          -> increase price weight
```

The final recommendation must explain:

```text
why candidate A ranks first
what candidate A sacrifices
why candidate B may suit a different priority
which triangle corner each candidate optimizes
which claims are marketing
which results are actually measured
```

The goal is not “find the biggest plan”. It is to find the best personal balance among route, price, and configuration.

### 3.11 Human purchase boundary

The AI should do the comparison, research, interpretation, and any executable testing it can do. The human should only handle steps that genuinely require human consent or access, such as final payment, MFA/CAPTCHA, accepting provider terms, or local actions the AI cannot access.

Do not ask the user to paste payment-card data, provider passwords, or other financial/account secrets into prompts, logs, Issues, or the repository.

After purchase, re-test the **real assigned VPS**. Provider Test IP performance does not prove every production instance is identical.

Only after the instance passes procurement acceptance should deployment continue to SSH bootstrap.

---

## 4. Human SSH bootstrap boundary

Before autonomous or semi-autonomous deployment, establish secure key-based access unless an equally secure path already exists.

Recommended flow:

```text
Human logs in once using provider password / console when necessary
        ↓
Generate SSH key pair locally if none exists
        ↓
Only the public key is installed on the VPS
        ↓
Verify key-based SSH login
        ↓
Local AI/Agent uses the already-working ssh / SSH agent / SSH config
```

If the AI has authorized local-shell access, it should generate/install/test the key itself where possible without exposing private-key content. If a provider password, MFA, or console interaction must be performed by the human, guide that step explicitly.

Rules:

1. SSH private keys remain on the user's local device.
2. Only the `.pub` key goes to `authorized_keys`.
3. Never ask the user to paste a root password or private key into chat, GitHub, Issues, logs, or prompts.
4. Prefer the user's existing `ssh`, SSH Agent, or `~/.ssh/config` over reading/exporting private keys.
5. Do not disable password login until key-based login is proven to work.
6. Preserve provider-console recovery where possible.
7. If secure SSH access cannot be established, stop and guide the human through the minimum required bootstrap.

Windows manual fallback example:

```powershell
ssh-keygen -t ed25519
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@SERVER_IP "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
ssh root@SERVER_IP
```

The final `ssh` must succeed before unattended server changes continue.

---

## 5. Resource contract

Distinguish **required for the selected profile** from optional enhancements.

### Required for HY2 baseline

- VPS / Linux host controlled by the user;
- root or sudo access;
- provider policy permitting intended personal VPN/proxy use;
- public server address;
- UDP reachability on selected HY2 port;
- compatible client;
- HY2 password/auth material;
- TLS material accepted by the HY2 client;
- normal VPS outbound Internet access;
- verified SSH key-based administration before AI-controlled deployment, unless an equally secure path already exists.

Resolve first:

```text
SERVER_IP_OR_HOSTNAME
SSH_ACCESS_METHOD
HY2_UDP_PORT
HY2_TLS_CERTIFICATE_STRATEGY
CLIENT_TYPE
```

### Additional resources for WARP

Only if WARP is selected:

```text
Cloudflare WARP Linux client / account state
local proxy mode support
chosen local proxy port (repo example: 127.0.0.1:40000)
```

Do not make WARP the host-wide default route in this project.

### Additional resources for fixed SOCKS5

Only if a fixed egress is selected:

```text
SOCKS_HOST
SOCKS_PORT
SOCKS_USERNAME (if required)
SOCKS_PASSWORD (if required)
```

The upstream must be trusted and legitimately usable by the user.

### Additional resources for REALITY

Only if REALITY backup inbound is selected:

```text
VLESS UUID
REALITY X25519 private/public key pair
REALITY short ID
serverName/target strategy
reachable TCP port
```

A domain is not inherently required for REALITY itself.

### Additional resources for Cloudflare Tunnel

Only if the emergency Tunnel entry is selected:

```text
Cloudflare account
appropriate domain / tunnel configuration
secret/token handling path
```

Do not require WARP, fixed SOCKS5, REALITY, Cloudflare Tunnel, a second VPS, residential IP, or IPv6 merely because examples exist.

---

## 6. Routing policy semantics

Repository example policy may use:

```text
ordinary traffic                 -> direct
OpenAI / ChatGPT / Codex         -> WARP
Gemini / Google AI               -> WARP
Claude / Anthropic               -> optional fixed SOCKS5
```

Treat this as a maintainer preference / example policy, not a universal service requirement.

Avoid unsupported claims such as:

- "this prevents bans";
- "this IP can never be blocked";
- "Claude requires residential IP";
- "WARP is a residential IP".

---

## 7. WARP architecture rule

Prefer **WARP Local Proxy / WarpProxy mode**:

```text
Linux default route -> VPS native network

Xray selected route
   -> 127.0.0.1:40000
   -> warp-svc
   -> Cloudflare WARP
```

Never make global WARP routing the baseline design.

Why:

- keeps SSH/system updates on native route;
- prevents fixed SOCKS upstream connections from accidentally traversing WARP;
- keeps Direct as a clean baseline;
- limits WARP failure impact to explicitly selected routes.

Official references:

- <https://developers.cloudflare.com/warp-client/get-started/linux/>
- <https://developers.cloudflare.com/warp-client/warp-modes/>

Cloudflare CLI syntax changes. Prefer current docs plus local `warp-cli --help` over historical commands.

For WARP health, test real requests through the local proxy. A live `warp-svc` process alone is not evidence of healthy egress.

Prefer a systemd timer for new/public watchdog deployments. Cron may be mentioned as a historical/simple alternative.

---

## 8. Fixed SOCKS5 boundary

SOCKS5 itself does not provide transport encryption.

When documenting a remote fixed SOCKS5:

- state that SOCKS itself is not an encrypted VPN;
- note HTTPS still protects HTTPS application payloads end-to-end;
- if stronger link confidentiality is required, use a controlled encrypted/private path or provider that supplies one.

Do not equate "fixed/residential IP" with "encrypted" or "safer transport".

For deliberately pinned destinations, prefer fail-closed behavior unless the user explicitly requests fallback.

Do not silently reroute fixed-egress traffic to Direct when the upstream fails.

---

## 9. Audited client reality

Current Windows audit:

```text
v2rayN 7.24.2
HY2 active       -> sing-box 1.13.14
REALITY profile  -> Xray core
TUN + Rule mode
```

v2rayN is a GUI/config manager, not one specific core.

Observed model:

```text
GUI metadata + global preferences
              ↓
        v2rayN generates
              ↓
core-specific runtime config
```

Keep sing-box, Xray, and Mihomo field names separate.

---

## 10. Xray source of truth

Prefer current official Xray docs over copied blog configs or remembered production aliases:

- Hysteria inbound: <https://xtls.github.io/config/inbounds/hysteria.html>
- Hysteria transport: <https://xtls.github.io/config/transports/hysteria.html>
- VLESS / Vision: <https://xtls.github.io/config/inbounds/vless.html>
- REALITY: <https://xtls.github.io/config/transports/reality.html>
- RAW: <https://xtls.github.io/config/transports/raw.html>
- SOCKS outbound: <https://xtls.github.io/config/outbounds/socks.html>
- Installer: <https://github.com/XTLS/Xray-install>

Current assumptions:

- current Xray supports Hysteria2;
- Hysteria version is 2;
- HY2 is the primary entry;
- REALITY/Vision is optional backup;
- current docs may use fields that differ from historical production aliases;
- REALITY current server-side docs use `target`; historical configs may show `dest`;
- current SOCKS outbound docs use flat address/port/user/pass fields; old configs may use older shapes.

If upstream schema changes, update every affected example/doc together.

---

## 11. Repository file map

```text
README.md                              Chinese human-facing architecture and profile guidance
AGENTS.md                              AI procurement/deployment/maintenance contract
examples/xray-server.example.jsonc     server-side Xray schema example
examples/v2rayn-hysteria2.example.md   audited v2rayN / sing-box HY2 client example
examples/v2rayn-reality-vision.example.md
                                       v2rayN / Xray REALITY client example
docs/vps-selection.md                  pre-deployment VPS procurement, route and UDP testing guide
docs/warp-outbound.md                  WARP egress behavior and validation
docs/static-socks.md                   fixed SOCKS5 egress behavior
```

Synchronization rules:

- VPS procurement/scoring/testing guidance change -> `docs/vps-selection.md` + relevant README entry points + AGENTS procurement contract.
- The default daily HY2/AI triangle score must remain `route 50 / price 30 / config 20` in both AGENTS and `docs/vps-selection.md`.
- Xray schema change -> server example + README references + affected docs + AGENTS.
- HY2 client field change -> HY2 client example + relevant README notes.
- REALITY client field change -> REALITY example + relevant README notes.
- WARP policy/CLI change -> WARP doc + server example if needed + AGENTS.
- SOCKS schema/policy change -> static SOCKS doc + server example + AGENTS if safety boundary changes.

Never leave contradictory assumptions across files.

---

## 12. Production host is not the template

Production evolved through experiments and may contain legacy paths/backups/compatibility fields.

Public examples should follow:

```text
working production behavior
        ↓
read-only audit
        ↓
current upstream documentation
        ↓
remove secrets + legacy/dead config
        ↓
clean public example
```

Prefer clean layouts such as:

```text
/usr/local/bin/xray
/usr/local/etc/xray/config.json
systemd-managed services
explicit firewall rules
minimal configs
```

---

## 13. Secret handling

Never commit or paste live secrets.

Placeholders only:

```text
YOUR_SERVER_IP
YOUR_UUID
YOUR_REALITY_PRIVATE_KEY
YOUR_REALITY_PUBLIC_KEY
YOUR_SHORT_ID
YOUR_HY2_PASSWORD
YOUR_DOMAIN
YOUR_SERVER_NAME
YOUR_SOCKS_HOST
YOUR_SOCKS_USERNAME
YOUR_SOCKS_PASSWORD
```

Never expose:

- SSH private keys;
- root/VPS passwords;
- TLS private keys;
- Cloudflare tokens;
- production proxy credentials;
- subscription URLs;
- full production configs containing secrets.

---

## 14. Firewall / listeners

Open only selected-feature ports.

Example full profile:

```text
TCP 22      SSH
TCP 443     REALITY
UDP 24443   HY2
```

An HY2 + WARP + fixed-SOCKS Profile D does not need REALITY TCP 443 unless REALITY is actually enabled.

Preserve SSH access before firewall changes. Remember provider-side security groups may exist independently of host firewall.

---

## 15. Testing philosophy

Change one variable at a time.

Before buying a VPS, follow [`docs/vps-selection.md`](./docs/vps-selection.md): do not infer route quality, UDP health, or peak-hour performance from marketing specs alone.

Prefer checking:

- connection success rate;
- latency / variance;
- timeouts;
- peak-hour behavior;
- sustained transfer stability;
- long-lived connection behavior;
- final egress IP for each route.

Do not call a path healthy from one speed test.

### AI deployment self-check

Before saying deployment is complete, verify the features actually selected:

1. SSH key-based administration still works.
2. Server config validation passes.
3. Expected listeners are present and unnecessary example ports are closed.
4. HY2 client/server credentials match.
5. Direct egress works.
6. If WARP is enabled, a request through the local proxy reaches the intended WARP egress.
7. If fixed SOCKS5 is enabled, selected traffic reaches that fixed egress and does not silently fall back.
8. If REALITY is enabled, client/server UUID/key/short-ID/serverName parameters match.
9. Firewall/provider rules permit only the intended management/proxy ports.
10. No real secrets were written to repository, logs, Issues, or chat output.

Do not claim end-to-end client success unless the client path was actually tested.

---

## 16. Documentation style

`README.md` is for Chinese-speaking humans: explain the practical recommendation first.

`AGENTS.md` is for AI maintainers/deployers: preserve procurement guidance, minimal-human-work execution policy, architecture, profile semantics, SSH bootstrap boundary, resource prerequisites, safety boundaries, source-of-truth links, and secret hygiene.

The repository must remain understandable without private production context.