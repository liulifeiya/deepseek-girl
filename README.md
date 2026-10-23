# deepseek-girl

一套可迁移的 QQ 机器人：DeepSeek Harness（dsh）+ dsh-onebot-qq + NapCat，带人设、记忆、主动搭话、群聊插话、常挂 agent 和定时任务。

「不立刻回、等合适时机再回」的机制见 `patches/DEFERRED-SESSION.md`。

## 一键部署（Windows）

目标机：Windows Server 2022/2025 或 Windows 10+，PowerShell 5.1 即可。

```powershell
git clone https://github.com/liulifeiya/deepseek-girl.git $env:USERPROFILE\deepseek-girl
cd $env:USERPROFILE\deepseek-girl

# 依赖（一次性）：Node 22+、Python 3.12、pnpm、dsh
corepack enable --install-directory $env:APPDATA\npm pnpm
pnpm add -g @deepseek-ai/dsh

.\deploy\preflight.ps1          # 体检
.\deploy\install.ps1 -DryRun    # 先看计划
.\deploy\install.ps1            # 安装并启动
```

装完首次要扫码登录 QQ（NapCat 不能自动登录）：

```powershell
.\deploy\show-qr.ps1
```

部署细节、目录约定、计划任务见 **[deploy/README.md](deploy/README.md)**；
改造记录与遗留差异见 **[docs/WINDOWS.md](docs/WINDOWS.md)**。


## 目录

| 路径 | 内容 |
|---|---|
| `deploy/` | Windows 部署：`install.ps1`、`preflight.ps1`、启动/保活/任务脚本、NapCat 配置生成 |
| `personas/` | 角色卡（1 大肥鱼十二三岁 / 2 溟月大肥鱼 / 3 鲸鱼娘）及设定原文 |
| `config/` | 行为规则 `AGENTS.md`、群聊插话 `group-wake.json`、睡眠时段、脱敏后的插件配置 |
| `patches/` | dsh-onebot-qq 补丁、会话人设绑定、NapCat 相关说明 |
| `scripts/` | 主动问候、图片预处理、人设导入、月度记忆整理 |
| `runtime/` | 保活守卫、在线心跳、看门狗、终端二维码 |
| `tts/` | 小米 MiMo TTS、Mureka 音乐、表情包生成 |
| `agent/` | 常挂智能体：立项 → 实施 → 验收 |
| `memory/` | 长期记忆与操作日志 |
| `docs/` | Windows 适配记录 |

## 部署脚本能做什么

`deploy/install.ps1` 按 8 步执行，全部幂等，可单独重跑：

| 步骤 | 内容 |
|---|---|
| `10-base` | 依赖检查：Node ≥ 22、pnpm、Python 3.12、dsh |
| `20-dsh` | 建 profile 并安装 6 个插件 |
| `30-plugins` | cordis 覆盖、OneBot token、onebot 补丁（含 Windows 路径补丁） |
| `40-botfiles` | 机器人脚本、补丁、人设卡导入、AGENTS.md |
| `50-tts` | venv + Pillow 等依赖 + TTS 脚本 |
| `60-agent` | 常挂 agent 代码与目录 |
| `70-napcat` | NapCat 的 OneBot/WebUI 配置生成 |
| `80-services` | 10 个计划任务（登录自启、保活、定时） |

常用参数：

```powershell
.\deploy\install.ps1 -DryRun          # 只打印
.\deploy\install.ps1 -SkipTasks       # 不注册计划任务
.\deploy\install.ps1 -SkipStart       # 装完不启动
.\deploy\install.ps1 -BotQQ 123 -AdminQQ 456 -OneBotToken <hex>
```

## 注意

- 密钥、Token、登录态都不入库：`deploy/deploy.conf`、`onebot-token.txt`、`dsh-web.env` 均在 `.gitignore`；`cordis.patch.yml` 里是占位符。
- `patches/apply-onebot-patches.py` 幂等；插件或 NapCat 升级后要重跑。
- 同一 QQ 不能两台机器同时在线，迁移时先停老机器再起新机器。
