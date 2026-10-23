#!/usr/bin/env python3
"""知识库管理：好奇心循环用它登记素材、去重、生成入口摘要。

用法:
  python kb.py stats
  python kb.py topics
  python kb.py search <关键词>
  python kb.py add --url <URL> --title <标题> --tags a,b --summary <一句话> [--body-file <md>]
  python kb.py inbox [条数]

目录（默认 %USERPROFILE%\\knowledge，可用 KB_HOME 覆盖）:
  index.jsonl   每条来源一行 JSON
  notes/        <slug>-<hash8>.md
  topics.json   兴趣清单
  INBOX.md      最近 N 条，供聊天时快速引用
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("KB_HOME") or (Path.home() / "knowledge"))
INDEX = HOME / "index.jsonl"
NOTES = HOME / "notes"
TOPICS = HOME / "topics.json"
INBOX = HOME / "INBOX.md"
INBOX_LIMIT = 12

DEFAULT_TOPICS = {
    "interests": [
        {"name": "大模型与 Agent", "weight": 3},
        {"name": "开源工具", "weight": 2},
        {"name": "硬件与算力", "weight": 2},
        {"name": "游戏与二次元", "weight": 1},
        {"name": "音乐与声音", "weight": 1},
        {"name": "网络文化与梗", "weight": 1},
    ],
    "questions": [],
    "lastTopic": "",
}


def ensure():
    HOME.mkdir(parents=True, exist_ok=True)
    NOTES.mkdir(parents=True, exist_ok=True)
    if not TOPICS.exists():
        TOPICS.write_text(json.dumps(DEFAULT_TOPICS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not INDEX.exists():
        INDEX.write_text("", encoding="utf-8")
    if not INBOX.exists():
        INBOX.write_text("# INBOX\n\n（还没有学到东西）\n", encoding="utf-8")


def rows():
    out = []
    if INDEX.exists():
        for line in INDEX.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def norm_url(url: str) -> str:
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"#.*$", "", u)
    u = u.rstrip("/")
    return u


def slugify(text: str) -> str:
    keep = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-")
    return (keep[:40] or "note").lower()


def load_topics():
    if TOPICS.exists():
        try:
            return json.loads(TOPICS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_TOPICS)


def cmd_stats(_args):
    data = rows()
    home = HOME
    size = sum(p.stat().st_size for p in home.rglob("*") if p.is_file()) if home.exists() else 0
    print(f"notes={len(data)} files={len(list(NOTES.glob('*.md'))) if NOTES.exists() else 0} kb={size/1024:.1f}KB")
    print(f"path={home}")
    if data:
        print("last:", data[-1].get("title", ""), "|", data[-1].get("at", ""))


def cmd_topics(_args):
    t = load_topics()
    data = rows()
    counts = {}
    for row in data:
        for tag in row.get("tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    print("interests:")
    for item in t.get("interests", []):
        name = item.get("name", "?")
        print(f"  - {name} (weight {item.get('weight', 1)}, covered {counts.get(name, 0)})")
    if t.get("questions"):
        print("open questions:")
        for q in t["questions"][:10]:
            print("  -", q)
    print("lastTopic:", t.get("lastTopic") or "(none)")


def cmd_search(args):
    kw = args.keyword.lower()
    hits = [r for r in rows() if kw in json.dumps(r, ensure_ascii=False).lower()]
    if not hits:
        print("no match")
        return
    for r in hits[-10:]:
        print(f"- {r.get('title','')} | {r.get('url','')} | {r.get('summary','')[:60]}")


def cmd_inbox(args):
    n = args.n or INBOX_LIMIT
    data = rows()[-n:]
    if not data:
        print("(empty)")
        return
    for r in data:
        print(f"- {r.get('title','')}：{r.get('summary','')} ({r.get('at','')[:10]})")


def regenerate_inbox():
    data = rows()[-INBOX_LIMIT:]
    lines = ["# INBOX", "", "最近学到的（由好奇心循环自动维护）", ""]
    for r in reversed(data):
        lines.append(f"## {r.get('title','')}")
        lines.append(f"- 摘要：{r.get('summary','')}")
        lines.append(f"- 标签：{', '.join(r.get('tags', []))}")
        lines.append(f"- 来源：{r.get('url','')}")
        lines.append(f"- 笔记：{r.get('note','')}")
        lines.append(f"- 时间：{r.get('at','')}")
        lines.append("")
    INBOX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_add(args):
    ensure()
    url = args.url.strip()
    title = args.title.strip() or url
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    summary = (args.summary or "").strip()
    body = ""
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8", errors="replace")

    nu = norm_url(url)
    for row in rows():
        if norm_url(row.get("url", "")) == nu:
            print(f"DUP url {row.get('note','')}")
            return 1

    sha = hashlib.sha256((body or summary or url).encode("utf-8")).hexdigest()
    short = sha[:8]
    name = f"{slugify(title)}-{short}.md"
    note_path = NOTES / name
    note = [f"# {title}", "", f"- 来源：{url}", f"- 标签：{', '.join(tags)}",
            f"- 抓取：{datetime.now().isoformat(timespec='seconds')}", "", "## 摘要", "", summary, ""]
    if body:
        note += ["## 笔记", "", body.strip(), ""]
    note_path.write_text("\n".join(note) + "\n", encoding="utf-8")

    row = {
        "url": url, "title": title, "tags": tags, "summary": summary,
        "note": str(note_path), "sha": sha, "at": datetime.now().isoformat(timespec="seconds"),
    }
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    t = load_topics()
    t["lastTopic"] = tags[0] if tags else title
    TOPICS.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    regenerate_inbox()
    print(f"NEW {note_path}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    sub.add_parser("topics").set_defaults(fn=cmd_topics)
    p = sub.add_parser("search"); p.add_argument("keyword"); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("inbox"); p.add_argument("n", nargs="?", type=int, default=INBOX_LIMIT); p.set_defaults(fn=cmd_inbox)
    p = sub.add_parser("add")
    p.add_argument("--url", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--body-file", default="")
    p.set_defaults(fn=cmd_add)
    args = ap.parse_args()
    ensure()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
