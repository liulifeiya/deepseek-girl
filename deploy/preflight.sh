#!/usr/bin/env bash
# 新机器体检：装之前先跑，避免装到一半发现缺东西。
#   ./deploy/preflight.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
DRY_RUN=0
# shellcheck source=deploy/lib.sh
. "$ROOT/deploy/lib.sh"
fails=0
check() { # check <描述> <命令...>
  local desc=$1; shift
  if "$@" >/dev/null 2>&1; then ok "$desc"; else warn "不满足: $desc"; fails=$((fails+1)); fi
}

step "系统"
. /etc/os-release
log "${PRETTY_NAME:-unknown} / $(uname -m)"
[ "${ID:-}" = "ubuntu" ] || [ "${ID:-}" = "debian" ] || warn "只在 Ubuntu/Debian 上验证过"
[ "$(uname -m)" = "x86_64" ] || warn "QQ/NapCat 只有 x86_64 包"

step "权限与 systemd"
if [ "$(id -u)" -eq 0 ]; then
  warn "当前是 root。建议用普通用户（如 ubuntu）跑，脚本内部按需 sudo"
else
  ok "非 root 用户: $USER"
fi
if sudo -n true 2>/dev/null; then
  ok "sudo 免密可用"
elif [ "$(id -u)" -eq 0 ]; then
  ok "root 直接可用"
else
  log "sudo 需要密码（装包时会提示，属正常）"
fi
check "systemd 用户实例可用" systemctl --user show-environment
check "loginctl 可用" command -v loginctl

step "资源"
mem_mb=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
disk_gb=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc '0-9')
log "内存 ${mem_mb}MB，$HOME 可用 ${disk_gb}GB"
[ "$mem_mb" -ge 1500 ] || warn "内存偏小，dsh + QQ 可能吃紧（建议 2G 以上）"
[ "$disk_gb" -ge 10 ] || warn "磁盘偏小，QQ 客户端 + NapCat 约 1G，建议留 10G 以上"

step "网络"
check "nodejs.org 可达" curl -fsSI --max-time 8 https://nodejs.org/dist/
check "npm registry 可达" curl -fsSI --max-time 8 https://registry.npmjs.org/
check "github.com 可达（NapCat/插件下载）" curl -fsSI --max-time 8 https://github.com/

step "端口"
for p in "${DSH_PORT:-3080}" "${NAPCAT_WS_PORT:-3001}" 6099; do
  if ss -lnt 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$p$"; then
    warn "端口 $p 已被占用（老机器还在跑？先停掉再迁移）"
  else
    ok "端口 $p 空闲"
  fi
done

step "已有安装"
for p in "$HOME/.dsh-user/profiles/web" "$HOME/Napcat/opt/QQ/qq" "$HOME/agent/worker.py"; do
  [ -e "$p" ] && warn "已存在: $p（install.sh 会覆盖配置，数据先导出）" || true
done

if [ "$fails" -gt 0 ]; then
  warn "有 $fails 项不满足，先处理再装"
  exit 1
fi
ok "体检通过，可以跑 ./deploy/install.sh --dry-run"
