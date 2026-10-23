#!/usr/bin/env python3
"""给 @momojie-s/dsh-archive-retention 打本地补丁（幂等）。

用法: python patch-archive-retention.py [插件目录]
默认: %USERPROFILE%\\.dsh-qq\\profiles\\qq\\node_modules\\@momojie-s\\dsh-archive-retention

修复的缺陷：
1. 会话文件名写死 session.jsonl.zstd —— 实际是 session.v4.jsonl.zstd，
   导致「删除前静止检查」看不到文件、孤儿清理永远读不到 parentSession。
2. 没有演练模式（dryRun）：只能真删。
3. 清单只在 deleted > 0 时写，失败详情只进内存。
4. sweepCron 非法时静默永不触发。
5. lastSweepAt 只在内存，频繁重启会错过每日清扫。
6. 无跨进程锁，两个 DSH 实例共享一个 HOME 时会并发清扫。
"""
import os
import sys
from pathlib import Path

MARKER = 'LOCAL PATCH (retention-fix)'

DEFAULT_PLUGIN = Path.home() / '.dsh-qq' / 'profiles' / 'qq' / 'node_modules' / '@momojie-s' / 'dsh-archive-retention'

plugin = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PLUGIN
target = plugin / 'lib' / 'index.js'
if not target.exists():
    print('WARN: plugin not found, skip:', target)
    sys.exit(0)

src = target.read_text(encoding='utf-8')
if MARKER in src:
    print('archive-retention: already patched')
    sys.exit(0)

REPLACEMENTS = []


def rep(old, new):
    REPLACEMENTS.append((old, new))


# ---------------------------------------------------------------- 1. 文件名兼容
rep(
    "import { existsSync, readFileSync } from 'node:fs';",
    "import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';",
)

rep(
    "/** Re-check the artifact right before acting; false when it moved or got rewritten. */\nasync function stillQuiescent(dir, plannedLastWriteMs) {",
    """// LOCAL PATCH (retention-fix): 会话文件名带版本（session.v4.jsonl.zstd），不能写死
async function latestArtifact(dir) {
    try {
        let best;
        for (const name of await readdir(dir)) {
            if (!/^session.*\\.jsonl\\.zstd$/.test(name))
                continue;
            const full = join(dir, name);
            const info = await stat(full);
            if (best === undefined || info.mtimeMs > best.mtimeMs)
                best = { path: full, mtimeMs: info.mtimeMs };
        }
        return best;
    }
    catch {
        return undefined;
    }
}
function latestArtifactSync(dir) {
    try {
        let best;
        for (const name of readdirSync(dir)) {
            if (!/^session.*\\.jsonl\\.zstd$/.test(name))
                continue;
            const full = join(dir, name);
            const info = statSync(full);
            if (best === undefined || info.mtimeMs > best.mtimeMs)
                best = { path: full, mtimeMs: info.mtimeMs };
        }
        return best?.path;
    }
    catch {
        return undefined;
    }
}
/** Re-check the artifact right before acting; false when it moved or got rewritten. */
async function stillQuiescent(dir, plannedLastWriteMs) {""",
)

rep(
    """        const artifact = join(dir, 'session.jsonl.zstd');
        if (existsSync(artifact)) {
            const art = await stat(artifact);
            if (plannedLastWriteMs !== undefined && art.mtimeMs > plannedLastWriteMs)
                return false;
        }""",
    """        const artifact = await latestArtifact(dir);
        if (artifact !== undefined && plannedLastWriteMs !== undefined && artifact.mtimeMs > plannedLastWriteMs)
            return false;""",
)

rep(
    """        const artifact = join(dir, 'session.jsonl.zstd');
        if (!existsSync(artifact))
            return undefined;
        const firstLine = zstdDecompressSync(readFileSync(artifact)).toString('utf8').split('\\n')[0];""",
    """        const artifact = latestArtifactSync(dir);
        if (artifact === undefined)
            return undefined;
        const firstLine = zstdDecompressSync(readFileSync(artifact)).toString('utf8').split('\\n')[0];""",
)

# ---------------------------------------------------------------- 2. dryRun
rep(
    "    enabled: z.boolean().default(true).volatile(),\n    retentionValue:",
    "    enabled: z.boolean().default(true).volatile(),\n    // LOCAL PATCH (retention-fix): 演练模式，只写清单不删\n    dryRun: z.boolean().default(false).volatile(),\n    retentionValue:",
)
rep(
    "        enabled: c.enabled ?? true,\n        retentionValue: c.retentionValue ?? 7,",
    "        enabled: c.enabled ?? true,\n        dryRun: c.dryRun ?? false,\n        retentionValue: c.retentionValue ?? 7,",
)
rep(
    "        enabled: config.enabled.get(),\n        retentionValue: config.retentionValue.get(),",
    "        enabled: config.enabled.get(),\n        dryRun: config.dryRun.get(),\n        retentionValue: config.retentionValue.get(),",
)

