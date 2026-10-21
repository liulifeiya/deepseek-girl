#!/usr/bin/env python3
"""在 dsh-onebot-qq 新版本上重打本地补丁（幂等）。

用法：python3 apply-onebot-patches.py [插件 lib 目录]
默认路径：~/.dsh-user/profiles/web/node_modules/dsh-onebot-qq/lib

补丁内容：
1. 引用回复：回复文本以 [[quote]] 开头 → 变成 QQ 引用（引用当前会话最近一条入站消息）
2. 分段发送：正文里的 [[split]] → 拆成多条消息依次发
3. 群里不播报「任务运行中，新消息已排队」提示
"""
import os
import re
import sys

DEFAULT_LIB = os.path.expanduser('~/.dsh-user/profiles/web/node_modules/dsh-onebot-qq/lib')
lib = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LIB

PATCHES = {
    'outbound.js': [
        (
            "import { TRACE_REASONS } from './trace.js';\n",
            "import { TRACE_REASONS } from './trace.js';\n"
            "/** LOCAL PATCH (quote-reply): chatId → last inbound message_id. */\n"
            "export const lastInboundIds = new Map();\n",
        ),
        (
            "    sendToChat(chatId, text, options = {}) {\n        return this.enqueue(chatId, async () => {\n            if (!this.ctx.connected()) {",
            "    sendToChat(chatId, text, options = {}) {\n        return this.enqueue(chatId, async () => {\n"
            "            // LOCAL PATCH (quote-reply): strip a leading [[quote]] / [[引用]] marker.\n"
            "            if (/^\\s*\\[\\[(?:quote|引用)\\]\\]/.test(text)) {\n"
            "                text = text.replace(/^\\s*\\[\\[(?:quote|引用)\\]\\]\\s*/, '');\n"
            "                if (options.replyTo === undefined) {\n"
            "                    const lastId = lastInboundIds.get(chatId);\n"
            "                    if (lastId !== undefined)\n"
            "                        options = { ...options, replyTo: lastId };\n"
            "                }\n"
            "            }\n"
            "            if (!this.ctx.connected()) {",
        ),
        (
            "                const plain = stripMarkdown(body);\n                if (plain !== '') {\n"
            "                    const id = await this.sendMsg(chatId, [{ type: 'text', data: { text: plain } }], options);\n"
            "                    if (id !== undefined)\n                        ids.push(id);\n                }",
            "                const plain = stripMarkdown(body);\n                if (plain !== '') {\n"
            "                    // LOCAL PATCH (multi-message): [[split]] sends chunks separately.\n"
            "                    const chunks = plain\n"
            "                        .split(/\\s*\\[\\[(?:split|分段)\\]\\]\\s*/)\n"
            "                        .map(chunk => chunk.trim())\n"
            "                        .filter(chunk => chunk !== '');\n"
            "                    for (let index = 0; index < chunks.length; index += 1) {\n"
            "                        if (index > 0)\n"
            "                            await new Promise(resolve => setTimeout(resolve, 400));\n"
            "                        const chunkOptions = index === 0 ? options : { ...options, replyTo: undefined };\n"
            "                        const id = await this.sendMsg(chatId, [{ type: 'text', data: { text: chunks[index] } }], chunkOptions);\n"
            "                        if (id !== undefined)\n                            ids.push(id);\n"
            "                    }\n                }",
        ),
        (
            "import { describeError } from './errors.js';\n",
            "import { describeError } from './errors.js';\n"
            "/** LOCAL PATCH (auto-split): 按句末标点把一段回复切成 2～3 条。\n"
            " *  含代码块、太长、句子太碎或句子数不在 2～3 之间时原样返回。 */\n"
            "function autoSplitChunks(text) {\n"
            "    if (text.includes('```') || text.length > 200)\n"
            "        return [text];\n"
            "    let parts = text.split(/(?<=[。！？!?])/).map(part => part.trim()).filter(part => part !== '');\n"
            "    if (parts.length < 2)\n"
            "        parts = text.split(/\\n+/).map(part => part.trim()).filter(part => part !== '');\n"
            "    if (parts.length < 2 || parts.length > 3)\n"
            "        return [text];\n"
            "    if (parts.some(part => part.length < 6))\n"
            "        return [text];\n"
            "    return parts;\n"
            "}\n",
        ),
        (
            "                    // LOCAL PATCH (multi-message): [[split]] sends chunks separately.\n"
            "                    const chunks = plain\n"
            "                        .split(/\\s*\\[\\[(?:split|分段)\\]\\]\\s*/)\n"
            "                        .map(chunk => chunk.trim())\n"
            "                        .filter(chunk => chunk !== '');\n",
            "                    // LOCAL PATCH (multi-message): [[split]] sends chunks separately.\n"
            "                    let chunks = plain\n"
            "                        .split(/\\s*\\[\\[(?:split|分段)\\]\\]\\s*/)\n"
            "                        .map(chunk => chunk.trim())\n"
            "                        .filter(chunk => chunk !== '');\n"
            "                    // LOCAL PATCH (auto-split): 没有手动标记时按句子自动分段。\n"
            "                    if (chunks.length === 1)\n"
            "                        chunks = autoSplitChunks(plain);\n",
        ),
        (
            "                    // LOCAL PATCH (auto-split): 没有手动标记时按句子自动分段。\n"
            "                    if (chunks.length === 1)\n"
            "                        chunks = autoSplitChunks(plain);\n",
            "                    // LOCAL PATCH (auto-split): 没有手动标记时按句子自动分段。\n"
            "                    if (chunks.length === 1)\n"
            "                        chunks = autoSplitChunks(plain);\n"
            "                    // LOCAL PATCH (auto-split): 单轮最多 3 条，多出来的并进第 3 条。\n"
            "                    if (chunks.length > 3) {\n"
            "                        const head = chunks.slice(0, 2);\n"
            "                        head.push(chunks.slice(2).join(''));\n"
            "                        chunks = head;\n"
            "                    }\n",
        ),
    ],
    'inbound.js': [
        (
            "import { currentTrace, TRACE_REASONS } from './trace.js';\n",
            "import { currentTrace, TRACE_REASONS } from './trace.js';\n"
            "// LOCAL PATCH (quote-reply): record inbound message ids for [[quote]].\n"
            "import { lastInboundIds } from './outbound.js';\n",
        ),
        (
            "        const plain = inbound.media.length === 0 && inbound.replyId === undefined && inbound.forwardId === undefined;\n",
            "        const plain = inbound.media.length === 0 && inbound.replyId === undefined && inbound.forwardId === undefined;\n"
            "        // LOCAL PATCH (quote-reply)\n"
            "        if (inbound.messageId !== undefined)\n"
            "            lastInboundIds.set(chatId, inbound.messageId);\n",
        ),
    ],
    'bridge.js': [
        (
            "        if (!this.queueNoticeChats.has(chatId)) {\n"
            "            this.queueNoticeChats.add(chatId);\n"
            "            this.sendToChat(chatId, QUEUE_NOTICE_TEXT).catch((error) => {\n"
            "                this.deps.log('debug', '排队提示发送失败: ' + describeError(error));\n"
            "                currentTrace()?.emit('notice', { ok: false, reason: '排队提示发送失败: ' + describeError(error) });\n"
            "            });\n"
            "        }",
            "        if (!this.queueNoticeChats.has(chatId)) {\n"
            "            this.queueNoticeChats.add(chatId);\n"
            "            // LOCAL PATCH (quiet groups): 群里不播报排队提示\n"
            "            if (!chatId.startsWith('group:')) {\n"
            "                this.sendToChat(chatId, QUEUE_NOTICE_TEXT).catch((error) => {\n"
            "                    this.deps.log('debug', '排队提示发送失败: ' + describeError(error));\n"
            "                    currentTrace()?.emit('notice', { ok: false, reason: '排队提示发送失败: ' + describeError(error) });\n"
            "                });\n"
            "            }\n"
            "        }",
        ),
    ],
}


