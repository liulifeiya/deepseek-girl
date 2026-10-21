# SPEC — 群聊自主接话模块（OneBot 11 / Node.js）

- 项目：`/home/ubuntu/agent/projects/1020-2127-astrbot-onebot-node`
- 状态：v0.1 立项（2026-10-20）
- 模块名：`group-autochat`
- 交付形态：零第三方依赖的 Node.js 库 + 可选 HTTP sidecar + CLI/demo

## 1. 目标

做一个独立的群聊自主接话模块：读取群里**所有人**的近期消息（不只是 @ 机器人的），结合最近上下文判断“这个话值不值得接、接哪条、用什么上下文接”，在通过频率/防抢话/防刷屏门控后主动发言；冷场、与机器人无关、或正在被人与人对话占用时保持沉默。

设计目标：

1. **默认沉默**：模块的默认倾向是不说话；只有明确相关、且不打扰对话时才接。
2. **可解释**：每次决定返回 `action`、`reason`、`score`；便于日志、调参和测试。
3. **可控频率**：按群冷却、每小时上限、最近机器人发言、静音时段控制，避免刷屏。
4. **独立可挂**：不修改、不 import 现有线上插件；以 OneBot 11 HTTP 旁路或库 API 接入。
5. **职责拆分**：模块负责“接不接/接哪条/给什么上下文”，具体回什么由宿主注入的 `replyGenerator` 决定；生成器可返回 `[[skip]]` 最终弃权。
6. **可测试**：决策核心是确定性的纯逻辑，时钟可注入；`node:test` 覆盖核心场景，不依赖真实 QQ。

### 参考与差异

参考 AstrBot 生态群聊模块的“漏斗”思路：**缓冲全部群消息 → 热度/相关性 → 概率或阈值 → 冷却/每小时上限 → 模型最终决定是否 `[[skip]]`**。现有本地的 `group-wake` 旁路补丁也采用了类似思路（缓冲、关键词、冷却、静默 token），但它依赖插件内部 `ctx`、以“安静一段时间”为触发条件，并且是修改插件文件的补丁。

本机未安装 AstrBot；立项时只读查看了现有 OneBot 适配层与 `group-wake` 旁路补丁的接口，参考其漏斗思路，不复制其代码。本模块的差异：

- 不依赖任何插件内部对象；通过公开的 OneBot 11 事件/HTTP API 或库 API 接入。
- **不做冷场触发**：会话必须仍在活跃窗口内才考虑接话；长时间没人说话就沉默。
- 前置门控是确定性的，不使用“无关话题随机兜底概率”，避免为刷存在感而插话。
- 机器人自己的发言也进入历史，用于防连发；`recordReply` 只在真正发送成功后调用。
- 最终“怎么接”交给宿主生成器/模型；生成器返回空或 `[[skip]]` 时不发送。

## 2. 典型使用场景

1. **群聊正在聊机器人了解的话题**：大家连续聊 AI / 游戏 / 电影，机器人根据关键词、问句和上下文接一句，并引用最后一条消息。
2. **两人快速对话**：两个群友在 20 秒内你来我往，机器人没有收到 @，保持沉默，避免抢话。
3. **冷场**：最后一条消息已过去 5 分钟以上，即使内容包含关键词，也不主动“暖场”。
4. **有人明确 @ 机器人**：作为候选接话；仍需通过静音时段、冷却和每小时上限，避免被连续 @ 时刷屏。
5. **OneBot 旁路接入**：现有 Python/Node 机器人继续运行；另起 Node sidecar，接收 OneBot HTTP 群事件，通过 OneBot HTTP API 发消息，不改线上插件文件。
6. **库内嵌**：已有 Node OneBot 宿主直接 `import { createAutoChat }`，把事件喂给 `observe`，自己发送并调用 `recordReply`。
7. **静音时段**：23:30–08:00 默认不主动发言；宿主自己的命令/私聊逻辑不受本模块影响。

## 3. 范围

### 3.1 做什么（v0.1）

