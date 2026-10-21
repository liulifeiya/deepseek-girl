/**
 * LOCAL PATCH MODULE (group-wake): 群聊自主插话。
 *
 * 移植自 AstrBot 生态的两个思路（astrbot_plugin_smart_wake / group_chat）：
 * 群消息先进缓冲并统计热度 → 安静一段时间后跑一次「漏斗」判定
 * （关键词加权抽签 + 兜底概率 + 冷却 + 精力/频率约束）→ 通过才唤起一次
 * 决策回合，由模型自己决定「接一句」还是输出 [[skip]] 保持安静。
 *
 * 设计约束：
 * - 纯旁路：本模块的异常绝不影响原有回复管线。
 * - 无配置侵入：配置放 ~/.dsh-user/group-wake.json，改动即时生效。
 * - 冷却与精力都写在内存里，重启归零（够用）。
 */
import { readFileSync } from 'node:fs';

const CONFIG_PATH = process.env.GROUP_WAKE_CONFIG ?? '/home/ubuntu/.dsh-user/group-wake.json';
const TICK_MS = 15_000;
const BUFFER_MAX = 40;
const HEAT_WINDOW_MS = 5 * 60_000;

const DEFAULTS = {
    enabled: true,
    idleMs: 45_000,          // 群里安静这么久才考虑插话
    cooldownMs: 8 * 60_000,  // 两次主动插话的最小间隔
    minMessages: 3,          // 至少攒够几条新消息才考虑
    fallbackProb: 0.08,      // 关键词没命中时的兜底概率
    maxTurnsPerHour: 4,      // 每小时最多主动几次
    maxMessagesBeforeReset: 60, // 群会话攒够这么多条消息就静默重开（0=关闭）
    quietStart: '23:30',
    quietEnd: '08:00',
    keywords: [
        ['大肥鱼', 6], ['肥鱼', 5], ['欧金金', 6], ['@', 4],
        ['你是不是', 3], ['你会', 2], ['能不能', 2], ['帮我', 2],
        ['为什么', 2], ['怎么办', 2], ['怎么样', 2], ['是谁', 3],
        ['表情包', 4], ['唱歌', 3], ['语音', 3], ['AI', 2], ['机器人', 4],
    ],
};

function readConfig() {
    try {
        const raw = JSON.parse(readFileSync(CONFIG_PATH, 'utf8'));
        return { ...DEFAULTS, ...raw };
    }
    catch {
        return { ...DEFAULTS };
    }
}

function minutesOf(hhmm) {
    const [h, m] = String(hhmm).split(':').map(Number);
    if (!Number.isFinite(h) || !Number.isFinite(m))
        return 0;
    return h * 60 + m;
}

function inQuietHours(config, now) {
    const d = new Date(now);
    const cur = d.getHours() * 60 + d.getMinutes();
    const start = minutesOf(config.quietStart);
    const end = minutesOf(config.quietEnd);
    if (start === end)
        return false;
    return start < end ? cur >= start && cur < end : cur >= start || cur < end;
}

function clockOf(ts) {
    const d = new Date(ts);
    return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}


/** 群成员放行名单（非管理员用）：~/.dsh-user/group-user-allow.json
 *  形如 {"allow": ["1126678256", "3525840251"]}
 *  文件不存在或 allow 为空 = 不启用（所有人都按原规则处理）。 */
const ALLOW_PATH = process.env.GROUP_USER_ALLOW ?? '/home/ubuntu/.dsh-user/group-user-allow.json';

export function readGroupUserAllow(groupId) {
    try {
        const raw = JSON.parse(readFileSync(ALLOW_PATH, 'utf8'));
        // 分群设置优先：groups[群号] = ["QQ", ...]（限定）或 null/[]（该群不设限）
        const groups = raw?.groups;
        if (groups !== null && typeof groups === 'object' && groupId !== undefined && String(groupId) in groups) {
            const list = Array.isArray(groups[String(groupId)]) ? groups[String(groupId)].map(String) : [];
            return list.length > 0 ? list : null;
        }
        const list = Array.isArray(raw?.allow) ? raw.allow.map(String) : [];
        return list.length > 0 ? list : null;
    }
    catch {
        return null;
    }
}

export class GroupWake {
    /** @type {Map<string, object>} chatId → chat state */
    chats = new Map();
    timer;
    lastTickAt = 0;
    replies = [];

    /** Reset everything (tests / manual). */
    reset() {
        this.chats.clear();
        this.replies = [];
    }

    start() {
        if (this.timer !== undefined)
            return;
        this.timer = setInterval(() => {
            try {
                this.tick();
            }
            catch (error) {
                // 纯旁路：永不抛出
                void error;
            }
        }, TICK_MS);
        this.timer.unref?.();
    }

    state(chatId) {
        let chat = this.chats.get(chatId);
        if (chat === undefined) {
            chat = { buffer: [], pending: 0, lastNoteAt: 0, lastDecisionAt: 0, turns: [], lastNickname: '', sinceReset: 0 };
            this.chats.set(chatId, chat);
        }
        return chat;
    }

