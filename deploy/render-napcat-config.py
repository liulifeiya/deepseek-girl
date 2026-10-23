"""Generate NapCat configs from the repo templates (Windows).

用法: python render-napcat-config.py [仓库根目录]

写 %USERPROFILE%\\Napcat\\config\\ 下的：
  napcat.json / napcat_<QQ>.json / napcat_protocol_<QQ>.json
  onebot11_<QQ>.json  （WS 3001 + token 取自 qq-dsh-bot\\onebot-token.txt）
  webui.json          （随机 token，仅监听 127.0.0.1）
"""
import json
import os
import secrets
import sys
from pathlib import Path

HOME = Path.home()
BOT = HOME / "qq-dsh-bot"
CFG = HOME / "Napcat" / "config"
BOT_QQ = os.environ.get("BOT_QQ", "2836148023")
WS_PORT = int(os.environ.get("NAPCAT_WS_PORT", "3001"))


def find_repo() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    for parent in Path(__file__).resolve().parents:
        if (parent / "napcat" / "napcat.json").exists() and (parent / "web" / "package.json").exists():
            return parent
    raise SystemExit("repo root not found; pass it as the first argument")


REPO = find_repo() / "napcat"
token = (BOT / "onebot-token.txt").read_text(encoding="utf-8").strip()

CFG.mkdir(parents=True, exist_ok=True)


def dump(name, data):
    with open(CFG / name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load(name):
    with open(REPO / name, encoding="utf-8") as f:
        return json.load(f)


dump("napcat.json", load("napcat.json"))
dump(f"napcat_{BOT_QQ}.json", load("napcat_2836148023.json"))
dump(f"napcat_protocol_{BOT_QQ}.json", load("napcat_protocol_2836148023.json"))

ob = load("onebot11_2836148023.json")
ob["network"]["websocketServers"] = [{
    "name": "bot-ws", "enable": True, "host": "127.0.0.1", "port": WS_PORT,
    "messagePostFormat": "array", "reportSelfMessage": True, "token": token,
    "enableForcePushEvent": True, "debug": False, "heartInterval": 30000,
}]
dump(f"onebot11_{BOT_QQ}.json", ob)

webui = load("webui.json")
webui["host"] = "127.0.0.1"
webui["token"] = secrets.token_hex(24)
webui["autoLoginAccount"] = BOT_QQ
dump("webui.json", webui)

print("config ->", CFG)
print("onebot token (first 8):", token[:8])
print("webui token:", webui["token"])