- 纯 Node.js（ESM）决策核心，零第三方运行时依赖。
- 按群维护最近消息环形缓冲（默认 40 条），支持 TTL/活跃窗口判断。
- 输入归一化：群号、用户、昵称、文本、消息 ID、时间、是否自己、是否 @ 机器人、回复目标。
- 确定性门控：空历史、机器人最后发言、冷场、静音时段、冷却、每小时上限、回复他人、快速双人对话。
- 确定性相关性评分：兴趣关键词、问句、最近活跃人数、最近机器人发言惩罚。
- 输出决策：`reply` / `silent`、reason、score、`replyToMessageId`、最近上下文。
- `buildReplyPrompt()`：把上下文、回复目标和“1–2 句、别总结、可 `[[skip]]`”的约束组装成提示词，供宿主生成器使用。
- OneBot 11 群事件归一化与 `send_group_msg` 负载构造。
- HTTP sidecar：`POST /onebot/event` 接事件，`GET /healthz` 健康检查，使用内置 `fetch` 调 OneBot HTTP API；支持 token、dry-run、事件去重。
- CLI/demo：`node examples/demo.js` 用脚本化消息流演示决策；`node src/cli.js` 启动 sidecar。
- 标准库 `node:test` 单测 + 接入说明（README）。
- 可选：把核心库嵌入现有 Node 宿主，不启动 HTTP 服务。

### 3.2 明确不做（v0.1；部分留 v0.2）

- 不修改、不覆盖、不打补丁到任何线上插件文件（包括现有 `group-wake` 补丁）；不 import 其私有模块或 `ctx`。
- 不直接调用 LLM/API，不保存 API Key；回复文本由宿主注入的生成器产生。
- 不做模型训练、embedding、向量库、情感/意图大模型分类。
- 不处理图片/语音/视频内容；非文本消息只保留占位符，不参与语义判断。
- 不主动“暖场/冷场救场”，不做随机无关插话。
- 不做持久化数据库、跨重启状态恢复；冷却和计数都在内存中，重启归零。
- 不做多平台（微信/Telegram/Discord）、多账号、多机器人实例协调。
- 不做 Web UI、管理后台、配置热更新、npm 发布、单文件二进制。
- 不做百万消息性能优化/压测；默认只保留最近 40 条。
- 不保证绕过平台风控或“像真人”；接入者需自行遵守群规和平台规则。
- 不实现 OneBot 反向 WebSocket 服务端；v0.1 走 HTTP 事件/API 或库内嵌，WS 适配留 v0.2。
- 不支持只开反向 WS、未启用 HTTP 事件/API 的 OneBot 部署；这种部署需要在 OneBot 侧启用 HTTP，或等 v0.2 的 WS 客户端适配。
- 不自动停用现有 `group-wake`；两套自主接话同时开可能重复发言，接入时需二选一（文档说明，不自动改配置）。

### 3.3 运行环境

- Node.js ≥ 20（本机实测 v24.19.0），ESM。
- 零第三方依赖：`node:http`、`node:test`、全局 `fetch`、`URL` 等内置能力。
- 主要目标 Linux/macOS；Windows 未实测。
- OneBot 11 实现需支持 HTTP 事件上报和 HTTP API（NapCat / Lagrange / go-cqhttp 等通常支持）；具体配置由接入方完成。
- 不需要 Python；不依赖 NoneBot/AstrBot 运行时。

## 4. 架构与接口

### 4.1 计划目录

```text
package.json              # type: module，dependencies 为空
src/engine.js             # 决策核心、历史、冷却、评分
src/prompt.js             # buildReplyPrompt
src/onebot.js             # OneBot 11 事件归一化 / 发送负载
src/server.js             # HTTP sidecar（node:http + fetch）
src/cli.js                # 环境变量启动、dry-run、加载生成器
examples/demo.js          # 脚本化消息流演示
test/engine.test.js
test/onebot.test.js
test/server.test.js
README.md
SPEC.md
PLAN.md
WORKLOG.md
```

### 4.2 核心 API

