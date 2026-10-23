#!/usr/bin/env python3
"""archive-retention 第二轮补丁：回收站、容量上限、机器人自己的归档名单。

在 patch-archive-retention.py（v1）之后运行，幂等。
用法: python patch-archive-retention-2.py [插件目录]

新增：
- 删除先进 `sessions-archive/_trash/<时间戳>/<id>`，超过 trashRetentionHours
  （默认 72h）再物理删除；rename 失败才退回 rm。
- maxTotalBytes（默认 0=关）：归档总量超限时按最旧优先清理。
- extraArchivedIdsFile（默认 archive-list.json）：机器人没有 GUI，
  用它维护「要归档的会话 id」；与 GUI 的 archivedSessionIds 合并。
"""
import sys
from pathlib import Path

MARKER = 'LOCAL PATCH (retention-fix2)'
DEFAULT_PLUGIN = Path.home() / '.dsh-qq' / 'profiles' / 'qq' / 'node_modules' / '@momojie-s' / 'dsh-archive-retention'

plugin = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PLUGIN
target = plugin / 'lib' / 'index.js'
if not target.exists():
    print('WARN: plugin not found, skip:', target)
    sys.exit(0)

src = target.read_text(encoding='utf-8')
if MARKER in src:
    print('archive-retention: already patched (v2)')
    sys.exit(0)
if 'LOCAL PATCH (retention-fix)' not in src:
    print('WARN: v1 补丁未打，先跑 patch-archive-retention.py')
    sys.exit(1)

R = []


def rep(old, new):
    R.append((old, new))


rep(
    "import { mkdir, readdir, rm, stat, writeFile } from 'node:fs/promises';",
    "import { mkdir, readdir, rename, rm, stat, writeFile } from 'node:fs/promises';",
)

rep(
    """    dryRun: z.boolean().default(false).volatile(),
    retentionValue: z.number().min(1).default(7).volatile(),""",
    """    dryRun: z.boolean().default(false).volatile(),
    // LOCAL PATCH (retention-fix2): 回收站保留小时数 / 归档容量上限 / 额外归档名单
    trashRetentionHours: z.number().min(1).default(72).volatile(),
    maxTotalBytes: z.number().min(0).default(0).volatile(),
    extraArchivedIdsFile: z.string().default('archive-list.json').volatile(),
    retentionValue: z.number().min(1).default(7).volatile(),""",
)

rep(
    """        dryRun: c.dryRun ?? false,
        retentionValue: c.retentionValue ?? 7,""",
    """        dryRun: c.dryRun ?? false,
        trashRetentionHours: c.trashRetentionHours ?? 72,
        maxTotalBytes: c.maxTotalBytes ?? 0,
        extraArchivedIdsFile: c.extraArchivedIdsFile ?? 'archive-list.json',
        retentionValue: c.retentionValue ?? 7,""",
)

rep(
    """        dryRun: config.dryRun.get(),
        retentionValue: config.retentionValue.get(),""",
    """        dryRun: config.dryRun.get(),
        trashRetentionHours: config.trashRetentionHours.get(),
        maxTotalBytes: config.maxTotalBytes.get(),
        extraArchivedIdsFile: config.extraArchivedIdsFile.get(),
        retentionValue: config.retentionValue.get(),""",
)

rep(
    """    const archiveRoot = join(home, 'sessions-archive');
    const sessionsRoot = join(home, 'sessions');""",
    """    const archiveRoot = join(home, 'sessions-archive');
    const sessionsRoot = join(home, 'sessions');
    // LOCAL PATCH (retention-fix2): 删除先挪进回收站，到期再物理清
    const trashRoot = join(archiveRoot, '_trash');
    async function quarantine(dir, id, stamp) {
        const useStamp = stamp ?? new Date().toISOString().replace(/[:.]/g, '-');
        const dest = join(trashRoot, useStamp, id);
        try {
            await mkdir(join(trashRoot, useStamp), { recursive: true });
            await rename(dir, dest);
            return dest;
        }
        catch {
            await rm(dir, { recursive: true, force: true });
            return undefined;
        }
    }""",
)

rep(
    "                workspaces = (await readdir(archiveRoot, { withFileTypes: true })).filter(e => e.isDirectory()).map(e => e.name);",
    "                workspaces = (await readdir(archiveRoot, { withFileTypes: true })).filter(e => e.isDirectory() && e.name !== '_trash' && e.name !== '_manifests').map(e => e.name);",
)

rep(
    """                        await rm(dir, { recursive: true, force: true });
                        outcome.deleted += 1;
                        outcome.freedBytes += probe.sizeBytes;
                        deletedList.push({ id, from: join('sessions-archive', ws), sizeBytes: probe.sizeBytes });""",
    """                        const trashed = await quarantine(dir, id, sweepStamp);
                        outcome.deleted += 1;
                        outcome.freedBytes += probe.sizeBytes;
                        deletedList.push({ id, from: join('sessions-archive', ws), sizeBytes: probe.sizeBytes, trash: trashed });""",
)

rep(
    """            catch (error) {
                outcome.failureDetails.push(`registry: ${error instanceof Error ? error.message : String(error)}`);
            }
            for (const id of archived) {""",
    """            catch (error) {
                outcome.failureDetails.push(`registry: ${error instanceof Error ? error.message : String(error)}`);
            }
            // LOCAL PATCH (retention-fix2): 机器人没有 GUI，用本地名单补充
            try {
                const extraPath = join(home, cfg.extraArchivedIdsFile);
                if (existsSync(extraPath)) {
                    const extra = JSON.parse(readFileSync(extraPath, 'utf8'));
                    if (Array.isArray(extra)) {
                        const merged = new Set(archived.map(String));
                        for (const item of extra) {
                            if (typeof item === 'string' || typeof item === 'number')
                                merged.add(String(item));
                        }
                        archived = [...merged];
                    }
                }
            }
            catch (error) {
                outcome.failureDetails.push(`archive-list: ${error instanceof Error ? error.message : String(error)}`);
            }
            for (const id of archived) {""",
)

