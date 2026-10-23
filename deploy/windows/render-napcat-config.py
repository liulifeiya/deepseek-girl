"""Generate NapCat configs for Windows from the repo templates."""
import json, os, secrets, sys

repo = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\deepseek-girl-main\napcat"
cfg = r"C:\Users\Administrator\Napcat\config"
bot = "2836148023"
token = open(r"C:\Users\Administrator\qq-dsh-bot\onebot-token.txt", encoding="utf-8").read().strip()
port = 3001

os.makedirs(cfg, exist_ok=True)

def dump(name, data):
    with open(os.path.join(cfg, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def load(name):
    with open(os.path.join(repo, name), encoding="utf-8") as f:
        return json.load(f)

dump("napcat.json", load("napcat.json"))
dump(f"napcat_{bot}.json", load("napcat_2836148023.json"))
dump(f"napcat_protocol_{bot}.json", load("napcat_protocol_2836148023.json"))

ob = load("onebot11_2836148023.json")
ob["network"]["websocketServers"] = [{
    "name": "bot-ws", "enable": True, "host": "127.0.0.1", "port": port,
    "messagePostFormat": "array", "reportSelfMessage": True, "token": token,
    "enableForcePushEvent": True, "debug": False, "heartInterval": 30000,
}]
dump(f"onebot11_{bot}.json", ob)

webui = load("webui.json")
webui["host"] = "127.0.0.1"
webui["token"] = secrets.token_hex(24)
webui["autoLoginAccount"] = bot
dump("webui.json", webui)

print("config ->", cfg)
print("onebot token (first 8):", token[:8])
print("webui token:", webui["token"])