```js
import { createAutoChat, buildReplyPrompt } from './src/engine.js';

const engine = createAutoChat({
  interestKeywords: ['AI', '游戏'],
  cooldownMs: 180000,
  maxPerHour: 6,
  activeWindowMs: 300000,
  quietHours: { start: '23:30', end: '08:00' },
  now: () => Date.now(), // 测试可注入
});

const accepted = engine.observe({
  groupId: '123',
  userId: '456',
  nickname: '小明',
  text: '有人玩这个 AI 游戏吗？',
  messageId: 'm1',
  at: Date.now(),
  isSelf: false,
  mentionsSelf: false,
  replyToMessageId: null,
});

const decision = engine.decide('123');
// {
//   action: 'reply' | 'silent',
//   reason: 'empty' | 'bot-spoke-last' | 'cold' | 'quiet-hours' |
//           'cooldown' | 'hourly-cap' | 'reply-to-other' |
//           'rapid-exchange' | 'low-relevance' | 'mentioned' | 'relevant',
//   score: 0.0,
//   replyToMessageId: 'm1' | null,
//   context: [ ...最近 contextLimit 条消息... ]
// }

if (decision.action === 'reply') {
  const prompt = buildReplyPrompt(decision);
  const text = await replyGenerator({ decision, prompt });
  if (text && text.trim() !== '' && text.trim() !== '[[skip]]') {
    await sendGroupMessage(text, decision.replyToMessageId);
    engine.recordReply('123'); // 只有发送成功后才调用
  }
}
```

### 4.3 数据结构

**输入消息**（核心层；OneBot 适配器负责归一化）：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `groupId` | string | 是 | 群号 |
| `userId` | string | 是 | 发送者 QQ 号 |
| `nickname` | string | 否 | 群名片/昵称，缺省用 userId |
| `text` | string | 是 | 纯文本；非文本由适配器转占位符 |
| `messageId` | string | 是 | OneBot message_id，用于去重和回复 |
| `at` | number | 否 | epoch ms；缺省为 `now()` |
| `isSelf` | boolean | 否 | 是否机器人自己发的 |
| `mentionsSelf` | boolean | 否 | 是否 @ 了机器人 |
| `replyToMessageId` | string/null | 否 | 回复的目标消息 ID |

**决策**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `action` | `"reply"` / `"silent"` | 是否接话 |
| `reason` | string | 见上式枚举，必须可解释 |
| `score` | number | 0~1，mention 固定为 1 |
| `replyToMessageId` | string/null | 要引用的最后一条人类消息；silent 时为 null |
| `context` | array | 最近 `contextLimit` 条消息，oldest→newest，包含自己发出的消息 |

`observe(message)` 返回 `true` 表示入缓冲，`false` 表示重复 messageId、命令或以空文本被忽略。`decide(groupId, now?)` **不修改**频率状态；`recordReply(groupId, at?)` 只记录成功发送，用于冷却和每小时计数。`reset(groupId?)` 清空状态。

### 4.4 配置默认值

| 配置 | 默认 | 说明 |
| --- | --- | --- |
| `historyLimit` | 40 | 每群保留消息数，5..200 |
| `contextLimit` | 12 | 返回给生成器的上下文条数，1..50 |
| `activeWindowMs` | 300000（5 分钟） | 最后消息超过此值视为冷场 |
| `cooldownMs` | 180000（3 分钟） | 两次机器人发言的最小间隔 |
| `maxPerHour` | 6 | 每群每小时最多主动发言次数 |
| `minScore` | 0.55 | 相关性阈值 |
| `quietHours` | `{start:"23:30", end:"08:00"}` | 本地时间静音时段；传 `null` 关闭 |
| `interestKeywords` | `[]` | 兴趣关键词数组；大小写不敏感子串匹配；默认空表示只有 @ 或问句才可能接 |
| `rapidWindowMs` | 20000 | 快速双人对话判定窗口 |
| `now` | `Date.now` | 可注入时钟，测试用 |

配置非法（`maxPerHour` 非正整数、`cooldownMs` 为负、`contextLimit` 越界等）在创建时抛 `RangeError`/`TypeError`，不静默降级。

### 4.5 决策规则（按顺序，先命中先返回）