rep(
    """                    await rm(located.dir, { recursive: true, force: true });
                    outcome.deleted += 1;
                    outcome.freedBytes += located.probe.sizeBytes;
                    deletedList.push({ id, from: 'sessions', sizeBytes: located.probe.sizeBytes });""",
    """                    const trashed = await quarantine(located.dir, id, sweepStamp);
                    outcome.deleted += 1;
                    outcome.freedBytes += located.probe.sizeBytes;
                    deletedList.push({ id, from: 'sessions', sizeBytes: located.probe.sizeBytes, trash: trashed });""",
)

rep(
    """                    await rm(entry.path, { recursive: true, force: true });
                    outcome.deleted += 1;
                    outcome.freedBytes += probe.sizeBytes;
                    deletedList.push({ id: entry.name, from: join('sessions', entry.ws), sizeBytes: probe.sizeBytes });""",
    """                    const trashed = await quarantine(entry.path, entry.name, sweepStamp);
                    outcome.deleted += 1;
                    outcome.freedBytes += probe.sizeBytes;
                    deletedList.push({ id: entry.name, from: join('sessions', entry.ws), sizeBytes: probe.sizeBytes, trash: trashed });""",
)

rep(
    "        const deletedList = [];",
    "        const deletedList = [];\n        const sweepStamp = new Date(now).toISOString().replace(/[:.]/g, '-');",
)

TRASH_AND_CAP = """        // ---- LOCAL PATCH (retention-fix2): 回收站到期清理 ----
        if (!cfg.dryRun) {
            try {
                const parseStamp = (name) => {
                    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})-(\d{3})Z$/.exec(name);
                    return m === null ? undefined : Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6], +m[7]);
                };
                const stamps = (await readdir(trashRoot, { withFileTypes: true })).filter(e => e.isDirectory()).map(e => e.name);
                for (const stamp of stamps) {
                    const dir = join(trashRoot, stamp);
                    let born = parseStamp(stamp);
                    if (born === undefined) {
                        const probe = await probeDir(dir);
                        born = probe.lastWriteMs;
                    }
                    if (born !== undefined && now - born > cfg.trashRetentionHours * 3_600_000)
                        await rm(dir, { recursive: true, force: true });
                }
            }
            catch {
            }
        }
        // ---- LOCAL PATCH (retention-fix2): 容量上限（最旧优先）----
        if (cfg.maxTotalBytes > 0) {
            const items = [];
            let total = 0;
            try {
                const wsList = (await readdir(archiveRoot, { withFileTypes: true })).filter(e => e.isDirectory() && e.name !== '_trash' && e.name !== '_manifests').map(e => e.name);
                for (const ws of wsList) {
                    let ids = [];
                    try {
                        ids = (await readdir(join(archiveRoot, ws), { withFileTypes: true })).filter(e => e.isDirectory()).map(e => e.name);
                    }
                    catch {
                        continue;
                    }
                    for (const id of ids) {
                        const dir = join(archiveRoot, ws, id);
                        const probe = await probeDir(dir);
                        if (probe.lastWriteMs === undefined)
                            continue;
                        items.push({ ws, id, dir, probe });
                        total += probe.sizeBytes;
                    }
                }
            }
            catch {
            }
            items.sort((a, b) => a.probe.lastWriteMs - b.probe.lastWriteMs);
            const already = new Set(deletedList.map((entry) => `${entry.id}@${entry.from}`));
            for (const item of items) {
                if (total <= cfg.maxTotalBytes)
                    break;
                if (already.has(`${item.id}@${join('sessions-archive', item.ws)}`)) {
                    total -= item.probe.sizeBytes;
                    continue;
                }
                if (!(await stillQuiescent(item.dir, item.probe.lastWriteMs)))
                    continue;
                if (cfg.dryRun) {
                    outcome.wouldDelete += 1;
                    deletedList.push({ id: item.id, from: join('sessions-archive', item.ws), sizeBytes: item.probe.sizeBytes, dryRun: true, reason: 'size-cap' });
                }
                else {
                    try {
                        const trashed = await quarantine(item.dir, item.id);
                        outcome.deleted += 1;
                        outcome.freedBytes += item.probe.sizeBytes;
                        deletedList.push({ id: item.id, from: join('sessions-archive', item.ws), sizeBytes: item.probe.sizeBytes, trash: trashed, reason: 'size-cap' });
                    }
                    catch (error) {
                        outcome.failures += 1;
                        outcome.failureDetails.push(`${item.id}: ${error instanceof Error ? error.message : String(error)}`);
                    }
                }
                total -= item.probe.sizeBytes;
            }
        }
        if (outcome.deleted > 0 || outcome.wouldDelete > 0 || outcome.failures > 0) {"""

rep(
    "        if (outcome.deleted > 0 || outcome.wouldDelete > 0 || outcome.failures > 0) {",
    TRASH_AND_CAP,
)

missing = []
applied = 0
for old, new in R:
    if new in src:
        applied += 1
        continue
    if old not in src:
        missing.append(old.splitlines()[0][:80])
        continue
    src = src.replace(old, new, 1)
    applied += 1

if missing:
    print('WARN: 以下锚点未匹配:')
    for m in missing:
        print('   ', m)

target.write_text(src, encoding='utf-8')
print(f'archive-retention v2: {applied}/{len(R)} replacements applied')
