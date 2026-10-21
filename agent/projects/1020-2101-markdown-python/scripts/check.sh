#!/usr/bin/env bash
# 开发期快速自检：编译 + 单元测试 + 基本冒烟。
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m compileall -q md2txt
python3 -m unittest discover -s tests -v

out=$(printf '# 你好\n\nHello **world**.\n' | python3 -m md2txt)
[ "$out" = $'你好\n\nHello world.' ] || { echo "冒烟失败: $out" >&2; exit 1; }

printf '# Hi\n' | python3 -m md2txt --heading-style underline | grep -qx '=='
printf '' | python3 -m md2txt | wc -c | grep -qx '0'

echo "check.sh: ALL OK"
