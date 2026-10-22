#!/usr/bin/env bash
# 80-services：systemd 用户服务（不需要 root，但要 linger）
source "$(dirname "$0")/../lib.sh"
setup_path

UNIT_DIR="$HOME/.config/systemd/user"
SRC="$ROOT/deploy/templates/systemd"

step "生成 systemd 用户单元: $UNIT_DIR"
run mkdir -p "$UNIT_DIR"
for tpl in "$SRC"/*.tpl; do
  name="$(basename "$tpl" .tpl)"
  render "$tpl" "$UNIT_DIR/$name"
done
render "$ROOT/deploy/templates/logrotate-napcat.conf.tpl" "$DSH_HOME/logrotate-napcat.conf"

step "启用单元"
units=(dsh-web.service dsh-persona-bind.service dsh-daily-restart.timer \
       dsh-persona-bind.timer dsh-monthly.timer qq-proactive.timer)
[ "$WITH_NAPCAT" = "1" ] && units+=(napcat.service qq-guard.service qq-keepalive.service dsh-napcat-logrotate.timer)
[ "$WITH_AGENT" = "1" ] && units+=(dsh-agent.service)

if [ "$DRY_RUN" = 1 ]; then
  log "would systemctl --user enable ${units[*]}"
else
  systemctl --user daemon-reload
  systemctl --user enable "${units[@]}" >/dev/null
  ok "已 enable: ${units[*]}"
fi

step "开机自启（linger）"
if [ "$DRY_RUN" = 0 ]; then
  if loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q "Linger=yes"; then
    ok "linger 已开"
  else
    need_sudo
    sudo loginctl enable-linger "$USER" && ok "已开启 linger（重启后服务自己起来）"
  fi
fi

step "启动"
if [ "${NO_START:-0}" = "1" ]; then
  log "NO_START=1，先不启动（方便先导入数据）"
elif [ "$DRY_RUN" = 1 ]; then
  log "would systemctl --user restart dsh-web.service napcat.service qq-guard.service qq-keepalive.service dsh-agent.service"
else
  # napcat 要先起来，dsh 才连得上
  if [ "$WITH_NAPCAT" = "1" ]; then
    systemctl --user restart napcat.service
    for _ in $(seq 1 20); do
      systemctl --user is-active --quiet napcat.service && break
      sleep 1
    done
  fi
  systemctl --user restart dsh-web.service
  if [ "$WITH_NAPCAT" = "1" ]; then
    systemctl --user restart qq-guard.service qq-keepalive.service
  fi
  [ "$WITH_AGENT" = "1" ] && systemctl --user restart dsh-agent.service
  ok "服务已启动"
fi

step "状态"
if [ "$DRY_RUN" = 0 ]; then
  systemctl --user --no-pager --lines=0 status dsh-web.service 2>/dev/null | head -5 || true
  systemctl --user list-units --no-pager --state=running 'dsh-*' 'qq-*' 'napcat*' 2>/dev/null | head -12 || true
fi
ok "服务层完成"
