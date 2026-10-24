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
`DshBot-Web`（登录触发，DSH Web GUI 3080）、
`DshBot-DailyRestart`（每日 05:00）、`DshBot-Monthly`（每 4 周）、
`DshBot-Proactive-1030/1530/2030`、`DshBot-PersonaBind`（每分钟补绑人设）、
`DshBot-Curiosity`（每日 11:00 / 17:00 / 22:00，自主查资料写知识库）、
`DshBot-BootCheck`（SYSTEM / 开机，写 `qq-dsh-bot\boot.log`）。

## 自主好奇心知识库

机器人会按计划自己去网上找资料，写进 `%USERPROFILE%\knowledge\`：

| 文件 | 作用 |
|---|---|
| `index.jsonl` | 每条来源一行（url / title / tags / summary / note / sha / 时间） |
| `notes/*.md` | 每篇笔记（结论 + 要点 + 待验证 + 来源） |
| `INBOX.md` | 最近 12 条摘要，聊天时可直接引用 |
| `topics.json` | 兴趣清单与覆盖统计（决定下次查什么） |
| `curiosity.log` | 每轮运行日志 |

**兴趣范围只有「电竞」和「娱乐」**（其他领域不自动补，管理员想知道会直接问）。
清单见 `config/knowledge-topics.json`：

- esports：电竞赛事、电竞选手与战队、游戏版本与战术
- ent：影视与综艺、明星与娱乐八卦、音乐与声音、二次元与游戏、网络热梗

选题规则：两类交替、优先时效性（本周赛事/版本更新/新剧新综艺/正在发酵的热搜），
其余按覆盖度最少来；八卦只写多家媒体报道过的，不写营销号单方面爆料。
政治、宗教、民族、地域黑，以及未成年人私生活，一律跳过。

运行链路：任务 `DshBot-Curiosity` → `run-curiosity.ps1` → `dsh headless`（headless profile）
→ `web_search` + `web_fetch` → `kb.py add`（按 URL 去重）→ 更新 INBOX。

维护：

```powershell
$py = 'C:\Program Files\Python312\python.exe'
& $py "$env:USERPROFILE\qq-dsh-bot\kb.py" stats      # 条数 / 体积 / 最后一条
& $py "$env:USERPROFILE\qq-dsh-bot\kb.py" topics     # 兴趣与覆盖度
& $py "$env:USERPROFILE\qq-dsh-bot\kb.py" inbox      # 最近 12 条
& $py "$env:USERPROFILE\qq-dsh-bot\kb.py" search 关键词
& $py "$env:USERPROFILE\qq-dsh-bot\kb.py" rm --title-contains 关键词   # 删除（含笔记文件）
& $py "$env:USERPROFILE\qq-dsh-bot\kb.py" rm --url <URL>
```

### 表情包库（`%USERPROFILE%\stickers`）

网络上看到的图可以存进表情包库，聊天时直接发：

```powershell
$py = 'C:\Program Files\Python312\python.exe'
& $py "$env:USERPROFILE\qq-dsh-bot\meme-lib.py" add --url "<图片URL>" --tags "猫,无语" --source "<来源页>"
& $py "$env:USERPROFILE\qq-dsh-bot\meme-lib.py" from-page --url "<页面URL>" --limit 3 --tags "梗图"
& $py "$env:USERPROFILE\qq-dsh-bot\meme-lib.py" list / search 猫 / stats
```

- 校验图片头（png/jpg/gif/webp）、单张 ≤8MB、按 sha256 去重（重复输出 `DUP`）；
- 元数据写 `stickers\index.jsonl`（file/hash/url/page/tags/bytes/at）；
- 下载走系统 `curl.exe`：Windows 的 Python 常缺 CA 根证书，urllib 直连会 `CERTIFICATE_VERIFY_FAILED`；
- `from-page` 只解析 HTML 里的 `<img>`/`og:image`，对 JS 渲染的站点无效；外网站点受网络可达性限制。

### 表情包补习队列

群里发来她看不懂的表情包时，按 `AGENTS.md` 的规则：先自然回一句（不装懂、不编角色名），
再用一条命令记进队列：

```powershell
& $py "$env:USERPROFILE\qq-dsh-bot\kb-queue.py" add --hash <sha前16> --image "<图片路径>" --context "群号 配文"
```

后台任务 `DshBot-LearnQueue`（每 20 分钟）取 pending 项：`read_image` 看图 → `web_search`
查角色/梗 → 写笔记 → `kb.py add` → 自动同步仓库。每轮最多 2 条；队列为空时秒退，
不启动 dsh。队列文件 `knowledge\_queue.jsonl` **不参与仓库同步**。

```powershell
.\deploy\run-learn-queue.ps1 -Max 1          # 手动跑一条
& $py "$env:USERPROFILE\qq-dsh-bot\kb-queue.py" list --all
```

约束（写在 `curiosity-prompt.txt`）: 最多抓 3 页、10 分钟内、不碰内网地址、不存个人信息、主题不离开兴趣范围。

### 同步到独立仓库

知识库会同步到 **[liulifeiya/deepseek-girl-knowledge](https://github.com/liulifeiya/deepseek-girl-knowledge)**（私有）。
每轮好奇心结束自动调用 `sync-knowledge.ps1`；也可以手动：

```powershell
.\deploy\sync-knowledge.ps1              # 增量同步（按内容哈希，无变化时不提交）
.\deploy\sync-knowledge.ps1 -DryRun      # 只看差异
.\deploy\sync-knowledge.ps1 -Message "knowledge: 手动补一条"
```

Token 存在 `%USERPROFILE%\.dsh-qq\kb-sync.env`（`KB_SYNC_TOKEN=`，已用 `icacls` 限权）。
建议换成**只对该仓库有 Contents: Read/Write** 的细粒度令牌，不要长期使用全权限经典令牌。

同步范围：`index.jsonl`、`notes/*.md`、`INBOX.md`、`topics.json`、`README.md`；
跳过 `curiosity.log`、`_draft.md`、隐藏文件与临时文件。

## 重启自启（重要）

QQ/NapCat 是 GUI 程序，**必须有交互式登录会话**才能跑；只把任务改成开机启动不够。
完整自启需要两步：

1. **开启自动登录**（自己操作，不经过密码）：
   `Win+R` → `netplwiz` → 选中 `Administrator` → 取消「要使用本计算机，用户必须输入用户名和密码」→ 应用 → 输入两次密码 → 确定。
   **Windows Server 2025 上这个勾选框常常被隐藏**（实测如此），改用 Sysinternals Autologon：
   ```powershell
   # 下载并校验签名
   curl.exe -sSL -o "$env:TEMP\AutoLogon.zip" https://download.sysinternals.com/files/AutoLogon.zip
   Expand-Archive "$env:TEMP\AutoLogon.zip" "$env:USERPROFILE\Downloads\autologon" -Force
   Get-AuthenticodeSignature "$env:USERPROFILE\Downloads\autologon\Autologon64.exe"   # 应为 Valid / Microsoft
   # 运行后填 Administrator + 本机名 + 密码，点 Enable
   ```
   Autologon 把凭据加密存进 LSA（注册表不会出现明文 `DefaultPassword`）。
2. **验证**：`.\deploy\verify-autostart.ps1`
   检查 `AutoAdminLogon=1`、任务触发器、以及 `boot.log` 里最近一次开机是否记录到后端/QQ。

注意：
- 自动登录意味着控制台/带外管理（VNC）能直接进入桌面，云服务器请评估这一点。
- 三个启动脚本（DSH / NapCat / Workers）都是幂等的：自动登录后你再 RDP 登录，不会重复起进程。
- 本仓库现在也会自启 DSH Web GUI（3080）：任务 `DshBot-Web`，日志在 `.dsh\logs\dsh-web-console.log`。
- 想验证真正的重启链路，重启后回来看 `qq-dsh-bot\boot.log` 与 `verify-autostart.ps1` 的输出。

## 已知差异

- 没有 systemd / journalctl：日志是 `qq-dsh-bot\*.log`，`Get-Content -Tail -Wait` 跟。
- 没有 `chmod`：密钥文件用 `icacls` 限制。
- 会话→人设绑定是进程内状态，重启会丢，靠 `DshBot-PersonaBind` 每分钟补。
- `patch-napcat-quicklogin.py` 针对 Linux 布局；Windows 由 `start-napcat.ps1` 传 `-q`。
