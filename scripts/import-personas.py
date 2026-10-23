"""Import the repo's persona cards into the dsh-persona-dafeiyu store.

用法: python import-personas.py [仓库根目录]

把 <repo>/personas/personas.json 里的自定义人设卡写进
%USERPROFILE%\\.dsh-qq\\storages\\dsh-persona-dafeiyu\\personas.json，
保留原有的 mode / disabled / current 字段。
"""
import json
import shutil
import sys
from pathlib import Path

HOME = Path.home()
STORE = HOME / ".dsh-qq" / "storages" / "dsh-persona-dafeiyu" / "personas.json"
REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent

src = json.loads((REPO / "personas" / "personas.json").read_text(encoding="utf-8"))
cards = src.get("personas", [])
print("repo personas:", [(c["id"], c["name"]) for c in cards])

store = {}
if STORE.exists():
    store = json.loads(STORE.read_text(encoding="utf-8"))
    shutil.copy2(STORE, STORE.with_suffix(".json.bak"))

store.setdefault("version", 1)
store.setdefault("mode", "session")
store.setdefault("current", "dafeiyu")
store.setdefault("disabled", [])
store["personas"] = cards

STORE.parent.mkdir(parents=True, exist_ok=True)
STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("store written:", STORE, "->", len(cards), "custom personas")
