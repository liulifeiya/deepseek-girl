# 延时会话（Deferred Session）

QQ 机器人里「不立刻回、等合适时机再回」这一整套机制的统称。

## 包含两块

1. **超时补发** — `dsh-onebot-qq/lib/deferred.js`（Deferred delivery）
   回复超时后不放弃回合，把仍在跑的结果补发回原会话。

2. **群聊插话** — `dsh-onebot-qq/lib/group-wake.js`
   群消息先进缓冲，安静一段时间后按热度/关键词判定一次，决定接一句还是 `[[skip]]` 保持安静。

## 相关文件

- 配置：`~/.dsh-user/group-wake.json`
- 补丁：`~/qq-dsh-bot/patches/apply-onebot-patches.py`
- 静默/分段规则：见 `group-wake.json` 与 `outbound.js` 的 `autoSplitChunks`

## 命名约定

- 中文：延时会话
- 英文：Deferred Session
- 单模块仍按各自名字称呼（超时补发 / 群聊插话），避免混淆。
