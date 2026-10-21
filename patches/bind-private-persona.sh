#!/bin/bash
# 私聊固定人设 1（大肥鱼·十二三岁）。
# dsh-web 启动时（ExecStartPost）跑一次；dsh-persona-bind.timer 每 60 秒兜底一次，
# 兼顾 /new 之后生成的新会话 id。
set -u
API='http://127.0.0.1:3080/api/dsh-persona-dafeiyu'
PID='custom-mvi5y8pv'
SESSIONS='/home/ubuntu/.dsh-user/sessions/--home-ubuntu--'

# 等 API 就绪（启动时用；timer 跑的时候通常一次就过）
for _ in $(seq 1 30); do
  curl -sf "$API/status" >/dev/null 2>&1 && break
  sleep 2
done

curl -s -X POST "$API/mutate" -H 'Content-Type: application/json' \
  -d '{"action":"set-mode","mode":"session"}' >/dev/null

# 主会话 + 所有 /new 出来的私聊会话
{
  echo 'onebot-private-2812108776'
  for d in "$SESSIONS"/onebot-private-2812108776*; do
    [ -d "$d" ] && basename "$d"
  done
} | sort -u | while read -r sid; do
  [ -n "$sid" ] || continue
  curl -s -X POST "$API/mutate" -H 'Content-Type: application/json' \
    -d "{\"action\":\"set-session-persona\",\"sessionId\":\"$sid\",\"personaId\":\"$PID\"}" >/dev/null
done

# 群 877935643 固定人设 3（鲸鱼娘）
GROUP_PID='custom-mvi6xf9s'
for d in "$SESSIONS"/onebot-group-877935643*; do
  [ -d "$d" ] || continue
  sid=$(basename "$d")
  curl -s -X POST "$API/mutate" -H 'Content-Type: application/json' \
    -d "{\"action\":\"set-session-persona\",\"sessionId\":\"$sid\",\"personaId\":\"$GROUP_PID\"}" >/dev/null
done
