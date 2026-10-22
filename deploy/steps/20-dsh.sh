#!/usr/bin/env bash
# 20-dsh：Node + pnpm + dsh（版本锁死，避免插件补丁对不上）
source "$(dirname "$0")/../lib.sh"
setup_path

step "Node.js"
need_node=1
if have node; then
  cur="$(node -v | sed 's/^v//')"
  log "已有 node v$cur，目标 v$NODE_VERSION"
  [ "$cur" = "$NODE_VERSION" ] && need_node=0
fi

if [ "$need_node" = 1 ]; then
  case "$(uname -m)" in
    x86_64) arch=x64 ;;
    aarch64) arch=arm64 ;;
    *) die "不支持的架构: $(uname -m)" ;;
  esac
  pkg="node-v${NODE_VERSION}-linux-${arch}.tar.xz"
  url="https://nodejs.org/dist/v${NODE_VERSION}/${pkg}"
  tmp="$(mktemp -d)"
  log "下载 $url"
  run curl -fL --retry 3 --connect-timeout 20 -o "$tmp/$pkg" "$url"
  run tar -xJf "$tmp/$pkg" -C "$BOT_HOME/.local"
  run rm -rf "$BOT_HOME/.local/node"
  run mv "$BOT_HOME/.local/node-v${NODE_VERSION}-linux-${arch}" "$BOT_HOME/.local/node"
  run rm -rf "$tmp"
  export PATH="$BOT_HOME/.local/node/bin:$PATH"
  ok "node $(node -v)"
else
  ok "node 已是目标版本"
fi

step "pnpm"
if ! have pnpm; then
  run corepack enable
  run corepack prepare "pnpm@${PNPM_VERSION:-10.34.5}" --activate
fi
have pnpm || die "pnpm 没装上，检查 corepack"
ok "pnpm $(pnpm -v)"

step "dsh @${DSH_VERSION}"
DSH_BIN="$BOT_HOME/.local/share/pnpm/dsh"
if [ -x "$DSH_BIN" ] && "$DSH_BIN" --version 2>/dev/null | grep -q "$DSH_VERSION"; then
  ok "dsh $DSH_VERSION 已安装"
else
  run env PNPM_HOME="$BOT_HOME/.local/share/pnpm" \
      pnpm add -g "@deepseek-ai/dsh@${DSH_VERSION}"
fi

[ -x "$DSH_BIN" ] || die "dsh 没装到 $DSH_BIN，检查 pnpm 全局 bin 目录"
# 注意：~/.local/node/bin 里可能还有一份 npm 全局的 dsh，版本可能不同。
# systemd 单元固定用 .local/share/pnpm/dsh，避免踩到另一份。
ok "dsh $("$DSH_BIN" --version 2>/dev/null || echo '?')"
