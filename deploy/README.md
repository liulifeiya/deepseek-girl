# deploy — Windows 部署

目标机：**Windows Server 2022/2025 或 Windows 10+**，PowerShell 5.1 即可。
Linux 部署（`install.sh` + systemd）已移除；历史版本可在 git 记录里找到。

## 一键部署

```powershell
# 0) 依赖（一次性）
#    Node 22+（含 corepack）、Python 3.12、pnpm、dsh
corepack enable --install-directory $env:APPDATA\npm pnpm
pnpm add -g @deepseek-ai/dsh

# 1) 体检
.\deploy\preflight.ps1

# 2) 干跑看计划
.\deploy\install.ps1 -DryRun

# 3) 真装
.\deploy\install.ps1
```

`install.ps1` 的参数（括号内为默认值）：`-BotQQ (2836148023)`、`-AdminQQ (2812108776)`、
`-OneBotToken (随机生成)`、`-DshPort (3081)`、`-NapcatWsPort (3001)`、
`-SkipTasks`、`-SkipStart`。

它按 8 个步骤执行，全部幂等，可反复跑：

| 步骤 | 内容 |
|---|---|
| `10-base` | 依赖检查：Node ≥ 22、pnpm、Python 3.12、dsh |
| `20-dsh` | 在 `%USERPROFILE%\.dsh-qq\profiles\qq` 建 profile 并 `pnpm install` 6 个插件 |
| `30-plugins` | 渲染 `cordis.patch.yml`、生成 OneBot token、打 `dsh-onebot-qq` 本地补丁 |
| `40-botfiles` | 铺 `qq-dsh-bot\`（runtime/scripts/patches/personas）、人设卡导入、AGENTS.md |
| `50-tts` | `tts-venv` + pillow/aiohttp/tabulate，TTS/表情包脚本 |
| `60-agent` | 常挂智能体目录与代码 |
| `70-napcat` | 生成 `Napcat\config\`（OneBot WS、WebUI、协议配置） |
| `80-services` | 注册 `DshBot-*` 计划任务 |

## 首次登录

NapCat 不能自动登录，第一次要扫码：

```powershell
.\deploy\show-qr.ps1          # 等下一次二维码刷新并导出到 workspace
```

也可以用 `.\deploy\start-napcat.ps1` 启动后直接看弹出的 QQ 窗口。

## 目录约定

```
%USERPROFILE%\
├─ .dsh-qq\                     # 机器人专用 DSH_HOME（与桌面 GUI 的 .dsh 隔离）
│  ├─ profiles\qq\              # 插件 + cordis.patch.yml
│  ├─ sessions\  storages\  media\  proactive\
│  └─ dsh-web.env               # DEEPSEEK_API_KEY
├─ qq-dsh-bot\                  # 运行脚本、补丁、人设、日志、token
├─ agent\                       # 常挂智能体
├─ tts-venv\   tts-out\         # Python 环境与产物
├─ Napcat\                      # NapCat Shell（config\ 下是 OneBot 配置）
└─ AGENTS.md                    # 行为规则（workspacePath 根）
```

## 脚本清单

| 文件 | 用途 |
|---|---|
| `install.ps1` / `preflight.ps1` | 部署主入口 / 体检 |
| `env.ps1` | 所有脚本共用的环境变量 |
| `start-dsh.ps1` | 启动机器人后端（profile `qq`，3081） |
| `start-napcat.ps1` | 启动 QQ + NapCat 注入 |
| `start-workers.ps1` | guard / keepalive / watchdog |
| `start-agent.ps1` | 常挂智能体 worker |
| `restart-dsh.ps1` / `restart-napcat.cmd` | 重启后端 / 重启 NapCat |
| `show-qr.ps1` | 等刷新并导出登录二维码 |
| `probe-onebot.mjs` | 查登录号、在线状态、NapCat 版本 |
| `render-napcat-config.py` | 生成 NapCat 配置 |
| `install-tasks.ps1` | 注册 10 个计划任务 |
| `run-monthly.ps1` / `run-proactive.ps1` | 月度记忆整理 / 主动问候 |
| `restart-workers.ps1` | 只重启 guard/keepalive/watchdog（避免误杀调用方） |
| `selftest.ps1` | 部署自检：模块行为 + 接口 + headless shell |

## 本地补丁（`patches/`）

`pnpm install` 会还原 `node_modules`，所以插件补丁必须可重放。`install.ps1` 会自动跑：

| 脚本 | 作用 |
|---|---|
| `apply-onebot-patches.py` | dsh-onebot-qq：引用回复 / 分段 / 群聊插话 / @ 上下文 / 作息 / 人设锁定 / 语音模型路径 / 图片入库 / `/persona` 端口 |
| `patch-archive-retention.py` | archive-retention v1：会话文件名兼容、dryRun、清单含失败、cron 校验、状态持久化、跨进程锁 |
| `patch-archive-retention-2.py` | archive-retention v2：回收站（`_trash/<时间戳>`，默认 72h 后物理清）、`maxTotalBytes` 容量上限、`archive-list.json` 补充归档名单 |

### archive-retention 配置（插件页或 cordis.patch.yml）

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 总开关 |
| `dryRun` | `false` | 只写清单、不删 |
| `retentionValue` / `retentionUnit` | `7` / `days` | 归档保留期 |
| `trashRetentionHours` | `72` | 回收站保留小时数，到期物理删除 |
| `maxTotalBytes` | `0` | 归档总量上限（0=关闭），超限按最旧优先清 |
| `extraArchivedIdsFile` | `archive-list.json` | 机器人本地归档名单（用 `deploy\archive-session.ps1` 维护） |
| `sweepCron` | `0 4 * * *` | 清扫节奏；非法表达式会告警并回落默认 |

`deploy\archive-session.ps1 add|remove|list <sessionId>` 维护 `.dsh-qq\archive-list.json`。

## 计划任务

`DshBot-DSH`、`DshBot-Workers`、`DshBot-Agent`、`DshBot-NapCat`（登录触发）、
`DshBot-DailyRestart`（每日 05:00）、`DshBot-Monthly`（每 4 周）、
`DshBot-Proactive-1030/1530/2030`、`DshBot-PersonaBind`（每分钟补绑人设）、
`DshBot-BootCheck`（SYSTEM / 开机，写 `qq-dsh-bot\boot.log`）。

## 重启自启（重要）

QQ/NapCat 是 GUI 程序，**必须有交互式登录会话**才能跑；只把任务改成开机启动不够。
完整自启需要两步：

1. **开启自动登录**（自己操作，不经过密码）：
   `Win+R` → `netplwiz` → 选中 `Administrator` → 取消「要使用本计算机，用户必须输入用户名和密码」→ 应用 → 输入两次密码 → 确定。
   （服务器版若看不到这个勾选项，改用 `control userpasswords2`，或 Sysinternals Autologon。）
2. **验证**：`.\deploy\verify-autostart.ps1`
   检查 `AutoAdminLogon=1`、任务触发器、以及 `boot.log` 里最近一次开机是否记录到后端/QQ。

注意：
- 自动登录意味着控制台/带外管理（VNC）能直接进入桌面，云服务器请评估这一点。
- 三个启动脚本（DSH / NapCat / Workers）都是幂等的：自动登录后你再 RDP 登录，不会重复起进程。
- 想验证真正的重启链路，重启后回来看 `qq-dsh-bot\boot.log` 与 `verify-autostart.ps1` 的输出。

## 已知差异

- 没有 systemd / journalctl：日志是 `qq-dsh-bot\*.log`，`Get-Content -Tail -Wait` 跟。
- 没有 `chmod`：密钥文件用 `icacls` 限制。
- 会话→人设绑定是进程内状态，重启会丢，靠 `DshBot-PersonaBind` 每分钟补。
- `patch-napcat-quicklogin.py` 针对 Linux 布局；Windows 由 `start-napcat.ps1` 传 `-q`。
