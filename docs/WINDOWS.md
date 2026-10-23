# Windows 兼容性改造记录

本仓库最初按 Ubuntu + systemd 编写。这份文档记录在 Windows 上运行时，
哪些部分**已经换成 Windows 实现**、哪些**保持 Linux 不动**、以及为什么。

## 一、已改造（运行时真正会用到的）

| 文件 | 原来的 Linux 依赖 | 现在的实现 |
|---|---|---|
| `patches/group-wake.js` | `/home/ubuntu/.dsh-user/group-wake.json`、`group-user-allow.json` | 由 `BOT_HOME` + `DSH_HOME` 推导，支持 env 覆盖 |
| `patches/persona-lock.js` | `/home/ubuntu/.dsh-user/storages/dsh-persona-dafeiyu/personas.json` | 同上，`PERSONA_STORE` 可覆盖 |
| `patches/sleep-window.js` | `/home/ubuntu/.dsh-user/sleep-window.json` | 同上，`SLEEP_WINDOW_CONFIG` 可覆盖 |
| `patches/bind-private-persona.sh` | bash + `127.0.0.1:3080` + Linux 会话目录 | 新增 `bind-private-persona.ps1`：3081 + `DSH_HOME\sessions` |
| `runtime/guard.mjs` | `systemctl --user restart napcat.service` | `NAPCAT_RESTART_CMD` → `restart-napcat.cmd`；二维码路径可配 |
| `runtime/qr-term.py` | Linux NapCat 缓存路径 | 按平台自动判断，支持 `NAPCAT_QR_PNG` |
| `tts/mimo-tts.py` | `/home/ubuntu/tts-out` | `BOT_HOME` / `TTS_OUT_DIR`，目录自动创建 |
| `tts/mureka-music.py` | 同上 | 同上 |
| `tts/meme.py` | `/home/ubuntu/tts-out` + Noto CJK 字体 | 同上 + Windows 字体回退（msyhbd/msyh/simhei/simsun） |
| `tts/draw2.py` | 同上 | 同上 |
| `scripts/img-prep.py` | `~/qq-dsh-bot/image-lib/_prep` | `BOT_HOME` 推导 |
| `scripts/group-image-ingest.py` | `~/qq-dsh-bot/image-lib` | `BOT_HOME` 推导 |
| `agent/worker.py` | `/home/ubuntu/...`、`:` 分隔 PATH | 家目录推导 + `os.pathsep` + Windows PATH |
| `agent/project.py` | `bash hooks/on-notify.sh` | 依次找 `.ps1` / `.cmd` / `.sh` |
| `config/cordis.patch.yml` | `workspacePath: /home/ubuntu` | `C:\Users\Administrator` |
| `config/AGENTS.md` | `~/tts-out`、`/home/ubuntu/.dsh-user/media`、`python3` | Windows 绝对路径、`python` |
| `deploy/templates/systemd/*` | systemd 单元 | `deploy/windows/install-tasks.ps1` 注册 9 个计划任务 |
| `deploy/steps/70-napcat.sh` | Linux NapCat rootless 安装 | 官方 QQ NT + `NapCat.Shell.zip`（sha256 校验） |

新增的 Windows 专用文件：

- `deploy/windows/`：启动、保活、任务注册、二维码导出、OneBot 探测脚本
- `patches/bind-private-persona.ps1`：会话 ↔ 人设绑定

## 二、保持 Linux 原样（Windows 不调用）

| 路径 | 原因 |
|---|---|
| `deploy/install.sh`、`deploy/lib.sh`、`deploy/steps/*.sh` | apt + systemd 的一键装机；Windows 用 `deploy/windows/` |
| `deploy/preflight.sh`、`deploy/migrate-*.sh` | 依赖 systemctl/tar 流程 |
| `deploy/vendor/napcat-installer.sh` | 拉的是 Linux QQ 包 |
| `deploy/templates/systemd/` | 模板保留给 Linux 机器 |
| `patches/patch-napcat-quicklogin.py` | 针对 Linux `napcat.mjs`；Windows 用启动参数 `-q` 达到同样效果 |
| `docs/MIGRATION.md` | 讲的是 Ubuntu 迁移流程 |

## 三、Windows 上的路径约定

```
BOT_HOME   = C:\Users\Administrator
DSH_HOME   = C:\Users\Administrator\.dsh-qq          # 与现有 GUI 的 .dsh 隔离
PROFILE    = %DSH_HOME%\profiles\qq
运行目录   = %BOT_HOME%\qq-dsh-bot
NapCat     = %BOT_HOME%\Napcat
Agent      = %BOT_HOME%\agent
TTS        = %BOT_HOME%\tts-out，venv 在 %BOT_HOME%\tts-venv
```

## 四、遗留差异

1. **服务管理**：Windows 用“计划任务 + 登录触发”，不是常驻 service；
   机器重启后需要用户登录（或把任务改成 `SYSTEM` 账户并授权目录）。
2. **无 journalctl**：日志是 `qq-dsh-bot\*.log`，用 `Get-Content -Tail -Wait` 跟。
3. **无 `chmod`**：改用 `icacls` 限制 `dsh-web.env`、`onebot-token.txt` 的读权限。
4. **NapCat 布局不同**：Windows 是独立 `Napcat\` 目录 + `NapCatWinBootMain.exe`
   注入 QQ；配置在 `Napcat\config\`，不在 QQ 安装目录里。
