# Windows 适配记录

仓库原来按 Ubuntu + systemd 编写，现在**只保留 Windows 部署**。这份文档记录改了什么、
为什么，以及还有哪些差异。

## 一、仓库结构变化

以下 Linux 专用文件已删除（需要时从 git 历史取回）：

| 已删除 | 原用途 |
|---|---|
| `deploy/install.sh`、`deploy/lib.sh`、`deploy/preflight.sh`、`deploy/deploy.conf.example` | apt + systemd 一键装机 |
| `deploy/steps/*.sh`（8 个） | 分步安装 |
| `deploy/templates/systemd/*`、`deploy/templates/logrotate-napcat.conf.tpl` | systemd 单元与日志轮转 |
| `deploy/vendor/napcat-installer.sh` | Linux NapCat rootless 安装器 |
| `deploy/migrate-export.sh`、`deploy/migrate-import.sh` | 迁移打包/还原 |
| `patches/bind-private-persona.sh` | 会话↔人设绑定（bash） |
| `docs/MIGRATION.md` | Ubuntu 迁移手册 |

替代品：

| 新文件 | 用途 |
|---|---|
| `deploy/install.ps1` | 一键部署（8 步，幂等，支持 `-DryRun`） |
| `deploy/preflight.ps1` | 装机前体检 |
| `deploy/README.md` | Windows 部署说明 |
| `patches/bind-private-persona.ps1` | 会话↔人设绑定（PowerShell） |
| `scripts/import-personas.py` | 把人设卡导入插件 store |

`deploy/` 目录现在就是 Windows 部署目录（不再有 `deploy/windows/` 子目录）。

## 二、运行时脚本改造

| 文件 | 原来的 Linux 依赖 | 现在 |
|---|---|---|
| `patches/group-wake.js` | `/home/ubuntu/.dsh-user/...` | `BOT_HOME`/`DSH_HOME` 推导 |
| `patches/persona-lock.js` | 硬编码 personas.json 路径 | 同上，`PERSONA_STORE` 可覆盖 |
| `patches/sleep-window.js` | 硬编码 sleep-window.json | 同上 |
| `runtime/guard.mjs` | `systemctl restart napcat` | `NAPCAT_RESTART_CMD` → `restart-napcat.cmd` |
| `runtime/keepalive.mjs`、`watchdog.mjs` | `'/home/ubuntu'` 默认 | `USERPROFILE`/`HOME` 推导 |
| `runtime/qr-term.py` | Linux NapCat 缓存路径 | 平台自动判断 + `NAPCAT_QR_PNG` |
| `tts/*.py` | `/home/ubuntu/tts-out`、Noto 字体 | `BOT_HOME`/`TTS_OUT_DIR` + Windows 字体回退 |
| `scripts/img-prep.py`、`group-image-ingest.py` | `~/qq-dsh-bot/...` | `BOT_HOME` 推导 |
| `agent/worker.py`、`agent/project.py` | `/home/ubuntu/...`、`bash hook` | 家目录推导、`.ps1`/`.cmd` hook |
| `agent/bin/qr.py` | 硬编码二维码路径 | 平台判断 + `NAPCAT_QR_PNG` |
| `config/cordis.patch.yml` | `workspacePath: /home/ubuntu` | `C:\Users\Administrator` |
| `config/AGENTS.md` | `~/tts-out`、`python3` | Windows 绝对路径、`python` |

## 三、插件审计结果

profile `qq` 装了 6 个插件：`dsh-onebot-qq 0.9.3`、`dsh-persona-dafeiyu 0.4.1`、
`dsh-proactive 0.3.1`、`dsh-openwolf 0.10.2`、`dsh-cron 0.1.0`、
`@momojie-s/dsh-archive-retention 0.3.0`。

| 插件 | 结论 | 处理 |
|---|---|---|
| dsh-onebot-qq | 唯一 Linux 残留是 `stt.js` 的 whisper 模型路径 | 补丁加 `WHISPER_CPP_MODELS` 与 Windows 常见目录 |
| dsh-persona-dafeiyu | 功能正常；但仓库自带人设卡**没有导入**，只有 3 个内置人设 | `scripts/import-personas.py` 导入 3 张卡 |
| dsh-persona-dafeiyu | 会话→人设绑定是**进程内状态**，重启即丢 | 新增每分钟计划任务 `DshBot-PersonaBind` 兜底 |
| dsh-proactive | 正常；数据目录 `.dsh-qq\proactive`，安静时段 23:00–08:00 | 无需改动 |
| dsh-openwolf | 会给 AGENTS.md 注入 20KB 解剖表（含 QQ 表情包路径），每轮白烧 token | 配置 `injectAgentsMd: false` + ignore 列表 |
| dsh-cron | 纯解析库，peer 依赖由 dsh 提供 | 无需改动 |
| dsh-archive-retention | 会话文件名写死 `session.jsonl.zstd`（实际 `session.v4.jsonl.zstd`），孤儿清理失效；无 dryRun；失败不落盘；非法 cron 静默；重启丢 lastSweepAt；无跨进程锁；删除不可恢复；无容量上限；GUI 归档名单在机器人 profile 里空转 | v1 修前 6 项；v2 加回收站（`_trash`，72h）、`maxTotalBytes`、`archive-list.json` 本地名单 |

## 四、Windows 上的路径约定

```
BOT_HOME   = C:\Users\Administrator
DSH_HOME   = C:\Users\Administrator\.dsh-qq          # 与桌面 GUI 的 .dsh 隔离
PROFILE    = %DSH_HOME%\profiles\qq
运行目录   = %BOT_HOME%\qq-dsh-bot
NapCat     = %BOT_HOME%\Napcat
Agent      = %BOT_HOME%\agent
TTS        = %BOT_HOME%\tts-out，venv 在 %BOT_HOME%\tts-venv
```

## 五、遗留差异

1. **服务管理**：计划任务 + 登录触发，不是常驻 service；机器重启后需要用户登录
   （或把任务改成 `SYSTEM` 账户并给目录授权）。
2. **日志**：没有 journalctl，看 `qq-dsh-bot\*.log`。
3. **权限**：没有 `chmod`，密钥文件用 `icacls`。
4. **NapCat 布局**：独立 `Napcat\` 目录 + `NapCatWinBootMain.exe` 注入 QQ；
   配置在 `Napcat\config\`，不在 QQ 安装目录。
5. **语音转写**：需要自己装 ffmpeg + whisper.cpp，并把模型放到
   `%USERPROFILE%\whisper.cpp\models\` 或用 `WHISPER_CPP_MODELS` 指定。
