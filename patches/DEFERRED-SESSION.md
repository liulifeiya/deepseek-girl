# 延时会话（Deferred Session）

QQ 机器人里「什么时候不说话、什么时候开口、用谁的身份开口」这一整套机制的统称。

## 组成

| 模块 | 文件 | 作用 | 状态 |
|---|---|---|---|
| 超时补发 | `deferred.js` | 回复超时后不放弃回合，把结果补发回原会话 | 启用 |
| 群聊插话 | `group-wake.js` | 群消息缓冲、安静后判定要不要主动接话 | **已停用**（`enabled: false`） |
| @ 上下文 | `mention-context.js` | 被 @ 时收集本人近期发言与相关讨论 | 启用 |
| 睡眠时段 | `sleep-window.js` | 法定工作日工作时段完全沉默 | 启用 |
| 人格锁定 | `persona-lock.js` | 管理员发言时强制用 1 号人格 | 启用 |

## 规则串联

```
群消息
  │
  ├─ 睡眠时段？ → 是：直接丢弃（@ 也不理）
  ├─ 被 @？    → 否：只进缓冲，不回复
  │             是：收集上下文 → 关联筛选 → 注入人格锁（管理员）→ 回复
  │
  └─ 出站：按话题/句号切分，最多 3 条，间隔 400ms
```

## 关键配置

- `~/.dsh-user/sleep-window.json` — 睡眠时段、2026 年节假日与调休表
- `~/.dsh-user/group-wake.json` — 插话参数（已 `enabled: false`）
- `~/.dsh-user/profiles/web/cordis.patch.yml` — `requireMention: true`

## 相关文件

- 补丁：`patches/apply-onebot-patches.py`（幂等，可重复跑）
- 分段：`outbound.js` 的 `autoSplitChunks`，单轮硬上限 3 条
- 人设：`personas/personas.json`（1 大肥鱼十二三岁 / 2 溟月大肥鱼 / 3 鲸鱼娘）

## 命名约定

- 中文：延时会话
- 英文：Deferred Session
- 单模块仍按各自名字称呼（超时补发 / 群聊插话 / @ 上下文 / 睡眠时段 / 人格锁定），避免混淆。
