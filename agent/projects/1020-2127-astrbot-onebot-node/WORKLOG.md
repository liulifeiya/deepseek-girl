2026-10-20 完成 1020-2127-astrbot-onebot-node 立项：SPEC.md 定义 17 条可检验 AC，固定默认沉默、活跃窗口、冷却/每小时上限/静音/防抢话门控与 OneBot HTTP 旁路。
方案：零依赖 Node.js（≥20）核心 + 可注入 replyGenerator + 独立 HTTP sidecar/库内嵌；只读现有 OneBot/group-wake 接口，不改线上插件文件。
PLAN.md 拆 6 条任务约 8.5h，首条为可跑 demo 的决策引擎 MVP；本阶段未写实现，下一步 T1。
2026-10-20 21:37 T1 完成：`package.json`（零依赖）+ `src/engine.js`（observe/decide/recordReply/reset、历史/去重、empty/bot-spoke-last/cold/cooldown/relevance、mention 候选）+ `examples/demo.js`；`node examples/demo.js` 与内联断言通过。
2026-10-20 21:42 T2 完成：`src/onebot.js` 群事件归一化（文本/@自己/reply/媒体占位/self_id/私聊过滤/CQ raw fallback）+ `toSendGroupMsg`；`examples/onebot-demo.js` 4 事件与内联断言通过。
2026-10-20 21:45 T3 完成：`src/server.js` + `src/cli.js`（`POST /onebot/event`、`GET /healthz`、webhook token、dry-run、去重、fetch `send_group_msg`、成功后才 `recordReply`）；fake fetch/临时端口与 CLI→假 OneBot 端到端通过。
2026-10-20 21:50 T4 完成：`src/prompt.js` + 高级门控（quiet-hours/hourly-cap/reply-to-other/rapid-exchange/mention 边界）+ server prompt 与 outbound self 登记；TZ=UTC 门控/边界、prompt、reply-to-self 与 T1~T3 回归通过。
2026-10-20 21:53 T5 完成：`test/{engine,onebot,server}.test.js` 共 23 个 `node:test` 用例，覆盖 AC-1~AC-17 核心路径（固定时钟/fake fetch/临时端口）；`npm test` 与 `node --test` 23/23 全绿。
2026-10-20 21:56 T6 完成：README 全文（环境/sidecar/库内嵌/OneBot HTTP 配置/生成器/环境变量/安全/局限/AstrBot 与 group-wake 关系）；AC-1~AC-17 实跑 17/17 PASS、`node --test` 23/23，CLI dry-run health 通过（`/home/ubuntu/agent/work/t6-autochat-acceptance.txt`）。
2026-10-20 22:00 验收完成：AC-1~AC-17 17/17 PASS，`node --test` 23/23；生成 REPORT.md；加强 AC-10 historyLimit 与 AC-14 recordReply 冷却断言；证据 `/home/ubuntu/agent/work/verify-autochat-tests.txt`、`verify-autochat-acceptance.txt`。
