# Windows 部署（PowerShell + 计划任务）

仓库原本只有 Ubuntu 部署（`deploy/install.sh` + systemd）。这套目录是等价的
Windows 实现，目标机是 **Windows Server 2022/2025 / Windows 10+**，装法与 Linux 一致：
先装依赖，再把配置和脚本铺好，最后注册开机自启。

## 与 Linux 部署的对应关系

| Linux | Windows |
|---|---|
| `deploy/install.sh` | 按本文“安装顺序”手工执行（脚本都在本目录） |
| `systemd/*.service` | `install-tasks.ps1` 注册的 9 个计划任务 |
| `deploy/steps/70-napcat.sh` | 官方 QQ NT 安装包 + `NapCat.Shell.zip`（见下） |
| `runtime/guard.mjs` 里 `systemctl restart napcat` | `restart-napcat.cmd`（由 `NAPCAT_RESTART_CMD` 注入） |
| `patches/bind-private-persona.sh` | `patches/bind-private-persona.ps1` |
| `~/tts-venv`、`~/tts-out` | `%USERPROFILE%\tts-venv`、`%USERPROFILE%\tts-out` |

## 目录约定

```
%USERPROFILE%\
├─ .dsh-qq\                     # 机器人专用 DSH_HOME（不碰现有 GUI 的 .dsh）
│  ├─ profiles\qq\              # profile：插件 + cordis.patch.yml
│  ├─ sessions\                 # dsh 会话
│  ├─ dsh-web.env               # DEEPSEEK_API_KEY
│  ├─ group-wake.json
│  └─ sleep-window.json
├─ qq-dsh-bot\                  # 运行脚本、补丁、人设、日志
├─ agent\                       # 常挂智能体
├─ tts-venv\                    # Pillow/aiohttp/tabulate
├─ tts-out\                     # TTS/表情包脚本与产物
├─ Napcat\                      # NapCat Shell（config/ 下是 OneBot 配置）
└─ AGENTS.md                    # 行为规则（workspacePath 根）
```

## 安装顺序

1. **依赖**
   - Node 24（`node -v`）、`corepack enable --install-directory %APPDATA%\npm pnpm`
   - Python 3.12（`python.org` 安装包，勾 Add to PATH）
   - `pnpm install --frozen-lockfile` 于 `%USERPROFILE%\.dsh-qq\profiles\qq`
     （pnpm 12 需要 `pnpm-workspace.yaml` 里的 `allowBuilds`）
2. **插件补丁**：`python patches\apply-onebot-patches.py <profile>\node_modules\dsh-onebot-qq\lib`
3. **QQ + NapCat**
   - QQ NT 安装包：`https://qqdl.gtimg.cn/qqfile/QQNT/9.9.33/release/497e2f1f/QQ_9.9.33_260813_x64_01.exe`
   - NapCat：`NapCat.Shell.zip`（用官方 release 的 sha256 校验），解压到 `%USERPROFILE%\Napcat`
   - 配置：`python render-napcat-config.py`（写 `Napcat\config\`）
   - 启动：`start-napcat.ps1`，首次用 `show-qr.ps1` 取二维码扫码
4. **启动**：`start-dsh.ps1`（3081 端口）、`start-workers.ps1`（guard/keepalive/watchdog）、`start-agent.ps1`
5. **开机自启**：`powershell -ExecutionPolicy Bypass -File install-tasks.ps1`

## 常用命令

```powershell
.\start-napcat.ps1          # 启动 QQ + NapCat（要管理员）
.\start-dsh.ps1             # 机器人后端（3081）
.\start-workers.ps1         # 保活/看门狗
.\restart-napcat.ps1        # 实际文件是 restart-napcat.cmd
.\show-qr.ps1               # 等下一次二维码刷新并导出
node .\probe-onebot.mjs     # 查登录号/在线状态/NapCat 版本
```

## 已知差异

- `deploy/*.sh`（install/migrate/preflight）保持 Linux 版不动，Windows 用本目录脚本。
- `patch-napcat-quicklogin.py` 针对 Linux 的 `napcat.mjs` 布局；Windows 版由
  `start-napcat.ps1` 直接给 QQ 传 `-q <QQ号>`，首次扫码后通常可直接快速登录。
- 日志走文件（`qq-dsh-bot\*.log`），没有 journalctl；用 `Get-Content -Tail -Wait` 看。
