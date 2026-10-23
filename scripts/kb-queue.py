#!/usr/bin/env python3
"""表情包 / 图片学习队列：聊天里遇到看不懂的图，先记下来，后台异步去查。

用法:
  python kb-queue.py add --hash <sha前16> --image <绝对路径> [--context "群877935643 配文xxx"]
  python kb-queue.py list [--json] [--all]
  python kb-queue.py done --id <id> --result "<LEARNED ...>"
  python kb-queue.py fail --id <id> --reason "..."

队列文件: %USERPROFILE%\\knowledge\\_queue.jsonl（不参与仓库同步）
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("KB_HOME") or (Path.home() / "knowledge"))
QUEUE = HOME / "_queue.jsonl"


def load():
    items = []
    if QUEUE.exists():
        for line in QUEUE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def save(items):
    HOME.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in items) + ("\n" if items else ""),
                     encoding="utf-8")


def cmd_add(args):
    items = load()
    h = args.hash.strip().lower()
    for it in items:
        if it.get("hash") == h and it.get("status") in ("pending", "done"):
            print(f"DUP {it.get('status')} {it.get('id')}")
            return 1
    pending = [i for i in items if i.get("status") == "pending"]
    if len(pending) >= 20:
        print("QUEUE_FULL (>=20 pending)")
        return 2
    item = {
        "id": "img-" + h[:10] + "-" + datetime.now().strftime("%H%M%S"),
        "hash": h,
        "image": str(Path(args.image)),
        "context": (args.context or "").strip()[:120],
        "status": "pending",
        "at": datetime.now().isoformat(timespec="seconds"),
        "result": "",
    }
    items.append(item)
    save(items)
    print(f"QUEUED {item['id']}")
    return 0


def cmd_list(args):
    items = load()
    if not args.all:
        items = [i for i in items if i.get("status") == "pending"]
    if args.json:
        print(json.dumps(items, ensure_ascii=False))
        return 0
    if not items:
        print("(empty)")
        return 0
    for it in items:
        print(f"{it.get('status'):8} {it.get('id'):24} {it.get('image')} | {it.get('context','')[:40]}")
    return 0


def _finish(args, status):
    items = load()
    hit = False
    for it in items:
        if it.get("id") == args.id:
            it["status"] = status
            it["result"] = (args.result or getattr(args, "reason", "") or "").strip()[:500]
            it["doneAt"] = datetime.now().isoformat(timespec="seconds")
            hit = True
    if not hit:
        print("not found:", args.id)
        return 1
    save(items)
    print(f"{status}: {args.id}")
    return 0


def cmd_done(args):
    return _finish(args, "done")


def cmd_fail(args):
    return _finish(args, "failed")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("--hash", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--context", default="")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("--json", action="store_true")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("done")
    p.add_argument("--id", required=True)
    p.add_argument("--result", default="")
    p.set_defaults(fn=cmd_done)

    p = sub.add_parser("fail")
    p.add_argument("--id", required=True)
    p.add_argument("--reason", default="")
    p.set_defaults(fn=cmd_fail)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