GROUP_WAKE_MARKER = '// LOCAL PATCH (group-wake)'

def patch_group_wake(lib):
    """复制 group-wake.js，并在 inbound/outbound 挂上：缓冲、成员白名单、[[skip]]。"""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'group-wake.js')
    dst = os.path.join(lib, 'group-wake.js')
    if os.path.exists(src):
        with open(src) as f:
            body = f.read()
        with open(dst, 'w') as f:
            f.write(body)
        print('group-wake.js: copied')

    def apply(name, old, new, marker):
        path = os.path.join(lib, name)
        with open(path) as f:
            text = f.read()
        if marker in text:
            return
        if old not in text:
            print('WARN: group-wake anchor missing in ' + name)
            return
        with open(path, 'w') as f:
            f.write(text.replace(old, new, 1))
        print(name + ': group-wake hook applied')

    apply('inbound.js',
          "import { lastInboundIds } from './outbound.js';\n",
          "import { lastInboundIds } from './outbound.js';\n"
          "// LOCAL PATCH (group-wake)\n"
          "import { groupWake, readGroupUserAllow } from './group-wake.js';\n",
          "readGroupUserAllow } from './group-wake.js'")

    mention_anchor = ("        const mentioned = detectMention(inbound.segments, inbound.raw, "
                      "this.ctx.selfId(), this.ctx.config.botQQ);\n")
    apply('inbound.js',
          mention_anchor,
          mention_anchor
          + "        // LOCAL PATCH (group-wake): 未 @ 的群消息也要进缓冲\n"
          + "        if (kind === 'group') {\n"
          + "            try {\n"
          + "                groupWake.note(this.ctx, { ...inbound, mentioned });\n"
          + "            }\n"
          + "            catch {\n"
          + "            }\n"
          + "        }\n"
          + "        // LOCAL PATCH (group user allowlist): 群里只理管理员和指定成员\n"
          + "        if (kind === 'group') {\n"
          + "            try {\n"
          + "                const allow = readGroupUserAllow(groupId);\n"
          + "                if (allow !== null) {\n"
          + "                    const isAdmin = classifyUserRole(userId, this.ctx.policy.adminUsers) === 'admin';\n"
          + "                    if (!isAdmin && !allow.includes(userId)) {\n"
          + "                        this.ctx.log('debug', 'group user not allowlisted: ' + userId);\n"
          + "                        return;\n"
          + "                    }\n"
          + "                }\n"
          + "            }\n"
          + "            catch {\n"
          + "            }\n"
          + "        }\n",
          "group user not allowlisted")

    apply('bridge.js',
          "            sendToChat: (chatId, text) => this.sendToChat(chatId, text),\n",
          "            sendToChat: (chatId, text) => this.sendToChat(chatId, text),\n"
          "            // LOCAL PATCH (group-wake): 静默重开会话\n"
          "            resetChatQuiet: chatId => this.registry.resetChat(chatId),\n",
          "resetChatQuiet")

    apply('outbound.js',
          "            if (!this.ctx.connected()) {\n",
          "            // LOCAL PATCH (group-wake): [[skip]] = 决定不说话\n"
          "            if (/^\\s*\\[\\[(?:skip|静默)\\]\\]\\s*$/.test(text))\n"
          "                return [];\n"
          "            if (!this.ctx.connected()) {\n",
          "[[skip]]")

