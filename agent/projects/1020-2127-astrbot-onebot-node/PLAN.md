# PLAN — group-autochat v0.1

6 条任务，约 8.5 小时；每条 1~2 小时，按顺序做。第一条是能在本地跑起来的最小版本，后续逐步补 OneBot 适配、sidecar、门控和测试。只做 SPEC 3.1 范围内的功能。

- [x] T1（1.5h，MVP）建立 `package.json`（ESM、dependencies 为空）与 `src/engine.js`：实现 `createAutoChat` 的 `observe/decide/recordReply/reset`、每群历史缓冲、基础门控（empty/cold/low-relevance/cooldown/relevant）和配置默认值；写 `examples/demo.js`，用脚本化群消息直接 `node examples/demo.js` 打印决策，确认能跑。
- [x] T2（1h，OneBot 适配）实现 `src/onebot.js`：`normalizeOneBot11` 处理群消息的文本、@ 自己、reply、图片占位、self_id 和私聊过滤；`toSendGroupMsg` 生成带可选 reply 段的 `send_group_msg` 负载；用 3~4 个手写事件做同步冒烟。
- [x] T3（1.5h，HTTP sidecar）实现 `src/server.js` 与 `src/cli.js`：`node:http` 提供 `POST /onebot/event`、`GET /healthz`，支持 webhook token、dry-run、事件去重、`fetch` 调 OneBot HTTP API 的 `send_group_msg`，发送成功后才 `recordReply`；用 fake fetch 和临时端口冒烟。
- [x] T4（1.5h，门控与生成器）补齐 `src/prompt.js` 和高级决策：mention 绕过相关性/防抢话门控（不绕过冷却/静音/上限）、reply-to-other、rapid-exchange、quiet-hours、bot-spoke-last、hourly-cap、历史裁剪/去重、配置校验；定义 `replyGenerator` 契约与 `[[skip]]`/空文本弃权。
- [x] T5（2h，测试）新增 `node:test` 测试：`test/engine.test.js`、`test/onebot.test.js`、`test/server.test.js`，覆盖 AC-1~AC-17 的核心路径（固定时钟、fake fetch、临时 HTTP 端口）；`node --test` 全绿。
- [x] T6（1h，文档与验收）写 `README.md`：Node/OneBot 环境、sidecar 与库内嵌两种接入、OneBot HTTP 配置、生成器示例、环境变量、安全（token/本地绑定）、已知局限、与 AstrBot/现有 `group-wake` 的关系；按 SPEC 第 5 节跑 AC-1~AC-17，把结果写入本项目 `WORKLOG.md`，确认零依赖且未改线上插件。

## 执行说明

- 依赖顺序：T1 → T2 → T3 → T4；T5 跟在前四条之后；T6 最后。T2/T3 不要修改现有插件文件或读取其私有 `ctx`。
- 每条任务完成即自测：T1 跑 demo，T2 用手写事件，T3 用 fake fetch/临时端口，T4 用固定时钟；T5 之后以 `node --test` 为准。
- 时间盒：单条超过 2 小时就收窄到 SPEC 3.1 的最小行为，把扩展记入 v0.2，不拖长。
- v0.2 候选（本次不做）：OneBot 正向 WS 客户端、持久化冷却状态、多群/多账号协调、模型打分、配置热更新、npm 发布。
- 全程零第三方依赖；不修改线上运行的插件/配置，不向真实 QQ 群发测试消息，不做打包发布与覆盖率门禁。
