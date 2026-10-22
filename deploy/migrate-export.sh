#!/usr/bin/env bash
# 老机器导出：把「人 + 配置 + 记忆 + 会话」打成一个迁移包。
#
#   ./deploy/migrate-export.sh                      # 不含密钥，可安全传输
#   ./deploy/migrate-export.sh --with-secrets       # 含 API key / token（注意保管）
#   ./deploy/migrate-export.sh --with-sessions      # 带上聊天会话（默认带）
#   ./deploy/migrate-export.sh --no-sessions        # 只要配置和人设
#   ./deploy/migrate-export.sh --with-media         # 带上收发的图片（比较大）
#   ./deploy/migrate-export.sh -o /tmp/qqbot.tar.gz
#   ./deploy/migrate-export.sh --with-qq-login      # 带上 QQ 登录态（省一次扫码，成功率看设备验证）
#   ./deploy/migrate-export.sh --stop               # 打包前停服务，打完再起
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
DRY_RUN=0
# shellcheck source=deploy/lib.sh
. "$ROOT/deploy/lib.sh"
load_conf
setup_path

OUT=""
WITH_SECRETS=0
WITH_SESSIONS=1
WITH_MEDIA=0
WITH_LOGS=0
WITH_QQ_LOGIN=0
STOP=0

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output) OUT="$2"; shift 2 ;;
    --with-secrets) WITH_SECRETS=1; shift ;;
    --with-sessions) WITH_SESSIONS=1; shift ;;
    --no-sessions) WITH_SESSIONS=0; shift ;;
    --with-media) WITH_MEDIA=1; shift ;;
    --with-logs) WITH_LOGS=1; shift ;;
    --with-qq-login) WITH_QQ_LOGIN=1; shift ;;
    --stop) STOP=1; shift ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "未知参数: $1" ;;
  esac
done

[ "$HOME" = "$BOT_HOME" ] || die "导出要在 $BOT_HOME 对应用户下跑（当前 HOME=$HOME）"

STAMP="$(date +%Y%m%d-%H%M)"
OUT="${OUT:-$HOME/qqbot-migrate-$STAMP.tar.gz}"
STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

restart_services() {
  [ "$STOP" = 1 ] || return 0
  systemctl --user start dsh-web.service 2>/dev/null || true
  [ "$WITH_NAPCAT" = "1" ] && systemctl --user start napcat.service 2>/dev/null || true
  [ "$WITH_AGENT" = "1" ] && systemctl --user start dsh-agent.service 2>/dev/null || true
}
trap 'restart_services; cleanup' EXIT

if [ "$STOP" = 1 ]; then
  step "暂停服务（保证会话文件一致）"
  systemctl --user stop dsh-agent.service dsh-web.service napcat.service 2>/dev/null || true
  sleep 2
fi

step "收集文件"
copy() { # copy <相对 $HOME 的路径>
  local rel=$1
  [ -e "$HOME/$rel" ] || { log "跳过（不存在）$rel"; return 0; }
  mkdir -p "$STAGE/$(dirname "$rel")"
  cp -a "$HOME/$rel" "$STAGE/$rel"
  log "  + $rel"
}

# 机器人配置与记忆
for p in \
  .dsh-user/group-wake.json \
  .dsh-user/sleep-window.json \
  .dsh-user/group-user-allow.json \
  .dsh-user/logrotate-napcat.conf \
  .dsh-user/storages \
  .dsh-user/proactive \
  qq-dsh-bot/persona-dafeiyu.md \
  qq-dsh-bot/persona-niannian.md \
  qq-dsh-bot/proactive-targets.txt \
  qq-dsh-bot/proactive-state.json \
  qq-dsh-bot/monthly-prompt.txt \
  qq-dsh-bot/image-lib \
  tts-out/stickers
do
  copy "$p"
done

# 会话（聊天上下文）
if [ "$WITH_SESSIONS" = 1 ]; then
  copy .dsh-user/sessions
fi

# 图片/附件
if [ "$WITH_MEDIA" = 1 ]; then
  copy .dsh-user/media
  copy .dsh-user/attachments
fi

# 常挂智能体的项目与记忆
if [ "$WITH_AGENT" = "1" ]; then
  for p in agent/MEMORY.md agent/GOAL.md agent/WORKLOG.md agent/NOTIFY.log \
           agent/state agent/projects agent/done agent/failed; do
    copy "$p"
  done
fi

# QQ 登录态（best effort：可能省一次扫码，也可能因设备验证失效）
if [ "$WITH_QQ_LOGIN" = 1 ]; then
  copy .config/QQ/global/nt_db
  copy .config/QQ/global/nt_data/Login
  copy .config/QQ/global/nt_data/mmkv
  for d in "$HOME"/.config/QQ/nt_qq_*; do
    [ -d "$d" ] || continue
    copy ".config/QQ/$(basename "$d")/nt_db"
    copy ".config/QQ/$(basename "$d")/nt_data/mmkv"
  done
fi

# 日志
if [ "$WITH_LOGS" = 1 ]; then
  for p in qq-dsh-bot/guard.log qq-dsh-bot/keepalive.log qq-dsh-bot/proactive.log \
           qq-dsh-bot/dsh-web.log qq-dsh-bot/watchdog.log agent/logs; do
    copy "$p"
  done
fi

# 密钥（可选）
if [ "$WITH_SECRETS" = 1 ]; then
  step "打包密钥（包里是明文，传完记得删）"
  for p in \
    .dsh-user/dsh-web.env \
    .dsh-user/.credentials.yaml \
    qq-dsh-bot/onebot-token.txt \
    qq-dsh-bot/napcat-webui.txt \
    tts-out/mimo-key.txt \
    tts-out/mureka-key.txt
  do
    copy "$p"
  done
fi

step "清单"
if [ "$DRY_RUN" = 0 ]; then
  {
    echo "qqbot-migrate manifest"
    echo "created:   $(date -Iseconds)"
    echo "bot_qq:    $BOT_QQ"
    echo "admin_qq:  $ADMIN_QQ"
    echo "host:      $(hostname)"
    echo "os:        $(. /etc/os-release && echo "$PRETTY_NAME")"
    echo "node:      $(node -v 2>/dev/null || echo '?')"
    echo "dsh:       $("$BOT_HOME/.local/share/pnpm/dsh" --version 2>/dev/null || echo '?')"
    echo "with_secrets:  $WITH_SECRETS"
    echo "with_sessions: $WITH_SESSIONS"
    echo "with_media:    $WITH_MEDIA"
    echo "with_qq_login: $WITH_QQ_LOGIN"
    echo "files:     $(find "$STAGE" -type f | wc -l)"
    echo "size:      $(du -sh "$STAGE" | cut -f1)"
  } > "$STAGE/manifest.txt"
  cat "$STAGE/manifest.txt"
fi

step "打包 -> $OUT"
if [ "$DRY_RUN" = 1 ]; then
  log "would tar $STAGE -> $OUT"
else
  tar -czf "$OUT" -C "$STAGE" .
  chmod 600 "$OUT"
  sha256sum "$OUT" | tee "$OUT.sha256"
  ok "完成: $OUT"
  if [ "$WITH_SECRETS" = 1 ]; then
    warn "包含密钥，别传群/别提交 git；导入后建议删掉这个包"
  fi
fi
