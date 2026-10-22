#!/usr/bin/env bash
# 70-napcat：QQ 客户端 + NapCat 注入 + OneBot/WebUI 配置
source "$(dirname "$0")/../lib.sh"
setup_path

if [ "$WITH_NAPCAT" != "1" ]; then
  log "WITH_NAPCAT=0，跳过（需要 NapCat 时把 deploy.conf 改回 1 重跑这一步）"
  exit 0
fi

NAPCAT_DIR="$BOT_HOME/Napcat/opt/QQ"
QQ_BIN="$NAPCAT_DIR/qq"
step "NapCat: $NAPCAT_DIR"

if [ -x "$QQ_BIN" ]; then
  ok "QQ/NapCat 已安装"
else
  [ "$HOME" = "$BOT_HOME" ] || die "NapCat 安装脚本按 \$HOME 落盘，请用 $BOT_HOME 对应用户运行（当前 HOME=$HOME）"
  need_sudo
  log "用官方安装脚本装 QQ + NapCat（rootless，下载约 300MB，需要几分钟）"
  run bash "$ROOT/deploy/vendor/napcat-installer.sh" --docker n --qq "$BOT_QQ" --cli n
  [ -x "$QQ_BIN" ] || die "NapCat 装完但找不到 $QQ_BIN，看安装日志"
fi

step "写入 OneBot / WebUI 配置"
CFG="$NAPCAT_DIR/resources/app/app_launcher/napcat/config"
SRC="$ROOT/napcat"
run mkdir -p "$CFG"
if [ "$DRY_RUN" = 0 ]; then
  python3 - "$SRC" "$CFG" "$BOT_QQ" "$ONEBOT_TOKEN" "$NAPCAT_WS_PORT" <<'PY'
import json, os, secrets, sys
src, cfg, bot, token, port = sys.argv[1:6]
port = int(port)

def dump(name, data):
    with open(os.path.join(cfg, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def load(name):
    with open(os.path.join(src, name), encoding="utf-8") as f:
        return json.load(f)

# 基础配置：控制台日志、自动时间同步
dump("napcat.json", load("napcat.json"))
dump(f"napcat_{bot}.json", load("napcat_2836148023.json"))
dump(f"napcat_protocol_{bot}.json", load("napcat_protocol_2836148023.json"))

# OneBot：只开本地 WS，token 与 dsh 两端一致
ob = load("onebot11_2836148023.json")
ob["network"]["websocketServers"] = [{
    "name": "bot-ws", "enable": True, "host": "127.0.0.1", "port": port,
    "messagePostFormat": "array", "reportSelfMessage": True, "token": token,
    "enableForcePushEvent": True, "debug": False, "heartInterval": 30000,
}]
dump(f"onebot11_{bot}.json", ob)

# WebUI 单独一个 token，只监听本机
webui = load("webui.json")
webui["host"] = "127.0.0.1"
webui["token"] = secrets.token_hex(24)
webui["autoLoginAccount"] = bot
dump("webui.json", webui)
print("napcat configs ->", cfg)
print("webui token ->", webui["token"])
PY
else
  log "would render napcat configs into $CFG"
fi

step "快速登录补丁（重启 Worker 保留 -q）"
MJS="$NAPCAT_DIR/resources/app/app_launcher/napcat/napcat.mjs"
if [ "$DRY_RUN" = 1 ]; then
  log "would patch $MJS"
elif [ -f "$MJS" ]; then
  python3 "$ROOT/patches/patch-napcat-quicklogin.py" "$MJS" || \
    warn "快速登录补丁没打上（NapCat 版本变了？看 patches/NAPCAT-QUICK-LOGIN.md）"
else
  warn "找不到 napcat.mjs，跳过快速登录补丁"
fi

ok "NapCat 层完成（首次启动要扫码登录，见 docs/MIGRATION.md）"