    /** 记录一条群消息（在 requireMention 门控之前调用，未 @ 的消息也要进来）。 */
    note(ctx, inbound) {
        try {
            const config = readConfig();
            if (!config.enabled)
                return;
            if (inbound.kind !== 'group')
                return;
            const text = String(inbound.text ?? '').trim();
            const media = Array.isArray(inbound.media) ? inbound.media.length : 0;
            if (text === '' && media === 0)
                return;
            if (text.startsWith('/'))
                return; // 命令不进缓冲
            const chat = this.state(inbound.chatId);
            if (this.ctx === undefined)
                this.ctx = ctx;
            chat.buffer.push({
                at: Date.now(),
                nickname: String(inbound.nickname ?? inbound.userId ?? ''),
                userId: String(inbound.userId ?? ''),
                text: text.slice(0, 300),
                media,
            });
            if (chat.buffer.length > BUFFER_MAX)
                chat.buffer.splice(0, chat.buffer.length - BUFFER_MAX);
            chat.pending += 1;
            chat.sinceReset = (chat.sinceReset ?? 0) + 1;
            chat.lastNoteAt = Date.now();
            const resetLimit = Number(config.maxMessagesBeforeReset ?? 60);
            if (resetLimit > 0 && chat.sinceReset >= resetLimit && typeof ctx.resetChatQuiet === 'function') {
                chat.sinceReset = 0;
                Promise.resolve(ctx.resetChatQuiet(inbound.chatId)).then(() => {
                    ctx.log?.('info', 'group-wake 会话过长，已静默重开：' + inbound.chatId);
                }).catch((error) => {
                    ctx.log?.('warn', 'group-wake 静默重开失败: ' + String(error));
                });
            }
            chat.lastNickname = String(inbound.nickname ?? '');
            chat.lastInbound = inbound;
            this.start();
            void ctx;
        }
        catch {
            // 纯旁路
        }
    }

    heat(chat, now) {
        const recent = chat.buffer.filter(item => now - item.at < HEAT_WINDOW_MS);
        const users = new Set(recent.map(item => item.userId));
        return { messages: recent.length, users: users.size };
    }

    keywordScore(text, keywords) {
        let score = 0;
        for (const entry of keywords) {
            const [word, weight] = Array.isArray(entry) ? entry : [String(entry), 2];
            if (word !== '' && text.includes(word))
                score += Number(weight) || 0;
        }
        return score;
    }

    /** 决策回合的提示词：把最近聊天甩给模型，让它自己选接不接。 */
    buildPrompt(chat) {
        const lines = chat.buffer
            .slice(-12)
            .map(item => '[' + clockOf(item.at) + ' ' + item.nickname + '] ' + (item.text === '' ? '[图片/语音]' : item.text));
        return '[群聊快照] 群里最近的消息如下（你不是每条都要回，也没有人专门叫你）：\n'
            + lines.join('\n')
            + '\n\n如果你正好有话想接，就直接说一句自然的短话（1～2 句，别总结、别分析、别解释你在做什么）；'
            + '如果没什么可说的，或者气氛不适合插嘴，就只输出 [[skip]]。';
    }

    tick(now = Date.now()) {
        const config = readConfig();
        if (!config.enabled)
            return;
        if (inQuietHours(config, now))
            return;
        for (const [chatId, chat] of this.chats) {
            try {
                this.maybeWake(chatId, chat, config, now);
            }
            catch (error) {
                void error;
            }
        }
    }

    maybeWake(chatId, chat, config, now) {
        void now;
        if (chat.pending === 0)
            return;
        const ctx = this.ctx;
        if (ctx === undefined)
            return;
        const fresh = Date.now();
        if (fresh - chat.lastNoteAt < config.idleMs)
            return; // 还在聊，先不插
        if (fresh - chat.lastDecisionAt < config.cooldownMs)
            return;
        chat.turns = chat.turns.filter(t => fresh - t < 3_600_000);
        if (chat.turns.length >= config.maxTurnsPerHour)
            return;
        if (chat.pending < config.minMessages)
            return;
        const agent = ctx.getChat?.(chatId);
        if (agent !== undefined && agent.agent?.status === 'running')
            return;
        const heat = this.heat(chat, fresh);
        const joined = chat.buffer.map(item => item.text).join('\n');
        const score = this.keywordScore(joined, config.keywords ?? []);
        const base = score > 0 ? Math.min(0.85, score * 0.1) : config.fallbackProb;
        const heatFactor = heat.messages >= 20 ? 1.2 : heat.messages >= 5 ? 1 : 0.7;
        const prob = Math.max(0.02, Math.min(0.95, base * heatFactor));
        const roll = Math.random();
        chat.lastDecisionAt = fresh;
        const consumed = chat.pending;
        chat.pending = 0;
        if (roll > prob) {
            ctx.log?.('debug', 'group-wake 抽签未过：' + chatId + ' score=' + score + ' prob=' + prob.toFixed(2) + ' roll=' + roll.toFixed(2));
            return;
        }
        chat.turns.push(fresh);
        ctx.log?.('info', 'group-wake 唤起决策回合：' + chatId + '（缓冲 ' + consumed + ' 条，score=' + score + '，prob=' + prob.toFixed(2) + '）');
        const prompt = this.buildPrompt(chat);
        Promise.resolve(ctx.dispatchFollowup?.(chatId, prompt, 'member', chat.lastNickname ?? '')).catch((error) => {
            ctx.log?.('warn', 'group-wake 派发失败: ' + String(error));
        });
    }
}

/** 单例：inbound 管线在门控前调用 note()，bridge 在启动时 attach()。 */
export const groupWake = new GroupWake();

/** bridge 启动时把上下文挂上来（只挂一次）。 */
export function attachGroupWake(ctx) {
    if (groupWake.ctx !== undefined)
        return;
    groupWake.ctx = ctx;
    groupWake.start();
}

/** 供外部观察：当前各群缓冲情况。 */
export function groupWakeSnapshot() {
    return [...groupWake.chats.entries()].map(([chatId, chat]) => ({
        chatId,
        pending: chat.pending,
        buffered: chat.buffer.length,
        lastNoteAt: chat.lastNoteAt,
        lastDecisionAt: chat.lastDecisionAt,
        turnsLastHour: chat.turns.filter(t => Date.now() - t < 3_600_000).length,
    }));
}
