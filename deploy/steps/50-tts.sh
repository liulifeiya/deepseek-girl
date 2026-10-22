#!/usr/bin/env bash
# 50-tts：TTS/音乐/表情包脚本的 Python 环境
source "$(dirname "$0")/../lib.sh"
setup_path

[ "$WITH_TTS" = "1" ] || { log "WITH_TTS=0，跳过"; exit 0; }

VENV="$BOT_HOME/tts-venv"
OUT="$BOT_HOME/tts-out"

step "脚本与素材: $OUT"
run mkdir -p "$OUT/stickers"
for f in mimo-tts.py mureka-music.py meme.py draw2.py; do
  copy_script "$ROOT/tts/$f" "$OUT/$f"
done

step "API Key"
for pair in "MIMO_API_KEY:mimo-key.txt" "MUREKA_API_KEY:mureka-key.txt"; do
  var="${pair%%:*}"; file="${pair#*:}"
  val="${!var:-}"
  if [ -z "$val" ]; then
    log "$var 为空，跳过 $file（用到时再补）"
    continue
  fi
  if [ "$DRY_RUN" = 1 ]; then
    log "would write $OUT/$file"
  else
    printf '%s\n' "$val" > "$OUT/$file"
    chmod 600 "$OUT/$file"
    ok "$file 已写入"
  fi
done

step "Python venv: $VENV"
if [ ! -x "$VENV/bin/python" ]; then
  run python3 -m venv "$VENV"
fi

if [ "$DRY_RUN" = 1 ]; then
  run "$VENV/bin/pip" install --retries 2 --timeout 20 -r "$ROOT/deploy/requirements.txt"
else
  # 国内机器可以设 PIP_INDEX_URL 换镜像（见 deploy.conf.example）
  pip_args=(--retries 2 --timeout 20 --disable-pip-version-check)
  [ -n "${PIP_INDEX_URL:-}" ] && pip_args+=(-i "$PIP_INDEX_URL")
  if "$VENV/bin/pip" install -q "${pip_args[@]}" -r "$ROOT/deploy/requirements.txt"; then
    ok "python 依赖已装: $("$VENV/bin/python" -c 'import PIL;print("pillow",PIL.__version__)' 2>/dev/null || echo '?')"
  else
    warn "python 依赖没装全（网络/PyPI 源？）。机器人主流程不受影响，"
    warn "要用语音/表情包时重跑： ./deploy/install.sh --only 50 --yes"
    warn "或换源： PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ./deploy/install.sh --only 50"
  fi
fi

ok "TTS 层完成"
