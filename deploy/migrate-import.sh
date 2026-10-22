#!/usr/bin/env bash
# 新机器导入：把 migrate-export.sh 打的包还原到家目录。
# 先跑 install.sh（建议 --no-start），再跑这个，最后启动服务。
#
#   ./deploy/migrate-import.sh ~/qqbot-migrate-20261022-2130.tar.gz
#   ./deploy/migrate-import.sh 包.tar.gz --dry-run
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
DRY_RUN=0
# shellcheck source=deploy/lib.sh
. "$ROOT/deploy/lib.sh"
load_conf
setup_path

ARCHIVE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) die "未知参数: $1" ;;
    *) ARCHIVE="$1"; shift ;;
  esac
done

[ -n "$ARCHIVE" ] || die "用法: $0 <迁移包.tar.gz>"
[ -f "$ARCHIVE" ] || die "找不到: $ARCHIVE"
[ "$HOME" = "$BOT_HOME" ] || die "导入要在 $BOT_HOME 对应用户下跑（当前 HOME=$HOME）"

step "校验包"
if [ -f "$ARCHIVE.sha256" ]; then
  ( cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256" ) \
    || die "sha256 对不上，包损坏或被改过"
else
  warn "没有 .sha256 文件，跳过校验"
fi

step "检查路径安全性"
bad="$(tar -tzf "$ARCHIVE" | grep -E '(^/|(^|/)\.\.(/|$))' || true)"
[ -z "$bad" ] || die "包里有可疑路径:
$bad"
ok "路径正常"

step "包内容"
tar -tzf "$ARCHIVE" | head -20 || true
printf '  ... 共 %s 项\n' "$(tar -tzf "$ARCHIVE" | wc -l)"

if [ -f "$ARCHIVE" ]; then
  tmpm="$(mktemp -d)"
  tar -xzf "$ARCHIVE" -C "$tmpm" ./manifest.txt 2>/dev/null && cat "$tmpm/manifest.txt" || true
  rm -rf "$tmpm"
fi

step "备份现有配置"
for p in .dsh-user/group-wake.json .dsh-user/sleep-window.json qq-dsh-bot/onebot-token.txt; do
  [ -e "$HOME/$p" ] && backup_file "$HOME/$p"
done

step "还原到 $HOME"
if [ "$DRY_RUN" = 1 ]; then
  log "would tar -xzf $ARCHIVE -C $HOME"
else
  tar -xzf "$ARCHIVE" -C "$HOME" --exclude='./manifest.txt'
  ok "已还原"
fi

step "修权限"
if [ "$DRY_RUN" = 0 ]; then
  chmod 700 "$HOME/.dsh-user" 2>/dev/null || true
  chmod 600 "$HOME/qq-dsh-bot/onebot-token.txt" "$HOME/.dsh-user/dsh-web.env" 2>/dev/null || true
  chmod 600 "$HOME/tts-out/"*key.txt 2>/dev/null || true
  chmod 755 "$HOME/qq-dsh-bot/patches/"*.sh 2>/dev/null || true
  ok "权限已修"
fi

cat <<EOF

导入完成。接下来：
  1) 如果还没装环境： ./deploy/install.sh --no-start
  2) 确认 QQ 号/token 与 deploy.conf 一致：
       grep -E "botQQ|accessToken" $DSH_HOME/profiles/web/cordis.patch.yml
  3) 启动：
       systemctl --user restart dsh-web.service
       systemctl --user restart qq-guard.service qq-keepalive.service
  4) 看会话是否接上： tail -n 50 $HOME/qq-dsh-bot/dsh-web.log
EOF
