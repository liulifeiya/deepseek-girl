# deepseek-girl

一个跑在 [DeepSeek Harness](https://github.com/deepseek-ai)（下称 DSH）上的 AI 人格所依赖的 **profile 快照**：装了哪些插件、配置怎么写的、有哪些技能。

不是框架，不是插件源码的原创仓库 —— 这里绝大多数代码是别人的。这个仓库的价值只有一个：**一台真在跑、天天跟人聊天的机器，它的配置长什么样。**

## 目录

```
profile/
  cordis.yml            profile 根（空列表，真正的配置都在 patch 里）
  cordis.patch.yml      主配置：默认模型、UI、权限预设、QQ 桥接的 MCP 服务
  package.json          依赖清单（plugin 从哪来、版本锁在哪）
  pnpm-lock.yaml        完整依赖锁
  pnpm-workspace.yaml
plugins/
  dsh-mood/             心情系统：34 种心情、每日日记、跨会话硬盘记忆、品味库
  dsh-memes-reply/      蓝色大肥鱼表情包回复
  dsh-plugin-android-use/  adb 操作安卓手机（截图、点按、滑动、输入）
  qq-agent-presets/     QQ 侧 agent 预设（qq-chat / qq-chat-v2）
  qq-mode-console/      QQ 桥接的模式控制台
skills/
  yinchao-ai-music/     音潮 AI 音乐生成技能
```

## 插件一览

| 插件 | 版本 | 许可 | 上游 |
|---|---|---|---|
| dsh-mood | 0.14.15 | MIT | [JMX-4869/dsh-mood](https://github.com/JMX-4869/dsh-mood) |
| dsh-memes-reply | 0.1.4 | BSD-3-Clause | [liceses/dsh-memes-reply](https://github.com/liceses/dsh-memes-reply) |
| @huanlin/dsh-plugin-android-use | 0.4.2 | AGPL-3.0 | [HuanLinOTO/dsh-plugin-android-use](https://github.com/HuanLinOTO/dsh-plugin-android-use) |
| qq-agent-presets | 0.2.1-r1 | MIT | [Derpyu520/qq-bridge](https://github.com/Derpyu520/qq-bridge) |
| qq-mode-console | 0.2.1-r1 | MIT | [Derpyu520/qq-bridge](https://github.com/Derpyu520/qq-bridge) |

每个插件目录里都保留了它自己的 `LICENSE` / `package.json`，版权归各自作者。这个仓库只是把它们按「某台机器上实际装的样子」摆在一起，方便看和复原。

## 这份配置在干什么

- **模型**：`deepseek-account / deepseek-flash`，`reasoningEffort: max`
- **权限**：默认 `danger-full-access`（本机自用，图省事；你要抄的话建议从 `workspace-write` 起步）
- **QQ 桥接**：三个 MCP 服务（`snowluma`、`snowluma-host`、`web-search-safe`）指向 qq-bridge 的 stdio 入口，让 agent 能收发 QQ 消息、看图片、搜网
- **心情系统**：`dsh-mood` 把当前心情注入提示词，附带每日 23:59 自动生成的日记、可检索的硬盘记忆、以及一个跨会话的品味库

## 怎么用

```bash
mkdir -p ~/.dsh/profiles/myprofile
cp -r profile/* ~/.dsh/profiles/myprofile/
cp -r plugins/* ~/.dsh/profiles/myprofile/node_modules/   # 或按 package.json 用 pnpm 装
```

然后把 `profile/cordis.patch.yml` 里两处占位符换成你自己的路径：

- `<NODE_EXE>` → DSH 自带的 node 可执行文件
- `<QQ_BRIDGE_DIR>` → qq-bridge 的部署目录

## 脱敏说明

这个仓库**是公开的**，所以发布前清掉了全部本机信息：

- 所有绝对路径 → 占位符
- **没有任何 token、API key、密码、QQ 号、服务器地址**
- 会话记录、日记、记忆、品味库一个都没放进来（它们在私有仓库 `deepseek-girl-Memory` 里）

如果你照抄这份配置，记得别把原来的凭据一起抄进来。
