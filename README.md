# deepseek-girl

一套可迁移的 QQ 机器人：DeepSeek Harness（dsh）+ dsh-onebot-qq + NapCat，带人设、记忆、主动搭话、群聊插话、常挂 agent 和定时任务。

「不立刻回、等合适时机再回」的机制见 `patches/DEFERRED-SESSION.md`。

## 一键部署

```bash
git clone https://github.com/liulifeiya/deepseek-girl.git ~/deepseek-girl
cd ~/deepseek-girl
cp deploy/deploy.conf.example deploy/deploy.conf && chmod 600 deploy/deploy.conf
$EDITOR deploy/deploy.conf          # 填 BOT_QQ / ADMIN_QQ / ONEBOT_TOKEN / DEEPSEEK_API_KEY
./deploy/install.sh --dry-run       # 先看计划
./deploy/install.sh                 # 安装并启动
```

装完首次要扫码登录 QQ（NapCat 不能自动登录）：

```bash
~/tts-venv/bin/python ~/qq-dsh-bot/qr-term.py
```

从老机器搬家看 **[docs/MIGRATION.md](docs/MIGRATION.md)**：导出 → 新机器装环境 → 导入 → 扫码 → 验收。

Windows（Server 2022/2025、Win10+）没有 systemd，用 PowerShell + 计划任务部署，
见 **[docs/WINDOWS.md](docs/WINDOWS.md)** 和 **[deploy/windows/](deploy/windows/)**。

## 目录

| 路径 | 内容 |
|---|---|
| `deploy/` | 部署/迁移脚本：`install.sh`、`preflight.sh`、`migrate-export.sh`、`migrate-import.sh`、systemd 模板 |
| `personas/` | 角色卡（1 大肥鱼十二三岁 / 2 溟月大肥鱼 / 3 鲸鱼娘）及设定原文 |
| `config/` | 行为规则 `AGENTS.md`、群聊插话 `group-wake.json`、睡眠时段、脱敏后的插件配置 |
| `patches/` | dsh-onebot-qq 补丁、NapCat 快速登录补丁、延时会话文档 |
| `scripts/` | 主动问候、图片预处理、月度记忆整理 |
| `runtime/` | 保活守卫、在线心跳、看门狗、终端二维码 |
| `tts/` | 小米 MiMo TTS、Mureka 音乐、表情包生成 |
| `agent/` | 常挂智能体：立项 → 实施 → 验收 |
| `memory/` | 长期记忆与操作日志 |
| `docs/` | 迁移手册 |

## 部署脚本能做什么

`deploy/install.sh` 按 8 步执行，全部幂等，可单独重跑：

| 步骤 | 内容 |
|---|---|
| `10-base` | apt 依赖、中文字体、时区 Asia/Shanghai |
| `20-dsh` | Node 24 + pnpm + dsh（版本在 `deploy.conf` 里锁死） |
| `30-plugins` | profile、pnpm 插件、cordis 覆盖、onebot 补丁 |
| `40-botfiles` | 机器人脚本、补丁、人设、OneBot token |
| `50-tts` | venv + Pillow 等依赖 + TTS 脚本 |
| `60-agent` | 常挂 agent 代码与目录 |
| `70-napcat` | QQ/NapCat 安装、OneBot/WebUI 配置、快速登录补丁 |
| `80-services` | systemd 用户单元、linger、启动 |

常用参数：

```bash
./deploy/install.sh --dry-run          # 只打印
./deploy/install.sh --only 30,80       # 只跑指定步骤
./deploy/install.sh --skip napcat,tts  # 跳过组件
./deploy/install.sh --no-start         # 装完不启动（先导入数据）
```

## 注意

- 密钥、Token、登录态都不入库：`deploy/deploy.conf`、`onebot-token.txt`、`dsh-web.env` 均在 `.gitignore`；`cordis.patch.yml` 里是占位符。
- `patches/apply-onebot-patches.py` 幂等；插件或 NapCat 升级后要重跑。
- 同一 QQ 不能两台机器同时在线，迁移时先停老机器再起新机器。
