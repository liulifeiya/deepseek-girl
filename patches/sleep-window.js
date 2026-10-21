/**
 * LOCAL PATCH MODULE (sleep-window): 法定工作日的工作时段「睡觉」，不回复任何消息。
 *
 * 配置：~/.dsh-user/sleep-window.json，改完即时生效（每次判定都重读）。
 * - workdays：星期几算工作日（0=周日 … 6=周六）
 * - ranges：睡眠时段，[开始, 结束)
 * - holidays：法定节假日（"2026-10-01"），这些日期不算工作日
 * - workdayOverrides：调休上班日（"2026-10-11"），这些日期算工作日
 *
 * 纯旁路：配置缺失/损坏时回落到默认值，绝不抛错。
 */
import { readFileSync } from 'node:fs';

const CONFIG_PATH = process.env.SLEEP_WINDOW_CONFIG ?? '/home/ubuntu/.dsh-user/sleep-window.json';

const DEFAULTS = {
    enabled: true,
    workdays: [1, 2, 3, 4, 5],
    ranges: [['09:00', '12:00'], ['14:00', '18:00']],
    holidays: [],
    workdayOverrides: [],
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
        return -1;
    return h * 60 + m;
}

function dateKey(d) {
    return d.getFullYear() + '-'
        + String(d.getMonth() + 1).padStart(2, '0') + '-'
        + String(d.getDate()).padStart(2, '0');
}

/** 当前是否处于「睡眠时段」。 */
export function isSleeping(now = new Date()) {
    try {
        const cfg = readConfig();
        if (cfg.enabled === false)
            return false;
        const today = dateKey(now);
        const holidays = Array.isArray(cfg.holidays) ? cfg.holidays.map(String) : [];
        const overrides = Array.isArray(cfg.workdayOverrides) ? cfg.workdayOverrides.map(String) : [];
        let workday;
        if (holidays.includes(today))
            workday = false;
        else if (overrides.includes(today))
            workday = true;
        else
            workday = (Array.isArray(cfg.workdays) ? cfg.workdays : DEFAULTS.workdays).includes(now.getDay());
        if (!workday)
            return false;
        const cur = now.getHours() * 60 + now.getMinutes();
        const ranges = Array.isArray(cfg.ranges) ? cfg.ranges : DEFAULTS.ranges;
        return ranges.some(([start, end]) => {
            const s = minutesOf(start);
            const e = minutesOf(end);
            return s >= 0 && e >= 0 && cur >= s && cur < e;
        });
    }
    catch {
        return false;
    }
}
