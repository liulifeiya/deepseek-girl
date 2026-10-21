# group-autochat

零依赖 Node.js 群聊自主接话模块：读取 OneBot 11 群聊里所有人的近期消息，判断是否值得接、接哪条、给什么上下文；默认沉默，受冷却、每小时上限、静音时段和防抢话门控约束。可以作为独立 HTTP sidecar 运行，也可以把决策核心嵌入现有 Node 宿主。它不修改、不 import 任何线上插件文件。

当前版本：v0.1（T1~T6）。

## 环境要求

- Node.js ≥ 20（本机验证 v24.19）
- OneBot 11 实现支持 **HTTP 事件上报** 和 **HTTP API**（NapCat、Lagrange、go-cqhttp 等通常支持）
- 零第三方依赖：不需要 `npm install`，测试用 Node 内置 `node:test`
- Linux/macOS 为主要目标；Windows 未实测

> 如果现有 OneBot 只开了反向 WebSocket、没有 HTTP，需要先在 OneBot 侧启用 HTTP；v0.1 不实现 WS 客户端，也不修改任何插件文件。

## 快速开始

不需要安装依赖。先跑本地 demo（固定时钟、脚本化消息，不连 QQ）：

```bash
node examples/demo.js          # 决策引擎
node examples/onebot-demo.js   # 4 个 OneBot 11 事件 → 归一化/发送负载
```

跑测试：

```bash
npm test
# 或
node --test
```

当前 23 个测试全绿，覆盖 AC-1~AC-17 的核心路径；不会连接真实 QQ。

## 接入方式 A：HTTP sidecar（推荐给 Python/NoneBot/AstrBot）

sidecar 是独立进程：OneBot 把群消息 HTTP 事件 POST 给它；它调用 OneBot HTTP API 发消息。现有 Python/Node 机器人继续运行，不需要改插件文件。

### 1. 启动（先 dry-run）

```bash
AUTOCHAT_DRY_RUN=1 AUTOCHAT_PORT=8787 node src/cli.js
# 或 npm start（同样受环境变量控制）
```

dry-run 只记录 `would-reply`，不调用生成器、不发消息、不 `recordReply`。日志是 stdout 上的 JSON 行，不包含消息正文或 token。

### 2. OneBot 侧配置

不同实现的菜单位置不同，目标配置是：

1. 启用 **OneBot 11 HTTP API**（例如 `http://127.0.0.1:3000`），设置 access token（可选）。
2. 启用 **HTTP 事件上报**，POST 到 `http://127.0.0.1:8787/onebot/event`。
3. 上报范围选**群消息**，并确保**所有群消息都上报**（不是只上报 @ 机器人）。
4. 机器人 QQ 可填 `ONEBOT_SELF_ID`，事件里带 `self_id` 也可以。
5. 若现有实现已有另一个 WS 消费者，确认它允许多个事件消费者/额外 HTTP reporter；不允许时用方式 B 或等 v0.2。

本模块只读 OneBot 标准事件字段，不读取现有插件的内部状态，也不修改其文件/配置。

### 3. 正式运行 + 生成器

`AUTOCHAT_REPLY_MODULE` 指向一个 ESM 模块，导出 `generateReply`：

```js
// my-reply.js
export async function generateReply({ decision, prompt, groupId, context }) {
  // prompt 已包含最近上下文、回复目标、1–2 句约束和 [[skip]]
  // 这里接你自己的模型/服务；也可以直接返回一条固定话术
  // 返回 null / '' / '[[skip]]' 表示这次不发言
  return await callYourModel(prompt);
}
```

```bash
ONEBOT_API_BASE=http://127.0.0.1:3000 \
ONEBOT_SELF_ID=10001 \
ONEBOT_ACCESS_TOKEN=your-onebot-token \
AUTOCHAT_REPLY_MODULE=./my-reply.js \
AUTOCHAT_PORT=8787 \
AUTOCHAT_WEBHOOK_TOKEN=your-webhook-token \
node src/cli.js
```

`generateReply` 可以是异步的；返回非空字符串才会发送，发送成功后才 `recordReply`。sidecar 会把带 `message_id` 的机器人消息登记进历史，避免群友回复机器人时被误判成“回复其他人”。

### 4. HTTP 接口