1. **empty**：该群没有任何历史消息。
2. **bot-spoke-last**：最后一条消息 `isSelf=true`。机器人不能连发；要等人类说话。
3. **cold**：`now - 最后一条消息.at > activeWindowMs`。冷场不救场。
4. **quiet-hours**：本地时间位于静音时段（start 含、end 不含，支持跨午夜；`quietHours=null` 关闭）。
5. **cooldown**：距上次 `recordReply` 小于 `cooldownMs`。
6. **hourly-cap**：最近 3600000ms 内 `recordReply` 次数 ≥ `maxPerHour`。
7. **reply-to-other**：最后一条消息带 `replyToMessageId`，且目标不是历史中已知的机器人消息；不 @ 机器人时沉默。
8. **rapid-exchange**：最近 3 条人类消息都在 `rapidWindowMs` 内，且来自 ≥2 个不同用户；不 @ 机器人时沉默，避免插进两人对话。
9. **评分与阈值**：
   - `mentionsSelf=true`：score = 1.0，跳过第 7/8 步（但仍受 1–6 步约束）。
   - 否则从 0.1 起：
     - 命中的不同兴趣关键词各 +0.35，最多 +0.70；
     - 问句（含 `?`/`？`，或含 `怎么`/`如何`/`为什么`/`是不是`/`能不能`/`有没有`/`吗`/`呢`）+0.15；
     - 最近 60 秒有 ≥2 个不同人类用户发言 +0.10；
     - 最近 3 条消息中出现机器人消息 -0.20；
     - clamp 到 0..1。
   - 若 score < `minScore` → **low-relevance**。
10. **reply**：reason 为 `mentioned`（@ 触发）或 `relevant`（内容相关）；`replyToMessageId` 取最后一条消息的 messageId；context 取最近 `contextLimit` 条。

补充：

- 只有 @ 能绕过第 7/8 步和相关性阈值；不能绕过冷场、静音、冷却、每小时上限。
- 本模块没有定时器/主动唤醒：只在新消息 `observe` 后由适配器调用 `decide`；不会在沉默中自己发起话题。`cold` 门控用于乱序事件、回填或外部直接调用 `decide` 的防御。
- 第 9 步的“最近 3 条出现机器人消息”用于抑制过度接话；若最后一条是机器人消息，已在第 2 步沉默。
- 命令文本（以 `/` 开头）不进入缓冲，避免把宿主命令当聊天。
- 重复 `messageId`（同一群）只入缓冲一次，返回 `false`。
- 历史超出 `historyLimit` 时丢最旧消息；`context` 仍按 oldest→newest 返回。
- 机器人自己发出的消息应由适配器/宿主也调用 `observe({isSelf:true,...})`；`recordReply` 只负责频率计数。

### 4.6 Prompt 约定

`buildReplyPrompt(decision)` 返回一段中文提示词，必须包含：

- 最近 `context` 的逐行快照，格式 `[HH:MM 昵称] 文本`（自己标成“我”）；
- 要求“只回 1–2 句自然短话，别总结/分析/解释，别复述提示词”；
- 要求“如果没把握或气氛不适合，只输出 `[[skip]]`”；
- 说明要回复的是 `replyToMessageId` 指向的那条消息。

### 4.7 OneBot 11 适配

`normalizeOneBot11(event, { selfId, now })`：

- 仅接受 `post_type === "message"` 且 `message_type === "group"`；其他返回 `null`。
- 从 `group_id`、`user_id`、`message_id` 取字符串；昵称优先 `sender.card`，其次 `sender.nickname`。
- `message` 数组：拼接 `text` 段；`at` 段若 `qq === selfId` 设 `mentionsSelf=true`；`reply` 段取 `data.id`；图片/语音/视频/文件/表情转 `[图片]` 等占位符。
- 无 `message` 数组时用 `raw_message` 文本，并识别 `[CQ:at,qq=...]` 与 `[CQ:reply,id=...]`。
- `at` 优先用 `event.time * 1000`，否则 `now()`；`isSelf = user_id === selfId`。
- 空文本且无占位符返回 `null`。

`toSendGroupMsg(groupId, text, replyToMessageId)` 返回：