PERSONA_MARKER = 'LOCAL PATCH (persona)'


def patch_persona(lib):
    """在 commands.js 里加 /persona 命令（本会话切换人设）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(here, 'persona-command.js')
    if not os.path.exists(src_path):
        print('WARN: persona-command.js missing')
        return
    with open(src_path) as f:
        body = f.read()
    path = os.path.join(lib, 'commands.js')
    with open(path) as f:
        text = f.read()
    if PERSONA_MARKER in text:
        print('commands.js: persona already patched')
        return
    goal = ("    { name: 'goal', adminOnly: true, group: '其他', help: '[目标|clear] 目标记录', "
            "handler: (ctx, chatId, arg) => handleGoalCommand(ctx, chatId, arg) },\n")
    row = ("    { name: 'persona', adminOnly: true, group: '会话', help: '[编号|名字|global] 本会话用人设（global=跟随全局）', "
           "handler: (ctx, chatId, arg) => handlePersonaCommand(ctx, chatId, arg) },\n")
    ver = '/** /ver: plugin version + git commit (each read once and cached). */\n'
    if goal not in text or ver not in text:
        print('WARN: commands.js anchors missing')
        return
    text = text.replace(goal, goal + row, 1).replace(ver, body + ver, 1)
    with open(path, 'w') as f:
        f.write(text)
    print('commands.js: persona command applied')


MENTION_MARKER = 'LOCAL PATCH (mention-context)'


def patch_mention_context(lib):
    """复制 mention-context.js，并在 inbound 里挂上「@ 时带上下文」。"""
    here = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(here, 'mention-context.js')
    if not os.path.exists(src_path):
        print('WARN: mention-context.js missing')
        return
    with open(src_path) as f:
        body = f.read()
    with open(os.path.join(lib, 'mention-context.js'), 'w') as f:
        f.write(body)
    print('mention-context.js: copied')

    def apply(name, old, new, marker=None):
        path = os.path.join(lib, name)
        with open(path) as f:
            text = f.read()
        if marker is not None and marker in text:
            return
        if new in text:
            return
        if old not in text:
            print('WARN: mention anchor missing in ' + name)
            return
        with open(path, 'w') as f:
            f.write(text.replace(old, new, 1))
        print(name + ': mention-context hook applied')

    apply('inbound.js',
          "import { groupWake, readGroupUserAllow } from './group-wake.js';\n",
          "import { groupWake, readGroupUserAllow } from './group-wake.js';\n"
          "// LOCAL PATCH (mention-context): @ 时才取用的群聊上下文\n"
          "import { buildMentionContext, recordGroupMessage } from './mention-context.js';\n")

    gw = ("        // LOCAL PATCH (group-wake): 未 @ 的群消息也要进缓冲\n"
          "        if (kind === 'group') {\n"
          "            try {\n"
          "                groupWake.note(this.ctx, { ...inbound, mentioned });\n"
          "            }\n"
          "            catch {\n"
          "                // 纯旁路\n"
          "            }\n"
          "        }\n")
    apply('inbound.js', gw,
          gw + "        // LOCAL PATCH (mention-context): 所有群消息进上下文缓冲，@ 时才取用\n"
          "        if (kind === 'group') {\n"
          "            try {\n"
          "                recordGroupMessage(inbound);\n"
          "            }\n"
          "            catch {\n"
          "                // 纯旁路\n"
          "            }\n"
          "        }\n")

    final = ("        let final = wrapUserMessage(content, userId, nickname);\n"
             "        if (kind === 'group') {\n"
             "            final = buildGroupMessagePrefix(nickname, userId, mentioned) + final;\n")
    apply('inbound.js', final,
          "        let final = wrapUserMessage(content, userId, nickname);\n"
          "        if (kind === 'group') {\n"
          "            // LOCAL PATCH (mention-context): @ 时把最近相关的群聊带上\n"
          "            if (mentioned) {\n"
          "                const groupContext = buildMentionContext(chatId, userId, nickname);\n"
          "                if (groupContext !== '')\n"
          "                    final = groupContext + '\\n' + final;\n"
          "            }\n"
          "            final = buildGroupMessagePrefix(nickname, userId, mentioned) + final;\n",
          'LOCAL PATCH (mention-context): @ 时把最近相关的群聊带上')


def patch_sleep_window(lib):
    """复制 sleep-window.js，并在 inbound 里挂上「法定工作日工作时段不回复」。"""
    here = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(here, 'sleep-window.js')
    if not os.path.exists(src_path):
        print('WARN: sleep-window.js missing')
        return
    with open(src_path) as f:
        body = f.read()
    with open(os.path.join(lib, 'sleep-window.js'), 'w') as f:
        f.write(body)
    print('sleep-window.js: copied')

    def apply(name, old, new):
        path = os.path.join(lib, name)
        with open(path) as f:
            text = f.read()
        if new in text:
            return
        if old not in text:
            print('WARN: sleep anchor missing in ' + name)
            return
        with open(path, 'w') as f:
            f.write(text.replace(old, new, 1))
        print(name + ': sleep-window hook applied')

    apply('inbound.js',
          "import { buildMentionContext, recordGroupMessage } from './mention-context.js';\n",
          "import { buildMentionContext, recordGroupMessage } from './mention-context.js';\n"
          "// LOCAL PATCH (sleep-window): 法定工作日工作时段不回复\n"
          "import { isSleeping } from './sleep-window.js';\n")

    apply('inbound.js',
          "        const mentioned = detectMention(inbound.segments, inbound.raw, this.ctx.selfId(), this.ctx.config.botQQ);\n",
          "        // LOCAL PATCH (sleep-window): 法定工作日工作时段睡觉，任何消息都不回\n"
          "        if (isSleeping()) {\n"
          "            this.ctx.log('debug', 'sleep window, ignoring message in ' + chatId);\n"
          "            return;\n"
          "        }\n"
          "        const mentioned = detectMention(inbound.segments, inbound.raw, this.ctx.selfId(), this.ctx.config.botQQ);\n")


def patch_persona_lock(lib):
    """复制 persona-lock.js，并在 inbound 里挂上「管理员锁定 1 号人格」。"""
    here = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(here, 'persona-lock.js')
    if not os.path.exists(src_path):
        print('WARN: persona-lock.js missing')
        return
    with open(src_path) as f:
        body = f.read()
    with open(os.path.join(lib, 'persona-lock.js'), 'w') as f:
        f.write(body)
    print('persona-lock.js: copied')

    def apply(name, old, new):
        path = os.path.join(lib, name)
        with open(path) as f:
            text = f.read()
        if new in text:
            return
        if old not in text:
            print('WARN: persona-lock anchor missing in ' + name)
            return
        with open(path, 'w') as f:
            f.write(text.replace(old, new, 1))
        print(name + ': persona-lock hook applied')

    apply('inbound.js',
          "import { isSleeping } from './sleep-window.js';\n",
          "import { isSleeping } from './sleep-window.js';\n"
          "// LOCAL PATCH (persona-lock): 管理员发言锁定 1 号人格\n"
          "import { buildPersonaLock } from './persona-lock.js';\n")

    apply('inbound.js',
          "        let final = wrapUserMessage(content, userId, nickname);\n"
          "        if (kind === 'group') {\n"
          "            // LOCAL PATCH (mention-context): @ 时把最近相关的群聊带上\n",
          "        let final = wrapUserMessage(content, userId, nickname);\n"
          "        if (kind === 'group') {\n"
          "            // LOCAL PATCH (persona-lock): 管理员的消息强制用 1 号人格\n"
          "            const personaLock = buildPersonaLock(userId);\n"
          "            if (personaLock !== '')\n"
          "                final = personaLock + '\\n' + final;\n"
          "            // LOCAL PATCH (mention-context): @ 时把最近相关的群聊带上\n")


patch_persona(lib)

for name, pairs in PATCHES.items():
    path = os.path.join(lib, name)
    with open(path) as f:
        src = f.read()
    changed = 0
    for old, new in pairs:
        if new in src:
            continue
        if old not in src:
            # 锚点因已有补丁而位移时，按补丁标记判断是否已打过，避免误报。
            found = re.search(r'LOCAL PATCH \(([^)]+)\)', new)
            if found and ('LOCAL PATCH (' + found.group(1)) in src:
                continue
            print('WARN: pattern missing in ' + name + ': ' + old.splitlines()[0][:60])
            continue
        src = src.replace(old, new, 1)
        changed += 1
    if changed:
        with open(path, 'w') as f:
            f.write(src)
    print(name + ': ' + str(changed) + ' patch(es) applied')

# group-wake 依赖 quote 补丁先插好 inbound 的 import，所以放在最后。
patch_group_wake(lib)
patch_mention_context(lib)
patch_sleep_window(lib)
patch_persona_lock(lib)