| 方法/路径 | 说明 |
| --- | --- |
| `POST /onebot/event` | 接收 OneBot 11 事件 JSON；非群消息忽略；重复 messageId 不重复发送 |
| `GET /healthz` | `{ ok: true, dryRun, groups }` |

设置 `AUTOCHAT_WEBHOOK_TOKEN` 后，事件请求需带 `Authorization: Bearer <token>` 或 `X-AutoChat-Token: <token>`；不匹配返回 401。坏 JSON 返回 400，不会让进程崩溃。

## 接入方式 B：库内嵌（现有 Node 宿主）

不启动 HTTP 服务，直接把事件喂给决策引擎，由宿主自己发送：

```js
import { createAutoChat, buildReplyPrompt } from './src/engine.js';
import { normalizeOneBot11 } from './src/onebot.js';

const engine = createAutoChat({
  interestKeywords: ['AI', '游戏'],
  cooldownMs: 180000,
  maxPerHour: 6,
  // quietHours: null, // 关闭静音时段
});

async function onGroupEvent(event) {
  const message = normalizeOneBot11(event, { selfId: '10001' });
  if (message === null || !engine.observe(message))
    return;

  const decision = engine.decide(message.groupId);
  if (decision.action !== 'reply')
    return;

  const prompt = buildReplyPrompt(decision);
  const text = await myModel(prompt); // 或你自己的生成器
  if (!text || text === '[[skip]]')
    return;

  await sendGroupMessage(message.groupId, text, decision.replyToMessageId);
  engine.recordReply(message.groupId);

  // 若宿主能收到自己发出的消息事件，也交给 observe({isSelf:true,...})；
  // 否则建议在发送成功后自行登记 outbound message_id（sidecar 已内置）。
}
```

核心 API：

```js
const engine = createAutoChat(options);
engine.observe(message);     // true=入缓冲；false=重复/命令/空文本
engine.decide(groupId);      // { action, reason, score, replyToMessageId, context }
engine.recordReply(groupId); // 只在真正发送成功后调用
engine.reset(groupId?);      // 测试/手动清空
```

## 配置

### 环境变量（sidecar）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AUTOCHAT_HOST` | `127.0.0.1` | 绑定地址；对外暴露时务必配 token |
| `AUTOCHAT_PORT` | `8787` | 监听端口；`0` 由系统分配 |
| `AUTOCHAT_WEBHOOK_TOKEN` | 空 | 入站事件鉴权；空表示不校验 |
| `ONEBOT_API_BASE` | 空 | OneBot HTTP API，如 `http://127.0.0.1:3000`；非 dry-run 必填 |
| `ONEBOT_ACCESS_TOKEN` | 空 | 调用 OneBot API 的 Bearer token |
| `ONEBOT_SELF_ID` | 空 | 机器人 QQ；也可从事件 `self_id` 学习 |
| `AUTOCHAT_DRY_RUN` | 关 | `1/true/yes/on` 时只记录不发送 |
| `AUTOCHAT_REPLY_MODULE` | 空 | 导出 `generateReply` 的 ESM 模块路径；不设则 dry-run |
| `AUTOCHAT_CONFIG` | 空 | 可选只读 JSON，传给 `createAutoChat`（不能包含函数 `now`） |

### 引擎配置（JSON / 库参数）

| 配置 | 默认 | 说明 |
| --- | --- | --- |
| `historyLimit` | 40 | 每群保留消息数，5..200 |
| `contextLimit` | 12 | 返回给生成器的上下文条数，1..50 |
| `activeWindowMs` | 300000 | 最后消息超过 5 分钟视为冷场 |
| `cooldownMs` | 180000 | 两次机器人发言最小间隔 3 分钟 |
| `maxPerHour` | 6 | 每群每小时最多主动发言次数 |
| `minScore` | 0.55 | 相关性阈值 |
| `quietHours` | `23:30–08:00` | 本地时间静音时段；`null` 关闭 |
| `interestKeywords` | `[]` | 兴趣关键词（大小写不敏感子串）；建议按群配置 |
| `rapidWindowMs` | 20000 | 双人快速对话判定窗口 |

`AUTOCHAT_CONFIG` 示例：