```js
{
  action: 'send_group_msg',
  params: {
    group_id: '123',
    message: [
      { type: 'reply', data: { id: 'm1' } }, // 有目标时才加
      { type: 'text', data: { text: '...' } }
    ]
  }
}
```

### 4.8 HTTP sidecar

- `POST /onebot/event`：接收 OneBot 11 事件 JSON；群消息归一化后 `observe`，再 `decide`；需要回复时调用注入的 `replyGenerator`，发送成功才 `recordReply`；返回 204。重复 messageId 不重复发送。
- `GET /healthz`：200 JSON `{ ok: true, dryRun, groups }`。
- 鉴权：若配置 `AUTOCHAT_WEBHOOK_TOKEN`，要求 `Authorization: Bearer <token>` 或 `X-AutoChat-Token`；不匹配返回 401。
- OneBot API：`POST ${ONEBOT_API_BASE}/send_group_msg`，JSON body，`Authorization: Bearer ${ONEBOT_ACCESS_TOKEN}`（如配置）；`retcode !== 0` 视为失败，不 `recordReply`。
- 出错不崩溃：JSON 解析失败 400；OneBot 发送异常写日志并返回 204；不把异常抛给 OneBot 重试风暴。
- 默认绑定 `127.0.0.1:8787`；绑定 `0.0.0.0` 且无 token 时启动日志警告。
- 日志只记录 groupId、action、reason、score、耗时；不记录消息正文、token。
- Dry-run：`AUTOCHAT_DRY_RUN=1` 或未提供生成器时不发送、不 `recordReply`，只记录 `would-reply`。
- CLI 环境变量：`AUTOCHAT_HOST`、`AUTOCHAT_PORT`、`AUTOCHAT_WEBHOOK_TOKEN`、`ONEBOT_API_BASE`、`ONEBOT_ACCESS_TOKEN`、`ONEBOT_SELF_ID`、`AUTOCHAT_DRY_RUN`、`AUTOCHAT_REPLY_MODULE`、`AUTOCHAT_CONFIG`。
- `AUTOCHAT_CONFIG` 可选，指向只读 JSON（engine 配置，如关键词/冷却）；不设置则用默认值。未设置 `AUTOCHAT_REPLY_MODULE` 或 `AUTOCHAT_DRY_RUN=1` 时为 dry-run；非 dry-run 时 `ONEBOT_API_BASE` 必填，缺失则启动报错。
- 生成器模块契约：`export async function generateReply({ decision, prompt, groupId, context })`，返回字符串或 `null`；返回空/`[[skip]]` 不发送。

**接入方式：**

1. **Sidecar（推荐给 Python/现有机器人）**：本模块独立进程；OneBot 配置把群消息 HTTP POST 到 `/onebot/event`，HTTP API 指向同一 OneBot。现有插件文件不改。
2. **库内嵌（Node 宿主）**：宿主把已有 OneBot 事件归一化后喂 `observe`，发送后调用 `recordReply`；不启动 HTTP 服务。
3. **不提供**：不需要修改现有 `group-wake` 补丁；若要切换，接入方自行停用旧补丁，模块不会自动改配置。

## 5. 可检验的验收标准

测试用固定时钟（注入 `now`）、内存消息和 fake `fetch`/fake HTTP；不依赖真实 QQ。所有 AC 应能用 `node --test` 或等价的确定性脚本验证。

