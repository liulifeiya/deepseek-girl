#!/usr/bin/env bash
# 10-base：系统依赖、时区、字体
source "$(dirname "$0")/../lib.sh"
setup_path

step "系统检查"
. /etc/os-release
log "系统: ${PRETTY_NAME:-unknown}"
case "${ID:-}" in
  ubuntu|debian) ;;
  *) warn "只在 Ubuntu/Debian 上验证过，继续但可能缺包" ;;
esac
[ "$(uname -m)" = "x86_64" ] || warn "napcat/QQ 只有 x86_64 的包，当前是 $(uname -m)"

if [ ! -d "$BOT_HOME" ]; then
  die "BOT_HOME 不存在: $BOT_HOME（先用该用户登录，或改 deploy.conf）"
fi

step "安装基础依赖"
pkgs=(curl ca-certificates git openssl jq unzip xvfb python3 python3-venv python3-pip fonts-noto-cjk)
missing=()
for p in "${pkgs[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
done

if [ "${#missing[@]}" -eq 0 ]; then
  ok "依赖齐全"
else
  need_sudo
  log "缺: ${missing[*]}"
  run sudo env DEBIAN_FRONTEND=noninteractive apt-get update -qq
  apt_install "${missing[@]}"
fi

step "时区"
tz="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
if [ "$tz" = "Asia/Shanghai" ]; then
  ok "时区已是 Asia/Shanghai"
else
  need_sudo
  warn "时区是 ${tz:-unknown}，机器人按北京时间判断睡眠/问候，改成 Asia/Shanghai"
  run sudo timedatectl set-timezone Asia/Shanghai
fi

step "目录"
run mkdir -p "$BOT_HOME/.local" "$BOT_HOME/qq-dsh-bot" "$BOT_HOME/napcat-setup" "$DSH_HOME"
ok "基础层完成"
