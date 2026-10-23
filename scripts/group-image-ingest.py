#!/usr/bin/env python3
"""群聊图片入库：按 sha256 去重，复制到图库并登记。

用法：
  python group-image-ingest.py <图片路径> [--chat 1003871222] [--sender 昵称或QQ] [--desc "一句话描述"]

输出：NEW <hash前16位> <库内路径> 或 DUP <hash前16位> <已有路径>
"""
import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime

HOME = os.environ.get("BOT_HOME") or os.path.expanduser("~")
LIB = os.path.join(HOME, "qq-dsh-bot", "image-lib")
INDEX = os.path.join(LIB, 'index.jsonl')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--chat', default='')
    ap.add_argument('--sender', default='')
    ap.add_argument('--desc', default='')
    args = ap.parse_args()

    os.makedirs(LIB, exist_ok=True)
    with open(args.path, 'rb') as f:
        data = f.read()
    digest = hashlib.sha256(data).hexdigest()
    short = digest[:16]

    # 去重：查索引里已有同 hash
    existing = None
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            for line in f:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get('sha256') == digest:
                    existing = row
                    break

    ext = os.path.splitext(args.path)[1].lower() or '.jpg'
    dest = os.path.join(LIB, short + ext)

    if existing is not None:
        print('DUP ' + short + ' ' + existing.get('file', dest))
        return

    shutil.copyfile(args.path, dest)
    row = {
        'sha256': digest,
        'file': dest,
        'chat': args.chat,
        'sender': args.sender,
        'desc': args.desc,
        'at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(INDEX, 'a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print('NEW ' + short + ' ' + dest)


if __name__ == '__main__':
    main()