| 编号 | 验收标准 | 验证方法 |
| --- | --- | --- |
| AC-1 | 空群历史返回 `silent/empty`；最后消息超过活跃窗口（默认 5 分钟）时，即使含关键词也返回 `silent/cold` | 构造空 engine 与 6 分钟前的关键词消息，断言 action/reason |
| AC-2 | 活跃但无关的消息返回 `silent/low-relevance`，score 低于 0.55 | 输入“今天天气不错”，断言不接话 |
| AC-3 | 活跃且相关时返回 `reply/relevant`，score ≥ 0.55，`replyToMessageId` 是最后一条消息，context 含最近消息 | 关键词 + 问句消息，断言字段 |
| AC-4 | `recordReply` 后冷却内返回 `silent/cooldown`；最后一条是机器人消息返回 `silent/bot-spoke-last`；冷却结束且人类再发言后恢复 `reply` | 注入时钟，逐步推进，断言 reason |
| AC-5 | 每小时上限：达到 `maxPerHour` 后返回 `silent/hourly-cap`；超过 3600000ms 后恢复 | `maxPerHour=2`，记录 2 次，再测第 3 次与 61 分钟后 |
| AC-6 | `mentionsSelf=true` 时，即使没有关键词也返回 `reply/mentioned`（在无冷却/静音前提下）；静音/冷却仍可拦截 | 输入“在吗”并设 @，断言 |
| AC-7 | 不 @ 时，最近 3 条人类消息在 20 秒内来自 ≥2 人 → `silent/rapid-exchange`；最后一条 @ 机器人则不被该门控拦截 | 构造双人快速对话，分别测有/无 @ |
| AC-8 | 最后一条消息回复的是另一个人类 → `silent/reply-to-other`；回复的是已知机器人消息 → 允许继续评分 | 填写 `replyToMessageId`，断言 |
| AC-9 | 本地时间 23:30–08:00 内返回 `silent/quiet-hours`；12:00 不拦截；跨午夜区间正确 | 注入本地时间对应的 epoch，断言 |
| AC-10 | `historyLimit` 生效（只保留最新 N 条）；重复 messageId 的 `observe` 返回 false 且不会重复计数；`context` 长度不超过 `contextLimit` | 灌入 5 条、`historyLimit=3`，检查缓冲/context/重复 |
| AC-11 | 非法配置（如 `maxPerHour=0`、`cooldownMs=-1`）创建时抛错；`reset` 清空历史、冷却和计数 | 断言异常类型与 reset 后 `silent/empty` |
| AC-12 | OneBot 群事件归一化：群号/用户/昵称/消息 ID/文本/@/reply 字段正确；私聊事件返回 null；机器人自己消息 `isSelf=true` | 用样例事件调用 `normalizeOneBot11` 断言 |
| AC-13 | 发送负载为 `send_group_msg`，含 `group_id`、文本段，指定 reply 时含 reply 段且顺序正确 | 调用 `toSendGroupMsg` 断言对象 |
| AC-14 | HTTP sidecar：POST 群事件返回 204，fake fetch 收到一次 `send_group_msg`，发送成功后 `recordReply` 生效；重复事件不重复发送；`/healthz` 返回 200 JSON | 用临时端口 + fake fetch 跑端到端 |
| AC-15 | HTTP 鉴权失败 401；坏 JSON 400；非群事件 204 且不发送；OneBot 发送失败不 `recordReply`、进程不崩 | 逐个请求断言状态码/调用次数 |
| AC-16 | 零第三方依赖：`package.json` 的 `dependencies` 为空；源码 import 只允许 `node:` 内置和项目内文件；不读写线上插件目录 | 检查 package.json/import；`node --test` 全绿；demo 可跑 |
| AC-17 | `buildReplyPrompt` 包含最近上下文、回复目标、1–2 句约束和 `[[skip]]`；生成器返回 `[[skip]]`/空时不发送、不 `recordReply` | 单测 prompt 内容；HTTP 端到端用 skip 生成器断言无 fetch |

## 6. 技术选型与理由

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 运行时 | Node.js ≥20，ESM | 本机 Node 24.19；内置 `fetch`、`node:test`、`node:http`；零依赖 |
| 决策核心 | 确定性规则 + 可注入生成器 | 可控、可解释、可测试；不会随机插话；生成器负责“怎么说” |
| 事件接入 | OneBot 11 HTTP 事件 + HTTP API | 标准协议，不需要改现有插件；sidecar 与 Python/Node 宿主解耦 |
| 发送 | 全局 `fetch` + `Authorization: Bearer` | 无需安装 axios/ws；NapCat 等通常支持 HTTP API |
| 测试 | `node:test` + fake fetch/http | 标准库，无 pytest/vitest 依赖；不连真实 QQ |
| 状态 | 内存 Map + 每群数组 | 7 天/40 条规模足够；重启归零是可接受 v0.1 边界 |
| 生成器 | 宿主注入的 `generateReply` | 不绑定模型/供应商；AstrBot/NoneBot 可接自己的模型；避免 API Key 入库 |
| 集成 | 独立 sidecar 或库内嵌 | 不改线上插件；HTTP 适合 Python 宿主，库 API 适合 Node 宿主 |

