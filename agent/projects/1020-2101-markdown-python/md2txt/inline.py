"""行内 token → 纯文本片段。

片段用 ``(text, atomic)`` 表示；atomic=True 的片段（URL、行内代码、图片地址）
在折行时不会被拆断。
"""

from __future__ import annotations

from typing import Any

from .html_text import html_to_text

Part = tuple[str, bool]


def _plain(parts: list[Part]) -> str:
    return "".join(text for text, _ in parts)


def _append(parts: list[Part], text: str, atomic: bool = False) -> None:
    if not text:
        return
    if not atomic and parts and not parts[-1][1]:
        merged = parts[-1][0] + text
        parts[-1] = (merged, False)
    else:
        parts.append((text, atomic))


def _find_close(tokens: list[Any], start: int, open_type: str, close_type: str) -> int:
    depth = 0
    for i in range(start, len(tokens)):
        if tokens[i].type == open_type:
            depth += 1
        elif tokens[i].type == close_type:
            depth -= 1
            if depth == 0:
                return i
    return len(tokens) - 1


def _render_tokens(tokens: list[Any], links: str, keep_html: bool, softbreak: str = " ") -> list[Part]:
    parts: list[Part] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        ttype = token.type
        if ttype == "text":
            _append(parts, token.content)
        elif ttype == "code_inline":
            _append(parts, token.content, atomic=True)
        elif ttype == "softbreak":
            _append(parts, softbreak)
        elif ttype == "hardbreak":
            _append(parts, "\n")
        elif ttype == "html_inline":
            _append(parts, html_to_text(token.content, keep_html=keep_html))
        elif ttype in ("em_open", "em_close", "strong_open", "strong_close",
                       "s_open", "s_close"):
            pass
        elif ttype == "link_open":
            close = _find_close(tokens, i, "link_open", "link_close")
            inner_parts = _render_tokens(tokens[i + 1:close], links, keep_html, softbreak)
            inner = _plain(inner_parts).strip()
            href = token.attrGet("href") or ""
            is_auto = token.markup in ("autolink", "linkify")
            if links == "text":
                if inner:
                    _append(parts, inner)
                elif not is_auto:
                    _append(parts, href, atomic=True)
            elif is_auto:
                text = inner or href
                if text.startswith("mailto:") and inner:
                    text = inner
                _append(parts, text, atomic=True)
            elif not inner or inner == href or inner == href.removeprefix("mailto:"):
                _append(parts, href, atomic=True)
            else:
                _append(parts, inner + " (" + href + ")", atomic=True)
            i = close + 1
            continue
        elif ttype == "image":
            src = token.attrGet("src") or ""
            alt = token.content or ""
            if links == "text":
                _append(parts, alt or "[image]")
            elif alt:
                _append(parts, f"{alt} ({src})", atomic=True)
            else:
                _append(parts, f"[image] ({src})", atomic=True)
        i += 1
    return parts


def render_inline(tokens: list[Any], links: str = "inline", keep_html: bool = False,
                  softbreak: str = " ") -> list[Part]:
    """把 inline token 列表渲染为文本片段列表；softbreak 指定软换行输出。"""
    return _render_tokens(tokens, links, keep_html, softbreak)


def inline_text(tokens: list[Any], links: str = "inline", keep_html: bool = False) -> str:
    """把 inline token 列表渲染为单个字符串。"""
    return _plain(render_inline(tokens, links, keep_html))
