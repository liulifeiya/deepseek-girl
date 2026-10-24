#!/usr/bin/env python3
"""网络图片 → 表情包库（stickers/）：下载、校验、去重、登记。

用法:
  python meme-lib.py add --url <图片URL> [--tags a,b] [--source <来源页面>]
  python meme-lib.py from-page --url <页面URL> [--limit 3] [--tags a,b]
  python meme-lib.py list [--tag x]      / search <kw> / stats

库目录: %USERPROFILE%\\stickers（可用 MEME_HOME 覆盖）
  index.jsonl   每张一行：file/hash/url/page/tags/bytes/at
  <hash16>.<ext> 图片本体
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("MEME_HOME") or (Path.home() / "stickers"))
INDEX = HOME / "index.jsonl"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) dsh-meme-lib/1.0"}
MAX_BYTES = 8 * 1024 * 1024


def ensure():
    HOME.mkdir(parents=True, exist_ok=True)
    if not INDEX.exists():
        INDEX.write_text("", encoding="utf-8")


def rows():
    out = []
    if INDEX.exists():
        for line in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def sniff(data: bytes):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def fetch(url: str) -> bytes:
    """用系统 curl 下载（Windows 的 Python 常缺 CA 根证书，urllib 会 SSL 验证失败）。"""
    import subprocess
    import tempfile

    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        r = subprocess.run(
            ["curl.exe", "-sSL", "--max-time", "25", "--max-filesize", str(MAX_BYTES),
             "-A", UA["User-Agent"], "-o", tmp, url],
            capture_output=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"curl exit={r.returncode} {r.stderr[:160].decode('utf-8', 'replace')}")
        data = Path(tmp).read_bytes()
        if not data:
            raise RuntimeError("empty response")
        if len(data) > MAX_BYTES:
            raise RuntimeError(f"too large: {len(data)} bytes")
        return data
    finally:
        Path(tmp).unlink(missing_ok=True)


def save(data: bytes, url: str, page: str, tags) -> str:
    ext = sniff(data)
    if not ext:
        raise ValueError("not an image (png/jpg/gif/webp only)")
    if len(data) > MAX_BYTES:
        raise ValueError(f"too large: {len(data)} bytes")
    digest = hashlib.sha256(data).hexdigest()
    short = digest[:16]
    for row in rows():
        if row.get("hash") == digest:
            print(f"DUP {row.get('file')}")
            return row.get("file", "")
    path = HOME / f"{short}.{ext}"
    path.write_bytes(data)
    row = {
        "file": str(path),
        "hash": digest,
        "url": url,
        "page": page,
        "tags": [t.strip() for t in tags if t.strip()],
        "bytes": len(data),
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"NEW {path}")
    return str(path)


def cmd_add(args):
    ensure()
    data = fetch(args.url)
    save(data, args.url, args.source or "", args.tags.split(",") if args.tags else [])
    return 0


IMG_RE = re.compile(r"""(?:src|data-src|data-original)=["']([^"']+\.(?:png|jpe?g|gif|webp)[^"']*)["']""", re.I)
OG_RE = re.compile(r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']""", re.I)


def cmd_from_page(args):
    ensure()
    page = args.url
    html = fetch(page).decode("utf-8", errors="replace")
    cands = [urllib.parse.urljoin(page, m) for m in IMG_RE.findall(html)]
    cands += [urllib.parse.urljoin(page, m) for m in OG_RE.findall(html)]
    seen, got = set(), 0
    for url in cands:
        if url in seen or urllib.parse.urlparse(url).scheme not in ("http", "https"):
            continue
        seen.add(url)
        if got >= args.limit:
            break
        try:
            data = fetch(url)
            if len(data) < 2048:  # 图标/占位图跳过
                continue
            if save(data, url, page, args.tags.split(",") if args.tags else []):
                got += 1
        except Exception as e:
            print(f"skip {url}: {e}")
    print(f"downloaded={got}")
    return 0 if got else 1


def cmd_list(args):
    items = rows()
    if getattr(args, "tag", ""):
        items = [r for r in items if args.tag in r.get("tags", [])]
    for r in items[-30:]:
        print(f"{r.get('hash','')[:10]} {r.get('bytes',0):>7}B {r.get('file')} | {','.join(r.get('tags', []))}")
    print(f"total={len(items)}")
    return 0


def cmd_search(args):
    kw = args.keyword.lower()
    hits = [r for r in rows() if kw in json.dumps(r, ensure_ascii=False).lower()]
    for r in hits[-10:]:
        print(f"{r.get('file')} | {','.join(r.get('tags', []))} | {r.get('page','')}")
    print(f"hits={len(hits)}")
    return 0


def cmd_stats(_args):
    items = rows()
    size = sum(r.get("bytes", 0) for r in items)
    print(f"images={len(items)} size={size/1024:.1f}KB path={HOME}")
    if items:
        print("last:", items[-1].get("file"))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("--url", required=True)
    p.add_argument("--tags", default="")
    p.add_argument("--source", default="")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("from-page")
    p.add_argument("--url", required=True)
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--tags", default="")
    p.set_defaults(fn=cmd_from_page)
    p = sub.add_parser("list"); p.add_argument("--tag", default=""); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("search"); p.add_argument("keyword"); p.set_defaults(fn=cmd_search)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