# ---------------------------------------------------------------- 3. 清单与计数
rep(
    """            enabled: false, scannedArchiveDir: 0, scannedGuiArchived: 0, scannedOrphans: 0, deleted: 0,
            freedBytes: 0, failures: 0, failureDetails: [], skippedAttached: 0, manifestPath: null,""",
    """            enabled: false, dryRun: false, scannedArchiveDir: 0, scannedGuiArchived: 0, scannedOrphans: 0, deleted: 0,
            wouldDelete: 0, freedBytes: 0, failures: 0, failureDetails: [], skippedAttached: 0, manifestPath: null,""",
)
rep(
    """        const cfg = withDefaults(current());
        if (!cfg.enabled)
            return outcome;""",
    """        const cfg = withDefaults(current());
        outcome.dryRun = cfg.dryRun;
        if (!cfg.enabled)
            return outcome;""",
)
rep(
    """                    try {
                        await rm(dir, { recursive: true, force: true });
                        outcome.deleted += 1;
                        outcome.freedBytes += probe.sizeBytes;
                        deletedList.push({ id, from: join('sessions-archive', ws), sizeBytes: probe.sizeBytes });
                    }""",
    """                    try {
                        if (cfg.dryRun) {
                            outcome.wouldDelete += 1;
                            deletedList.push({ id, from: join('sessions-archive', ws), sizeBytes: probe.sizeBytes, dryRun: true });
                            continue;
                        }
                        await rm(dir, { recursive: true, force: true });
                        outcome.deleted += 1;
                        outcome.freedBytes += probe.sizeBytes;
                        deletedList.push({ id, from: join('sessions-archive', ws), sizeBytes: probe.sizeBytes });
                    }""",
)
rep(
    """                try {
                    await rm(located.dir, { recursive: true, force: true });
                    outcome.deleted += 1;
                    outcome.freedBytes += located.probe.sizeBytes;
                    deletedList.push({ id, from: 'sessions', sizeBytes: located.probe.sizeBytes });
                }""",
    """                try {
                    if (cfg.dryRun) {
                        outcome.wouldDelete += 1;
                        deletedList.push({ id, from: 'sessions', sizeBytes: located.probe.sizeBytes, dryRun: true });
                        continue;
                    }
                    await rm(located.dir, { recursive: true, force: true });
                    outcome.deleted += 1;
                    outcome.freedBytes += located.probe.sizeBytes;
                    deletedList.push({ id, from: 'sessions', sizeBytes: located.probe.sizeBytes });
                }""",
)
rep(
    """                try {
                    await rm(entry.path, { recursive: true, force: true });
                    outcome.deleted += 1;
                    outcome.freedBytes += probe.sizeBytes;
                    deletedList.push({ id: entry.name, from: join('sessions', entry.ws), sizeBytes: probe.sizeBytes });
                }""",
    """                try {
                    if (cfg.dryRun) {
                        outcome.wouldDelete += 1;
                        deletedList.push({ id: entry.name, from: join('sessions', entry.ws), sizeBytes: probe.sizeBytes, dryRun: true });
                        continue;
                    }
                    await rm(entry.path, { recursive: true, force: true });
                    outcome.deleted += 1;
                    outcome.freedBytes += probe.sizeBytes;
                    deletedList.push({ id: entry.name, from: join('sessions', entry.ws), sizeBytes: probe.sizeBytes });
                }""",
)

rep(
    "        if (outcome.deleted > 0) {",
    "        if (outcome.deleted > 0 || outcome.wouldDelete > 0 || outcome.failures > 0) {",
)
rep(
    """                await writeFile(manifestPath, JSON.stringify({
                    createdAt: new Date(now).toISOString(),
                    retention: `${cfg.retentionValue} ${cfg.retentionUnit}`,
                    deleted: deletedList,
                }, null, 2), 'utf8');""",
    """                await writeFile(manifestPath, JSON.stringify({
                    createdAt: new Date(now).toISOString(),
                    retention: `${cfg.retentionValue} ${cfg.retentionUnit}`,
                    dryRun: cfg.dryRun,
                    deleted: deletedList,
                    counts: {
                        deleted: outcome.deleted,
                        wouldDelete: outcome.wouldDelete,
                        failures: outcome.failures,
                        skippedAttached: outcome.skippedAttached,
                    },
                    failureDetails: outcome.failureDetails,
                }, null, 2), 'utf8');""",
)
rep(
    "            ctx.logger.info(`archive-retention: deleted ${outcome.deleted} record(s), freed ${(outcome.freedBytes / 1e6).toFixed(1)}MB ` +",
    "            ctx.logger.info(`archive-retention: ${cfg.dryRun ? `would delete ${outcome.wouldDelete}` : `deleted ${outcome.deleted}`} record(s), freed ${(outcome.freedBytes / 1e6).toFixed(1)}MB ` +",
)

