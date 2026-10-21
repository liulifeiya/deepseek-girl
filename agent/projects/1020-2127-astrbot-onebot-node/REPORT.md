# REPORT — group-autochat v0.1 验收

- 项目：`/home/ubuntu/agent/projects/1020-2127-astrbot-onebot-node`
- 验收时间：2026-10-20 22:00
- 环境：Linux，Node.js v24.19.0，零第三方依赖
- 结论：**AC-1~AC-17 全部通过（17/17）**；`node --test` **23/23 通过**；README/CLI/零依赖检查通过
- 本次验收未修改功能代码或 README；仅新增本报告，并加强了 AC-10（historyLimit）与 AC-14（recordReply 后冷却）的测试断言

## 一、逐条验收

| AC | 结果 | 证据 |
| --- | --- | --- |
| AC-1 | 通过 | `AC-1 empty group and cold window are silent`：空群 `silent/empty`；6 分钟前的关键词消息 `silent/cold` |
| AC-2 | 通过 | `AC-2 unrelated active chatter is low relevance`：活跃但无关消息 `silent/low-relevance`，score < 0.55 |
| AC-3 | 通过 | `AC-3 relevant active topic replies...`：关键词 + 问句 → `reply/relevant`，score ≥ 0.55，`replyToMessageId`/context 正确 |
| AC-4 | 通过 | `AC-4 cooldown, bot-spoke-last, and recovery`：`recordReply` 后冷却内 `cooldown`；最后一条是自己 `bot-spoke-last`；冷却结束人类再发言恢复 `reply` |
| AC-5 | 通过 | `AC-5 hourly cap...`：`maxPerHour=2` 时第 3 次 `hourly-cap`；61 分钟后恢复 |
| AC-6 | 通过 | `AC-6 mention replies...`：@ 无关键词可 `mentioned`；静音/冷却仍拦截 |
| AC-7 | 通过 | `AC-7 rapid two-user exchange...`：20 秒内 3 条人类消息、≥2 人 → `rapid-exchange`；最后 @ 机器人 → `mentioned` |
| AC-8 | 通过 | `AC-8 reply-to-other...`：回复其他人类 `reply-to-other`；回复已知机器人消息允许评分；sidecar 发送后登记 outbound `message_id`，端到端回复机器人消息通过 |
| AC-9 | 通过 | `AC-9 quiet hours...`：23:45、跨午夜 07:00 静音；08:00 结束边界恢复；12:00 不拦截 |
| AC-10 | 通过 | `AC-10 history limit...`：8 条消息只保留最近 5 条（contextLimit=50 时 context 仍为 5）；contextLimit=3 时 context 为 3；重复 messageId 的 `observe` 返回 false |
| AC-11 | 通过 | `AC-11 invalid config...`：`maxPerHour=0`、`cooldownMs=-1` 抛 RangeError，非法静音时间抛 TypeError；`reset` 后回到 `empty` |
| AC-12 | 通过 | 4 个 OneBot 测试：群消息文本/@自己/reply/图片语音占位、私聊/非消息/缺字段/纯 @ 返回 null、self/昵称/时间回退、CQ raw fallback、@all 不算 @ 自己 |
| AC-13 | 通过 | `AC-13 builds send_group_msg...`：`send_group_msg`、`group_id`、文本段、reply 段顺序/类型正确；非法参数抛错 |
| AC-14 | 通过 | `AC-14 HTTP sidecar...`：临时端口 POST 204，fake fetch 收到一次 `send_group_msg`，重复事件不重发，发送后新消息在 cooldown 内不再发送（证明 `recordReply` 生效），`/healthz` 200 |
| AC-15 | 通过 | `AC-15 webhook token...` 与 `AC-15 send failure...`：无/错 token 401，坏 JSON 400，私聊 204 不发送；OneBot 发送失败不记录 cooldown，后续成功可发送；dry-run 不调用生成器/fetch |
| AC-16 | 通过 | `AC-16 zero runtime dependencies...`：`package.json` dependencies 为空；源码 import 仅 `node:`/项目内；`node --test` 23/23；两个 demo 退出 0；`node --check` 全部通过 |
| AC-17 | 通过 | `AC-17 buildReplyPrompt...` 与 `AC-17 [[skip]]/empty...`：prompt 含上下文、回复目标、1–2 句约束、`[[skip]]`；skip/空/null 不发送、不记录 |

## 二、怎么用

### 环境

- Node.js ≥ 20（本机 v24.19）
- 无需 `npm install`，零第三方依赖
- OneBot 11 需要启用 HTTP 事件上报和 HTTP API

### 快速验证

```bash
node examples/demo.js
node examples/onebot-demo.js
npm test
```