被否方案：

- **修改 `group-wake.js`/插件**：用户明确要求不改线上插件；耦合 `ctx` 也不可移植。
- **直接依赖 AstrBot**：AstrBot 是 Python 生态；本模块要独立 Node，且本机未安装 AstrBot。
- **`ws` 依赖做反向 WS**：引入依赖、测试复杂；v0.1 用 HTTP，WS 留 v0.2。
- **直接调用 LLM SDK**：需要 Key、供应商和费用；把生成器留给宿主更灵活。
- **随机兜底概率**：会造成无关插话，违背“与它无关不说话”；v0.1 不采用。
- **等待冷场再插话**：与用户“冷场不说话”相反；只检查活跃窗口。
- **向量数据库/embedding**：小群近 40 条消息，规则+关键词足够；避免重依赖。

## 7. 主要风险

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 规则过保守，几乎不接话 | 体验差 | `interestKeywords`/`minScore` 可调；demo 与日志给出 reason/score；v0.2 再引入模型打分 |
| 规则过激进或生成器话多 | 刷屏/抢话 | 默认沉默、冷却、每小时上限、双人快速对话门控、`[[skip]]` 二次弃权 |
| 群消息含隐私/敏感内容 | 泄露 | 核心不联网、不记正文；日志只记 groupId/reason/score；生成器由宿主负责合规 |
| OneBot 事件重复/乱序 | 重复回复 | messageId 去重；以 `at`/到达顺序维护；文档说明乱序限制 |
| OneBot HTTP 实现差异（鉴权头/字段） | 接不上 | 适配层只依赖 v11 标准字段；文档给出 NapCat/Lagrange 配置示例；可改 header |
| 现有 `group-wake` 同时运行 | 双回复 | 明确二选一；本模块不自动停用旧补丁；接入说明警示 |
| 静音时段/时区理解不一致 | 半夜发言 | 用服务器本地时间并写入文档；`quietHours=null` 可关闭；测试跨午夜 |
| 生成器慢/超时 | 事件堆积/重试 | sidecar 设置生成超时（默认 20s）；超时按 skip 处理；OneBot 事件去重 |
| 重启丢冷却状态 | 重启后多发 | 文档声明内存状态；v0.2 可选持久化；默认 cooldown 仍能防连发 |
| 0.0.0.0 暴露 webhook | 未授权调用 | 默认绑定 127.0.0.1；有 token 才建议外露；启动警告 |
| 平台风控/群规 | 账号风险 | 不承诺规避；建议小范围、低频率、遵守群规；dry-run 先观察 |

## 8. 交付与完成定义

v0.1 交付物：

- `src/engine.js`、`src/prompt.js`：决策、历史、评分、prompt。
- `src/onebot.js`：OneBot 11 归一化与发送负载。
- `src/server.js`、`src/cli.js`：HTTP sidecar、dry-run、生成器加载。
- `examples/demo.js`：脚本化消息流，能直接 `node examples/demo.js` 看决策。
- `test/*.test.js`：`node --test` 全绿，覆盖 AC-1~AC-17 核心路径。
- `README.md`：安装、OneBot 配置、两种接入方式、生成器契约、环境变量、安全、已知局限、与 AstrBot/现有补丁的关系。
- `SPEC.md`、`PLAN.md`、`WORKLOG.md`。

完成定义：AC-1~AC-17 实测通过；`node --test` 全绿；`node examples/demo.js` 可运行；`package.json` 无第三方依赖；实现与测试过程中未修改任何线上插件文件或配置（部署时由用户自行配置 OneBot HTTP 事件/API）；README 能让用户在“sidecar”和“库内嵌”之间做出选择并完成接入。