# ---------------------------------------------------------------- 4-6. 定时器：状态/校验/锁
OLD_TIMER = """    let lastSweepAt = Date.now();
    let sweeping = false;
    ctx.interval(() => {
        if (sweeping)
            return;
        const cfg = withDefaults(current());
        if (!cfg.enabled) {
            lastSweepAt = Date.now();
            return;
        }
        const now = Date.now();
        if (!cronDueSince(cfg.sweepCron, lastSweepAt, now))
            return;
        lastSweepAt = now;
        sweeping = true;
        void sweep().catch((error) => {
            ctx.logger.warn(`archive-retention: sweep failed: ${error instanceof Error ? error.message : String(error)}`);
        }).finally(() => { sweeping = false; });
    }, 30_000);"""

NEW_TIMER = """    // LOCAL PATCH (retention-fix): 状态持久化 + cron 校验 + 跨进程锁
    const statePath = join(home, 'archive-retention-state.json');
    const lockPath = join(home, 'archive-retention.lock');
    let lastSweepAt = Date.now();
    try {
        const raw = JSON.parse(readFileSync(statePath, 'utf8'));
        if (typeof raw.lastSweepAt === 'number' && Number.isFinite(raw.lastSweepAt))
            lastSweepAt = Math.min(Date.now(), raw.lastSweepAt);
    }
    catch {
    }
    let sweeping = false;
    let warnedCron;
    const effectiveCron = (cfg) => {
        if (isPlausibleCron(cfg.sweepCron))
            return cfg.sweepCron;
        if (warnedCron !== cfg.sweepCron) {
            warnedCron = cfg.sweepCron;
            ctx.logger.warn(`archive-retention: sweepCron "${cfg.sweepCron}" 无效，回落到 ${DEFAULT_SWEEP_CRON}`);
        }
        return DEFAULT_SWEEP_CRON;
    };
    const takeLock = async () => {
        try {
            await writeFile(lockPath, String(process.pid), { flag: 'wx' });
            return true;
        }
        catch {
            try {
                const info = await stat(lockPath);
                if (Date.now() - info.mtimeMs > 10 * 60_000) {
                    await writeFile(lockPath, String(process.pid));
                    return true;
                }
            }
            catch {
            }
            return false;
        }
    };
    const releaseLock = async () => {
        try {
            await rm(lockPath, { force: true });
        }
        catch {
        }
    };
    const persistState = async () => {
        try {
            await writeFile(statePath, JSON.stringify({ lastSweepAt, updatedAt: new Date().toISOString() }), 'utf8');
        }
        catch {
        }
    };
    ctx.interval(() => {
        if (sweeping)
            return;
        const cfg = withDefaults(current());
        if (!cfg.enabled) {
            lastSweepAt = Date.now();
            return;
        }
        const now = Date.now();
        if (!cronDueSince(effectiveCron(cfg), lastSweepAt, now))
            return;
        lastSweepAt = now;
        sweeping = true;
        void (async () => {
            if (!(await takeLock()))
                return;
            try {
                await sweep();
                await persistState();
            }
            catch (error) {
                ctx.logger.warn(`archive-retention: sweep failed: ${error instanceof Error ? error.message : String(error)}`);
            }
            finally {
                await releaseLock();
            }
        })().finally(() => { sweeping = false; });
    }, 30_000);"""

rep(OLD_TIMER, NEW_TIMER)

# ---------------------------------------------------------------- 应用
missing = []
for old, new in REPLACEMENTS:
    if new in src:
        continue
    if old not in src:
        missing.append(old.splitlines()[0][:80])
        continue
    src = src.replace(old, new, 1)

if missing:
    print('WARN: 以下锚点未匹配（插件版本变了？）:')
    for m in missing:
        print('   ', m)

target.write_text(src, encoding='utf-8')
print(f'archive-retention: patched ({len(REPLACEMENTS) - len(missing)}/{len(REPLACEMENTS)} replacements)')
