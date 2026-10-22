#!/usr/bin/env bash
# 30-plugins：dsh profile、插件、cordis 覆盖、onebot 补丁
source "$(dirname "$0")/../lib.sh"
setup_path

PROFILE="$DSH_HOME/profiles/web"
step "dsh profile: $PROFILE"
run mkdir -p "$PROFILE"

copy_file "$ROOT/web/package.json"        "$PROFILE/package.json"
copy_file "$ROOT/web/pnpm-workspace.yaml" "$PROFILE/pnpm-workspace.yaml"
copy_file "$ROOT/web/pnpm-lock.yaml"      "$PROFILE/pnpm-lock.yaml"

step "安装插件（pnpm）"
if [ "$DRY_RUN" = 0 ]; then
  cd "$PROFILE"
  if ! pnpm install --frozen-lockfile; then
    warn "锁文件对不上，退回普通 install（生产环境建议重新生成 lock 并提交）"
    pnpm install
  fi
  cd - >/dev/null
else
  run pnpm install --frozen-lockfile
fi

step "写入 cordis 覆盖配置"
render "$ROOT/deploy/templates/cordis.patch.yml.tpl" "$PROFILE/cordis.patch.yml"
chmod 600 "$PROFILE/cordis.patch.yml" 2>/dev/null || true

step "机器人运行配置"
if [ -f "$DSH_HOME/group-wake.json" ]; then
  ok "group-wake.json 已存在，保留（迁移数据优先）"
else
  copy_file "$ROOT/config/group-wake.json" "$DSH_HOME/group-wake.json"
fi
if [ -f "$DSH_HOME/sleep-window.json" ]; then
  ok "sleep-window.json 已存在，保留"
else
  copy_file "$ROOT/config/sleep-window.json" "$DSH_HOME/sleep-window.json"
fi

if [ "$DRY_RUN" = 1 ]; then
  log "would write $DSH_HOME/dsh-web.env"
elif [ -n "$DEEPSEEK_API_KEY" ]; then
  printf 'DEEPSEEK_API_KEY=%s\n' "$DEEPSEEK_API_KEY" > "$DSH_HOME/dsh-web.env"
  chmod 600 "$DSH_HOME/dsh-web.env"
  ok "dsh-web.env 已写入"
else
  warn "DEEPSEEK_API_KEY 为空，稍后在 $DSH_HOME/dsh-web.env 里补"
  : > "$DSH_HOME/dsh-web.env"
  chmod 600 "$DSH_HOME/dsh-web.env"
fi

step "给 dsh-onebot-qq 打补丁（引用回复 / 分段 / 群聊静默）"
LIB="$PROFILE/node_modules/dsh-onebot-qq/lib"
if [ "$DRY_RUN" = 1 ]; then
  log "would patch $LIB"
elif [ -d "$LIB" ]; then
  python3 "$ROOT/patches/apply-onebot-patches.py" "$LIB"
  if grep -q "LOCAL PATCH (quote-reply)" "$LIB/outbound.js"; then
    ok "补丁已生效"
  else
    die "补丁没打上：插件版本变了？看 patches/apply-onebot-patches.py 的匹配串"
  fi
else
  die "找不到 $LIB，pnpm install 可能失败"
fi

ok "插件层完成"
