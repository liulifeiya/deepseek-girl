"""显示宽度计算与按宽度折行。

CJK 宽字符按 2 列计算，组合字符按 0 列；emoji 近似按 2 列处理。
仅依赖标准库 unicodedata。
"""

from __future__ import annotations

import unicodedata

_ZERO_CATEGORIES = frozenset({"Mn", "Me", "Cf"})


def char_width(ch: str) -> int:
    """返回单个字符的显示宽度（0/1/2）。"""
    if ch in ("\n", "\r", "\t"):
        return 0
    if unicodedata.combining(ch):
        return 0
    if unicodedata.category(ch) in _ZERO_CATEGORIES:
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(text: str) -> int:
    """返回字符串的显示宽度，换行符不计入。"""
    return sum(char_width(ch) for ch in text)


def pad(text: str, width: int, align: str = "left") -> str:
    """把 text 补齐到 width 显示列。align 支持 left/right/center。"""
    gap = max(0, width - display_width(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def _tokenize(parts: list[tuple[str, bool]]) -> list[tuple[str, str, int]]:
    """把行内片段转成折行 token：word / space / break / atom。"""
    tokens: list[tuple[str, str, int]] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            text = "".join(buf)
            tokens.append(("word", text, display_width(text)))
            buf.clear()

    for text, atomic in parts:
        if atomic:
            flush()
            tokens.append(("atom", text, display_width(text)))
            continue
        for ch in text:
            if ch == "\n":
                flush()
                tokens.append(("break", "\n", 0))
            elif ch in (" ", "\t"):
                flush()
                if not tokens or tokens[-1][0] != "space":
                    tokens.append(("space", " ", 1))
            elif char_width(ch) == 2:
                flush()
                tokens.append(("word", ch, 2))
            else:
                buf.append(ch)
    flush()
    return tokens


def wrap_parts(
    parts: list[tuple[str, bool]],
    width: int,
    first_indent: str = "",
    next_indent: str = "",
) -> list[str]:
    """按显示宽度折行；原子片段（URL/行内代码）不拆断。

    parts 为 (文本, 是否原子) 列表；文本中的 ``\\n`` 视为强制换行。
    """
    if width <= 0:
        text = "".join(text for text, _ in parts)
        lines = text.split("\n")
        return [line.rstrip(" ") for line in lines]

    tokens = _tokenize(parts)
    lines: list[str] = []
    line = first_indent
    line_w = display_width(first_indent)
    at_start = True
    pending_space = False

    def flush() -> None:
        lines.append(line.rstrip(" "))

    for kind, text, tw in tokens:
        if kind == "break":
            flush()
            line = next_indent
            line_w = display_width(next_indent)
            at_start = True
            pending_space = False
            continue
        if kind == "space":
            if not at_start:
                pending_space = True
            continue
        sep = 1 if pending_space else 0
        if not at_start and line_w + sep + tw > width:
            flush()
            line = next_indent
            line_w = display_width(next_indent)
            at_start = True
            sep = 0
        if pending_space and not at_start:
            line += " "
            line_w += 1
        line += text
        line_w += tw
        at_start = False
        pending_space = False

    flush()
    return lines
