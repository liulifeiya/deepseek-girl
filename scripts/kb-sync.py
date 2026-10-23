#!/usr/bin/env python3
"""把本地知识库同步到独立的 GitHub 仓库（增量、按内容哈希比对）。

用法:
  python kb-sync.py                       # 同步到默认仓库
  python kb-sync.py --message "..."       # 自定义提交信息
  python kb-sync.py --dry-run             # 只看差异
  python kb-sync.py --repo owner/name --dir C:\\path\\knowledge

Token 读取顺序:
  1. 环境变量 KB_SYNC_TOKEN
  2. %USERPROFILE%\\.dsh-qq\\kb-sync.env 里的 KB_SYNC_TOKEN=...
  3. GITHUB_TOKEN

只同步文本资料：index.jsonl、notes/*.md、INBOX.md、topics.json、README.md。
跳过 curiosity.log、_draft.md、隐藏文件与临时文件。
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_REPO = "liulifeiya/deepseek-girl-knowledge"
SKIP_NAMES = {"curiosity.log", "_draft.md"}
SKIP_SUFFIX = (".tmp", ".log", ".bak", ".swp")


def load_token() -> str:
    tok = os.environ.get("KB_SYNC_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if tok:
        return tok.strip()
    env_file = Path.home() / ".dsh-qq" / "kb-sync.env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("KB_SYNC_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


class Api:
    def __init__(self, token: str, repo: str):
        self.token = token
        self.base = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "dsh-kb-sync",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def call(self, method, url, payload=None):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)


def local_files(root: Path):
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        name = p.name
        if name in SKIP_NAMES or name.startswith(".") or name.startswith("_") or rel.startswith("."):
            continue
        if rel.endswith(SKIP_SUFFIX):
            continue
        out[rel] = p
    return out


def remote_files(api: Api, tree_sha: str):
    out = {}
    data = api.call("GET", f"{api.base}/git/trees/{tree_sha}?recursive=1")
    for item in data.get("tree", []):
        if item.get("type") == "blob":
            out[item["path"]] = item["sha"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KB_SYNC_REPO", DEFAULT_REPO))
    ap.add_argument("--dir", default=os.environ.get("KB_HOME") or str(Path.home() / "knowledge"))
    ap.add_argument("--message", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.dir)
    if not root.exists():
        print("no knowledge dir:", root)
        return 1
    token = load_token()
    if not token:
        print("missing token: set KB_SYNC_TOKEN or %USERPROFILE%\\.dsh-qq\\kb-sync.env")
        return 2

    api = Api(token, args.repo)
    files = local_files(root)

    # 远端基线：空仓库时没有 ref
    base_sha = None
    base_tree = None
    remote = {}
    try:
        ref = api.call("GET", f"{api.base}/git/ref/heads/main")
        base_sha = ref["object"]["sha"]
        commit = api.call("GET", f"{api.base}/git/commits/{base_sha}")
        base_tree = commit["tree"]["sha"]
        remote = remote_files(api, base_tree)
    except urllib.error.HTTPError as e:
        # 404: 没有 main 分支；409: 仓库是空的（Git Repository is empty）
        if e.code not in (404, 409):
            print("read remote failed:", e.code)
            return 3
        # 空仓库不能直接建 blob（409），先用 Contents API 落一个初始提交
        seed = base64.b64encode("# deepseek-girl knowledge\n".encode("utf-8")).decode("ascii")
        api.call("PUT", f"{api.base}/contents/README.md", {
            "message": "init: 初始化知识库仓库",
            "content": seed,
        })
        ref = api.call("GET", f"{api.base}/git/ref/heads/main")
        base_sha = ref["object"]["sha"]
        commit = api.call("GET", f"{api.base}/git/commits/{base_sha}")
        base_tree = commit["tree"]["sha"]
        remote = remote_files(api, base_tree)

    # 本地内容哈希（用 blob sha 的算法：sha1("blob <len>\0" + 内容)）
    def blob_sha(path: Path) -> str:
        data = path.read_bytes()
        header = f"blob {len(data)}\0".encode()
        return hashlib.sha1(header + data).hexdigest()

    local_hashes = {rel: blob_sha(p) for rel, p in files.items()}
    added = sorted(k for k in files if k not in remote)
    modified = sorted(k for k in files if k in remote and remote[k] != local_hashes[k])
    deleted = sorted(k for k in remote if k not in files)
    print(f"added={len(added)} modified={len(modified)} deleted={len(deleted)}")
    for k in added:
        print("  +", k)
    for k in modified:
        print("  M", k)
    for k in deleted:
        print("  -", k)

    if not (added or modified or deleted):
        print("no changes")
        return 0
    if args.dry_run:
        print("(dry run)")
        return 0

    items = []
    for rel in added + modified:
        blob = api.call("POST", f"{api.base}/git/blobs", {
            "content": base64.b64encode(files[rel].read_bytes()).decode("ascii"),
            "encoding": "base64",
        })
        items.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    for rel in deleted:
        items.append({"path": rel, "mode": "100644", "type": "blob", "sha": None})

    tree_payload = {"tree": items}
    if base_tree:
        tree_payload["base_tree"] = base_tree
    tree = api.call("POST", f"{api.base}/git/trees", tree_payload)

    message = args.message.strip() or f"knowledge sync: {len(added)} new, {len(modified)} updated, {len(deleted)} removed"
    commit_payload = {"message": message, "tree": tree["sha"], "parents": [base_sha] if base_sha else []}
    commit = api.call("POST", f"{api.base}/git/commits", commit_payload)

    if base_sha:
        api.call("PATCH", f"{api.base}/git/refs/heads/main", {"sha": commit["sha"], "force": False})
    else:
        api.call("POST", f"{api.base}/git/refs", {"ref": "refs/heads/main", "sha": commit["sha"]})

    print("pushed:", commit["sha"])
    print("url: https://github.com/%s/commit/%s" % (args.repo, commit["sha"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
