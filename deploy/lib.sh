#!/usr/bin/env bash
# 部署脚本公共函数。所有 step 都 source 它。
# 约定：step 脚本从 install.sh 继承环境变量（BOT_HOME / BOT_QQ / ...），
# 自己不再解析参数。

set -euo pipefail

: "${ROOT:?ROOT 未设置（应由 install.sh 导出仓库根目录）}"

DRY_RUN="${DRY_RUN:-0}"
ASSUME_YES="${ASSUME_YES:-0}"

if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
  C_RESET=; C_BOLD=; C_DIM=; C_RED=; C_GREEN=; C_YELLOW=; C_BLUE=
fi

log()  { printf '%s[%s]%s %s\n' "$C_DIM" "$(date +%H:%M:%S)" "$C_RESET" "$*"; }
step() { printf '\n%s==> %s%s\n' "$C_BOLD" "$*" "$C_RESET"; }
ok()   { printf '%s  ok%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s[warn]%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()  { printf '%s[error]%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

# run <cmd...>：干跑时只打印
run() {
  if [ "$DRY_RUN" = 1 ]; then
    printf '  %s+%s %s\n' "$C_BLUE" "$C_RESET" "$*"
    return 0
  fi
  "$@"
}

# run_sh '<shell 串>'：需要管道/重定向时用
run_sh() {
  if [ "$DRY_RUN" = 1 ]; then
    printf '  %s+%s %s\n' "$C_BLUE" "$C_RESET" "$1"
    return 0
  fi
  bash -c "$1"
}

confirm() {
  [ "$ASSUME_YES" = 1 ] && return 0
  [ "$DRY_RUN" = 1 ] && return 0
  local answer
  read -r -p "$1 [y/N] " answer || true
  case "$answer" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

# 模板渲染：把 @NAME@ 换成同名环境变量
render() {
  local src=$1 dst=$2
  [ -f "$src" ] || die "模板不存在: $src"
  if [ "$DRY_RUN" = 1 ]; then
    printf '  %s+%s render %s -> %s\n' "$C_BLUE" "$C_RESET" "$src" "$dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  python3 - "$src" "$dst" <<'PY'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
for key in ("BOT_HOME", "BOT_QQ", "ADMIN_QQ", "ONEBOT_TOKEN", "GROUP_ALLOW",
            "GROUP_ALLOW_JSON", "DSH_PORT", "NAPCAT_WS_PORT", "DSH_HOME"):
    text = text.replace("@" + key + "@", os.environ.get(key, ""))
open(dst, "w", encoding="utf-8").write(text)
PY
}

# 复制单文件并给出权限；路径里的 @HOME@ 不做替换，由调用方传已渲染文件
copy_file() {
  local src=$1 dst=$2 mode=${3:-644}
  if [ "$DRY_RUN" = 1 ]; then
    printf '  %s+%s install -m %s %s %s\n' "$C_BLUE" "$C_RESET" "$mode" "$src" "$dst"
    return 0
  fi
  install -D -m "$mode" "$src" "$dst"
}

# 复制脚本并把老机器家目录/管理员号替换掉（迁移到别的用户名时用）
copy_script() {
  local src=$1 dst=$2 mode=${3:-755}
  if [ "$DRY_RUN" = 1 ]; then
    printf '  %s+%s install -m %s %s %s（替换 /home/ubuntu）\n' "$C_BLUE" "$C_RESET" "$mode" "$src" "$dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  sed -e "s|/home/ubuntu|$BOT_HOME|g" \
      -e "s|\b2812108776\b|$ADMIN_QQ|g" \
      -e "s|\b2836148023\b|$BOT_QQ|g" \
      "$src" > "$dst"
  chmod "$mode" "$dst"
}

# 备份已存在的文件（覆盖前用）
backup_file() {
  local f=$1
  [ -e "$f" ] || return 0
  local bak="${f}.bak-$(date +%Y%m%d%H%M%S)"
  run cp -a "$f" "$bak"
  log "已备份 $f -> $bak"
}

apt_install() {
  [ "$#" -gt 0 ] || return 0
  if ! have apt-get; then
    warn "非 apt 系统，跳过自动装包: $*"
    return 0
  fi
  local sudo=()
  [ "$(id -u)" -ne 0 ] && sudo=(sudo)
  run "${sudo[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@"
}

need_sudo() {
  if [ "$(id -u)" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    warn "接下来需要 sudo 权限（会提示输密码）"
  fi
}

# 读配置：deploy.conf 覆盖 deploy.conf.example
load_conf() {
  local conf="${DEPLOY_CONF:-$ROOT/deploy/deploy.conf}"
  local example="$ROOT/deploy/deploy.conf.example"

  if [ -f "$conf" ]; then
    set -a; . "$conf"; set +a
  elif [ -f "$example" ]; then
    warn "没有 deploy/deploy.conf，先用示例值（复制一份再改）"
    set -a; . "$example"; set +a
  else
    die "找不到 deploy/deploy.conf 或 deploy.conf.example"
  fi

  BOT_HOME="${BOT_HOME:-/home/ubuntu}"
  BOT_QQ="${BOT_QQ:-}"
  ADMIN_QQ="${ADMIN_QQ:-}"
  DSH_HOME="${DSH_HOME:-$BOT_HOME/.dsh-user}"
  DSH_PORT="${DSH_PORT:-3080}"
  NAPCAT_WS_PORT="${NAPCAT_WS_PORT:-3001}"
  DSH_VERSION="${DSH_VERSION:-0.2.0-rc.2}"
  NODE_VERSION="${NODE_VERSION:-24.19.0}"
  WITH_NAPCAT="${WITH_NAPCAT:-1}"
  WITH_TTS="${WITH_TTS:-1}"
  WITH_AGENT="${WITH_AGENT:-1}"
  GROUP_ALLOW="${GROUP_ALLOW:-}"

  # 群白名单 -> JSON 数组片段（"100...","877..."）
  GROUP_ALLOW_JSON=""
  for g in $GROUP_ALLOW; do
    GROUP_ALLOW_JSON="${GROUP_ALLOW_JSON}\"${g}\","
  done
  GROUP_ALLOW_JSON="${GROUP_ALLOW_JSON%,}"

  [ -n "$BOT_QQ" ] || die "deploy.conf 里 BOT_QQ 不能为空"
  [ -n "$ADMIN_QQ" ] || die "deploy.conf 里 ADMIN_QQ 不能为空"
  [ -n "${ONEBOT_TOKEN:-}" ] || die "deploy.conf 里 ONEBOT_TOKEN 不能为空（NapCat WS 和 dsh 两端要一致）"
  case "$ONEBOT_TOKEN" in
    REPLACE_*|change-me*) die "deploy.conf 里的 ONEBOT_TOKEN 还是占位符，先生成: openssl rand -hex 32" ;;
  esac

  export BOT_HOME BOT_QQ ADMIN_QQ DSH_HOME DSH_PORT NAPCAT_WS_PORT \
         DSH_VERSION NODE_VERSION WITH_NAPCAT WITH_TTS WITH_AGENT GROUP_ALLOW GROUP_ALLOW_JSON \
         ONEBOT_TOKEN ROOT DRY_RUN ASSUME_YES
  export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
  export MIMO_API_KEY="${MIMO_API_KEY:-}"
  export MUREKA_API_KEY="${MUREKA_API_KEY:-}"
  export PIP_INDEX_URL="${PIP_INDEX_URL:-}"
}

# 统一 PATH：node/pnpm 装在家目录，不依赖登录 shell
setup_path() {
  local home="${BOT_HOME:-$HOME}"
  export PATH="$home/.local/node/bin:$home/.local/share/pnpm:$home/.local/bin:/usr/local/bin:/usr/bin:/bin"
}
