#!/usr/bin/env bash
# 60-agent：常挂智能体（代码 + 目录，数据由 migrate-import 还原）
source "$(dirname "$0")/../lib.sh"
setup_path

[ "$WITH_AGENT" = "1" ] || { log "WITH_AGENT=0，跳过"; exit 0; }

A="$BOT_HOME/agent"
step "常挂智能体: $A"
run mkdir -p "$A"/{bin,inbox,done,failed,state,logs,work,projects,hooks}

copy_script "$ROOT/agent/worker.py"  "$A/worker.py"  644
copy_script "$ROOT/agent/project.py" "$A/project.py" 644
for f in agent qr.py; do
  copy_script "$ROOT/agent/bin/$f" "$A/bin/$f"
done

if [ ! -f "$A/GOAL.md" ] && [ "$DRY_RUN" = 0 ]; then
  cat > "$A/GOAL.md" <<'EOF'
# 长期目标

（写一两句你希望它长期推进的方向；空着也行，它只在 AUTONOMOUS 打开时看这里。）
EOF
fi
if [ ! -f "$A/MEMORY.md" ] && [ "$DRY_RUN" = 0 ]; then
  cat > "$A/MEMORY.md" <<'EOF'
# 长期记忆

（迁移时用 migrate-import.sh 还原老机器的 MEMORY.md，别在这里手写覆盖。）
EOF
fi
if [ ! -f "$A/WORKLOG.md" ] && [ "$DRY_RUN" = 0 ]; then
  printf '# 工作记录\n\n' > "$A/WORKLOG.md"
fi

ok "agent 层完成（自主推进默认关闭：touch $A/AUTONOMOUS 打开）"