```json
{
  "interestKeywords": ["AI", "游戏", "电影"],
  "cooldownMs": 180000,
  "maxPerHour": 4,
  "quietHours": { "start": "23:30", "end": "08:00" }
}
```

默认 `interestKeywords` 为空，此时通常只有 @ 机器人或足够明确的相关内容才可能接话；正式使用前请配置关键词。`quietHours` 使用运行机器的本地时区。

## 决策口径

- 只在新消息 `observe` 后决策，**没有定时器/冷场主动唤醒**；沉默中不会主动发起话题。
- 顺序门控：empty → bot-spoke-last → cold → quiet-hours → cooldown → hourly-cap → reply-to-other / rapid-exchange（@ 可绕过后两者）→ 相关性评分 → reply。
- `mention` 不绕过冷场、静音、冷却和每小时上限。
- 生成器返回 `null`/空串/`[[skip]]` 是最终弃权，不发送、不计数。
- 详细规则见 `SPEC.md` 第 4 节；每条 AC 见第 5 节。

## 安全

- 默认只监听 `127.0.0.1`；不要无 token 直接暴露到公网。必须外露时用反向代理 + TLS，并设置 `AUTOCHAT_WEBHOOK_TOKEN`。
- `ONEBOT_ACCESS_TOKEN` / webhook token 从环境变量注入；日志不记录 token 和消息正文。
- 核心不访问网络；只有 sidecar 调用你配置的 OneBot HTTP API，生成器由宿主负责。
- 先 dry-run 观察 `would-reply`，确认频率和内容后再正式发送。
- 遵守群规/平台规则；本项目不提供规避风控的能力。

## 已知局限

- v0.1 只支持 OneBot 11 HTTP 事件/API；不支持反向/正向 WebSocket 客户端，也不支持非 OneBot 平台。
- 不内置 LLM：必须由宿主提供 `generateReply`；sidecar 会等待生成器返回，建议生成器自行设置超时/快速失败。
- 状态只在内存：重启后历史、冷却、每小时计数归零；不保证重启期间不重复。
- 文本为主：图片/语音等只作为占位符，不做内容理解。
- 不做冷场主动发言、随机兜底、多账号、跨群聚合、Web UI、数据库或 npm 发布。
- 性能按每群最近 40 条消息设计，不承诺超大群/超高吞吐。
- 与 AstrBot 的群聊逻辑只是思路参考，不是 AstrBot 插件，也不保证行为完全一致。

## 与 AstrBot / 现有 `group-wake` 的关系

- **AstrBot**：Python 生态的机器人框架。本模块是独立的 Node.js 库/sidecar，不依赖 AstrBot，也不修改 AstrBot 插件；参考了 AstrBot 生态群聊模块“缓冲 → 相关性 → 频率/冷却 → 模型决定是否 `[[skip]]`”的漏斗思路。
- **现有 `group-wake` 补丁**：它是直接改插件文件的旁路补丁，依赖插件内部 `ctx`，以“安静一段时间”为触发条件并带随机兜底。本模块不 import 它、不改它；默认不做冷场触发，门控是确定性的，通过 HTTP/库 API 解耦。
- **不要同时开两套自主接话**：现有 `group-wake` 与本模块同时运行可能重复发言。若要切换，请自行停用旧补丁；本模块不会自动改任何线上配置。
- 本模块只读查看过现有 OneBot/插件接口用于适配，从未修改线上插件文件。

## 测试与验收

```bash
npm test        # node --test
```

- 23 个 Node 内置测试：AC-1~AC-17 核心路径，固定时钟、fake fetch、临时 HTTP 端口、OneBot 事件样例。
- `node --check` 覆盖所有源文件；`node examples/demo.js` 与 `node examples/onebot-demo.js` 可直接运行。
- `package.json` 的 `dependencies` 为空；源码 import 仅 `node:` 内置和项目内文件。
- AC-1~AC-17 的实跑结果与证据见本项目 `WORKLOG.md`。

## 项目结构

```text
src/engine.js    # 决策核心（历史/门控/评分）
src/prompt.js    # buildReplyPrompt
src/onebot.js    # OneBot 11 归一化 / send_group_msg 负载
src/server.js    # HTTP sidecar
src/cli.js       # 环境变量启动、dry-run、生成器加载
examples/        # 无网络 demo
test/            # node:test
```
