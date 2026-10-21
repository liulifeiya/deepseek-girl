# deepseek-girl

本机 QQ 机器人（DeepSeek Harness + dsh-onebot-qq + NapCat）的人格、配置、补丁、脚本与记忆备份。

整套「不立刻回、等合适时机再回」的机制，统称 **延时会话（Deferred Session）**，见 `patches/DEFERRED-SESSION.md`。

## 目录

| 目录 | 内容 |
|---|---|
| `personas/` | 角色卡库（1 大肥鱼十二三岁 / 2 溟月大肥鱼 / 3 鲸鱼娘）及设定原文 |
| `config/` | 行为规则 `AGENTS.md`、群聊插话配置 `group-wake.json`、插件配置（已脱敏） |
| `patches/` | dsh-onebot-qq 的本地补丁、NapCat 快速登录修复、引用回复补丁 |
| `scripts/` | 主动问候、图片预处理、月度提示词 |
| `memory/` | 长期记忆与操作日志 |

## 注意

- 所有密钥、Token、登录态都**不入库**：`onebot-token.txt`、`dsh-web.env`、`cordis.patch.yml` 的 `accessToken` 已替换为占位符。
- 恢复时把 `cordis.patch.yml` 的 `accessToken` 填回真实的 OneBot Token。
- `patches/apply-onebot-patches.py` 幂等，可重复跑；NapCat 升级会覆盖 `napcat.mjs`，需重打快速登录补丁（见 `patches/NAPCAT-QUICK-LOGIN.md`）。
