#!/usr/bin/env bash
# 40-botfiles：机器人运行脚本、补丁、token、人设
source "$(dirname "$0")/../lib.sh"
setup_path

BOT="$BOT_HOME/qq-dsh-bot"
step "运行目录: $BOT"
run mkdir -p "$BOT/patches" "$BOT/image-lib" "$BOT/session-archive"

step "看门狗 / 保活 / 二维码"
copy_script "$ROOT/runtime/guard.mjs"     "$BOT/guard.mjs"
copy_script "$ROOT/runtime/keepalive.mjs" "$BOT/keepalive.mjs"
copy_script "$ROOT/runtime/watchdog.mjs"  "$BOT/watchdog.mjs"
copy_script "$ROOT/runtime/qr-term.py"    "$BOT/qr-term.py"

step "业务脚本"
for f in img-prep.py group-image-ingest.py proactive.py; do
  copy_script "$ROOT/scripts/$f" "$BOT/$f"
done
copy_script "$ROOT/scripts/monthly-prompt.txt" "$BOT/monthly-prompt.txt" 644

step "补丁"
for f in group-wake.js mention-context.js persona-lock.js persona-command.js sleep-window.js; do
  copy_script "$ROOT/patches/$f" "$BOT/patches/$f"
done
copy_script "$ROOT/patches/apply-onebot-patches.py" "$BOT/patches/apply-onebot-patches.py"
copy_script "$ROOT/patches/bind-private-persona.sh" "$BOT/patches/bind-private-persona.sh"

step "人设"
for f in "$ROOT"/personas/persona-*.md; do
  [ -f "$f" ] || continue
  copy_file "$f" "$BOT/$(basename "$f")"
done

step "OneBot token"
if [ "$DRY_RUN" = 1 ]; then
  log "would write $BOT/onebot-token.txt"
else
  printf '%s\n' "$ONEBOT_TOKEN" > "$BOT/onebot-token.txt"
  chmod 600 "$BOT/onebot-token.txt"
  ok "token 已写入（600）"
fi

step "主动搭话白名单"
if [ -f "$BOT/proactive-targets.txt" ]; then
  ok "已存在，保留"
elif [ "$DRY_RUN" = 0 ]; then
  cat > "$BOT/proactive-targets.txt" <<'EOF'
# 主动搭话白名单：QQ号 昵称 [group:群号] [dm]
# 默认在群里 @ 对方（不需要好友）；行尾加 dm 才走私聊。
EOF
  chmod 600 "$BOT/proactive-targets.txt"
  log "已建空白名单：$BOT/proactive-targets.txt"
fi

step "运行期文件权限"
if [ "$DRY_RUN" = 0 ]; then
  chmod 700 "$BOT" 2>/dev/null || true
  touch "$BOT/dsh-web.log" "$BOT/guard.log" "$BOT/keepalive.log" "$BOT/napcat.log" 2>/dev/null || true
fi
ok "机器人文件层完成"