### HTTP sidecar（推荐给 Python/NoneBot/AstrBot）

先 dry-run：

```bash
AUTOCHAT_DRY_RUN=1 AUTOCHAT_PORT=8787 node src/cli.js
```

正式运行：

```bash
ONEBOT_API_BASE=http://127.0.0.1:3000 \
ONEBOT_SELF_ID=10001 \
AUTOCHAT_REPLY_MODULE=./my-reply.js \
AUTOCHAT_WEBHOOK_TOKEN=your-webhook-token \
AUTOCHAT_PORT=8787 \
node src/cli.js
```

OneBot 侧把群消息 HTTP 事件 POST 到 `http://127.0.0.1:8787/onebot/event`；HTTP API 指向 `ONEBOT_API_BASE`。生成器模块导出：

```js
export async function generateReply({ decision, prompt, groupId, context }) {
  return await callYourModel(prompt); // 或固定话术；null/''/'[[skip]]' 表示不发言
}
```

### 库内嵌（Node 宿主）

```js
import { createAutoChat, buildReplyPrompt } from './src/engine.js';
const engine = createAutoChat({ interestKeywords: ['AI', '游戏'] });
engine.observe(message);
const decision = engine.decide(message.groupId);
if (decision.action === 'reply') {
  const text = await myModel(buildReplyPrompt(decision));
  if (text && text !== '[[skip]]') {
    await sendGroupMessage(text, decision.replyToMessageId);
    engine.recordReply(message.groupId);
  }
}
```

完整配置、OneBot 配置、安全与局限见 `README.md`。

## 三、已知没做的部分

以下是 SPEC 3.2 / README 明确排除或 v0.1 的已知局限，不计为验收失败：

- v0.1 只支持 OneBot 11 **HTTP** 事件/API；不支持反向/正向 WebSocket 客户端；只开 WS 的部署需在 OneBot 侧启用 HTTP，或等 v0.2。
- 不内置 LLM：`generateReply` 由宿主提供；sidecar 会等待生成器，建议生成器自行设置超时/快速失败。
- 状态只在内存：重启后历史、冷却、每小时计数归零，不保证重启期间不重复。
- 文本为主：图片/语音/视频只做占位符，不做内容理解。
- 不做冷场主动发言、随机兜底、多账号、跨平台、跨群聚合、Web UI、数据库、npm 发布。
- 性能按每群最近 40 条消息设计，不承诺超大群/超高吞吐。
- 与 AstrBot 只是思路参考，不是 AstrBot 插件，不保证行为完全一致。
- 现有 `group-wake` 补丁不能与本模块同时开启自主接话，否则可能重复发言；本模块不自动停用/修改它。
- Windows 未实测。

## 四、验收过程与证据

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| `node --test` | 23 tests / 23 pass / 0 fail | `/home/ubuntu/agent/work/verify-autochat-tests.txt` |
| AC 映射 | AC-1~AC-17 全部出现且 PASS | 测试名称逐条含 `AC-n`，无缺失 |
| 语法检查 | 所有 `src/`、`examples/`、`test/` JS 通过 `node --check` | 验收命令输出 |
| demo | `node examples/demo.js`、`node examples/onebot-demo.js` 均退出 0 | `/home/ubuntu/agent/work/verify-autochat-demo.txt`、`verify-autochat-onebot-demo.txt` |
| README 必备章节 | 环境/两种接入/OneBot HTTP/生成器/环境变量/安全/局限/AstrBot 与 group-wake 均存在 | `/home/ubuntu/agent/work/verify-autochat-acceptance.txt` |
| 零依赖/隔离 | dependencies 为空；源码 import 仅 `node:`/项目内；源码不含内部插件路径 | 同上 |
| CLI dry-run | 启动、`/healthz`、SIGTERM 退出 0 | 同上 |
| CLI 端到端 | 假 OneBot API + 临时生成器：收到 `send_group_msg`，prompt 含 `[[skip]]`，退出 0 | 同上 |
| recordReply | 发送成功后第二次相关事件进入 cooldown，不重复发送 | AC-14 测试 PASS |

本次验收未改动功能代码或 README；新增 `REPORT.md`，并加强了 AC-10（historyLimit）与 AC-14（recordReply 后冷却）的测试断言。

## 五、结论

在 Node.js v24.19.0、零第三方依赖下，SPEC 的 AC-1~AC-17 全部实测通过，`node --test` 23/23 通过；README 覆盖环境、两种接入、OneBot HTTP 配置、生成器、配置、安全、已知局限和 AstrBot/group-wake 关系。v0.1 达到 SPEC 的完成定义，无阻塞。
