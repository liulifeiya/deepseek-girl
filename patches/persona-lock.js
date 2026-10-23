/**
 * LOCAL PATCH MODULE (persona-lock): 管理员发言时锁定「1 号人格」。
 *
 * dsh-persona 是按会话绑定人设的，同一个群里管理员和其他人共用一套。
 * 这个模块在消息层做覆盖：只要发送者是管理员，就在本条消息里带上 1 号人格，
 * 并要求模型只对这条回复使用它，不影响同群其他人的默认人设。
 */
import { readFileSync } from 'node:fs';

const HOME_DIR = process.env.BOT_HOME || process.env.USERPROFILE || process.env.HOME || process.cwd();
const DSH_HOME = process.env.DSH_HOME || `${HOME_DIR}/.dsh-user`;

const STORE_PATH = process.env.PERSONA_STORE ?? `${DSH_HOME}/storages/dsh-persona-dafeiyu/personas.json`;
const ADMIN_QQ = '2812108776';
const CACHE_MS = 60_000;

let cache = { at: 0, text: '' };

function personaOneText() {
    if (Date.now() - cache.at < CACHE_MS)
        return cache.text;
    try {
        const data = JSON.parse(readFileSync(STORE_PATH, 'utf8'));
        const list = Array.isArray(data.personas) ? data.personas : [];
        const first = list.find(item => /^1[\s.、]/.test(String(item.name ?? '')));
        cache = { at: Date.now(), text: String(first?.text ?? '') };
    }
    catch {
        cache = { at: Date.now(), text: '' };
    }
    return cache.text;
}

/** 管理员的消息才需要；返回空串表示不注入。 */
export function buildPersonaLock(userId) {
    try {
        if (String(userId) !== ADMIN_QQ)
            return '';
        const text = personaOneText();
        if (text === '')
            return '';
        return '<persona_lock>\n'
            + '【身份锁定】本条消息来自主人 2812108776。只针对这一条回复：'
            + '必须用下面这份人格，覆盖本会话的默认人设；回复完这条就恢复原人设，不要影响其他人。\n'
            + text + '\n'
            + '</persona_lock>';
    }
    catch {
        return '';
    }
}
