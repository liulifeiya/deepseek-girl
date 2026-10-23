/**
 * LOCAL PATCH MODULE (image-hash): 图片入库 + sha256 去重。
 *
 * 目的：群里/私聊看到的图自动落到 image-lib，并在正文里带上短哈希。
 * 同一张图再来一次时，模型看到相同 #hash 就能立刻认出来，不用重新理解。
 *
 * 纯旁路：任何异常都吞掉，不影响消息处理。
 */
import { createHash } from 'node:crypto';
import { appendFileSync, copyFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { extname, join } from 'node:path';

const HOME = process.env.BOT_HOME || process.env.USERPROFILE || process.env.HOME || process.cwd();
const LIB = join(HOME, 'qq-dsh-bot', 'image-lib');
const INDEX = join(LIB, 'index.jsonl');

function findInIndex(hash) {
    try {
        if (!existsSync(INDEX))
            return undefined;
        for (const line of readFileSync(INDEX, 'utf8').split('\n')) {
            const row = line.trim();
            if (row === '')
                continue;
            try {
                const item = JSON.parse(row);
                if (item.sha256 === hash)
                    return item;
            }
            catch {
                // 坏行跳过
            }
        }
    }
    catch {
        // 纯旁路
    }
    return undefined;
}

/**
 * 把图片登记进图库。
 * @param file 本地图片路径
 * @returns {{short: string, dup: boolean, file: string} | undefined}
 */
export function ingestImage(file) {
    try {
        if (typeof file !== 'string' || file === '' || !existsSync(file))
            return undefined;
        const data = readFileSync(file);
        const hash = createHash('sha256').update(data).digest('hex');
        const short = hash.slice(0, 16);

        const existing = findInIndex(hash);
        if (existing !== undefined)
            return { short, dup: true, file: String(existing.file ?? '') };

        mkdirSync(LIB, { recursive: true });
        const ext = extname(file) || '.img';
        const dest = join(LIB, short + ext);
        if (!existsSync(dest))
            copyFileSync(file, dest);
        appendFileSync(INDEX, JSON.stringify({
            sha256: hash,
            file: dest,
            source: file,
            bytes: data.length,
            at: new Date().toISOString(),
        }) + '\n');
        return { short, dup: false, file: dest };
    }
    catch {
        return undefined;
    }
}
