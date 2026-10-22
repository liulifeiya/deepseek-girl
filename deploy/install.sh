#!/usr/bin/env bash
# 一键部署：把仓库里的配置/补丁/脚本装成一套能跑的 QQ 机器人。
#
#   cp deploy/deploy.conf.example deploy/deploy.conf   # 填 QQ、token、key
#   ./deploy/install.sh --dry-run                      # 先看要做什么
#   ./deploy/install.sh                                # 真装
#
# 常用参数：
#   --dry-run            只打印，不动系统
#   --yes                不逐项确认
#   --conf FILE          指定配置文件
#   --only 30,40         只跑指定编号的步骤
#   --skip napcat,tts    跳过组件（也可在 deploy.conf 里关）
#   --no-start           装完不启动（先导入数据时用）
#   --list               列出步骤
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT

DRY_RUN=0
ASSUME_YES=0
ONLY=""
SKIP=""
NO_START=0

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --conf) DEPLOY_CONF="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --skip) SKIP="$2"; shift 2 ;;
    --no-start) NO_START=1; shift ;;
    --list)
      printf '%s\n' 10-base 20-dsh 30-plugins 40-botfiles 50-tts 60-agent 70-napcat 80-services
      exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage; exit 1 ;;
  esac
done

export DRY_RUN ASSUME_YES NO_START
# shellcheck source=deploy/lib.sh
. "$ROOT/deploy/lib.sh"

CONF="${DEPLOY_CONF:-$ROOT/deploy/deploy.conf}"
if [ ! -f "$CONF" ]; then
  if [ "$DRY_RUN" = 1 ]; then
    warn "没有 $CONF，干跑用示例值"
  else
    cp "$ROOT/deploy/deploy.conf.example" "$CONF"
    chmod 600 "$CONF"
    die "已生成 $CONF，填好 BOT_QQ / ONEBOT_TOKEN / DEEPSEEK_API_KEY 再跑一次"
  fi
fi
load_conf
setup_path

[ "$HOME" = "$BOT_HOME" ] || die "请用 $BOT_HOME 对应的用户运行（当前 HOME=$HOME），或改 deploy.conf 的 BOT_HOME"

# 组件开关与 --skip 合并
IFS=',' read -r -a skip_items <<< "$SKIP"
for s in "${skip_items[@]:-}"; do
  case "$s" in
    napcat) WITH_NAPCAT=0 ;;
    tts) WITH_TTS=0 ;;
    agent) WITH_AGENT=0 ;;
    "") ;;
    *) warn "未知 --skip 项: $s" ;;
  esac
done

ALL_STEPS=(10-base 20-dsh 30-plugins 40-botfiles 50-tts 60-agent 70-napcat 80-services)
if [ -n "$ONLY" ]; then
  STEPS=()
  IFS=',' read -r -a wanted <<< "$ONLY"
  for w in "${wanted[@]}"; do
    for s in "${ALL_STEPS[@]}"; do
      case "$s" in "$w"*) STEPS+=("$s") ;; esac
    done
  done
  [ "${#STEPS[@]}" -gt 0 ] || die "--only 没匹配到步骤"
else
  STEPS=("${ALL_STEPS[@]}")
fi

printf '%s\n' "────────────────────────────────────────────"
printf '  仓库:   %s\n' "$ROOT"
printf '  家目录: %s\n' "$BOT_HOME"
printf '  机器人: %s  管理员: %s\n' "$BOT_QQ" "$ADMIN_QQ"
printf '  步骤:   %s\n' "${STEPS[*]}"
printf '  模式:   %s\n' "$([ "$DRY_RUN" = 1 ] && echo 干跑 || echo 实际执行)"
printf '%s\n' "────────────────────────────────────────────"

confirm "按上面的计划执行？" || { log "已取消"; exit 0; }

for s in "${STEPS[@]}"; do
  f="$ROOT/deploy/steps/$s.sh"
  [ -f "$f" ] || die "缺步骤文件: $f"
  bash "$f"
done

step "收尾检查"
if [ "$DRY_RUN" = 0 ]; then
  failed=0
  for u in dsh-web.service; do
    systemctl --user is-active --quiet "$u" || { warn "$u 没起来"; failed=1; }
  done
  [ "$WITH_NAPCAT" = "1" ] && { systemctl --user is-active --quiet napcat.service || warn "napcat.service 没起来（可能要扫码）"; }
  if [ "$failed" = 0 ]; then ok "dsh-web 运行中"; fi
fi

cat <<EOF

下一步：
  1) 首次装 NapCat 要扫码登录：
       systemctl --user status napcat.service
       $BOT_HOME/tts-venv/bin/python $BOT_HOME/qq-dsh-bot/qr-term.py
  2) 看日志：
       journalctl --user -u dsh-web -n 50 --no-pager
       tail -f $BOT_HOME/qq-dsh-bot/dsh-web.log
  3) 老机器迁移数据（人设/记忆/会话/白名单）：
       ./deploy/migrate-export.sh --with-secrets     # 老机器
       ./deploy/migrate-import.sh ~/qqbot-migrate-*.tar.gz   # 新机器
  完整步骤见 docs/MIGRATION.md
EOF
