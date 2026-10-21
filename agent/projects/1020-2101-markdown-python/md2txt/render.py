"""纯文本渲染：块模型 → 文本行。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .html_text import html_to_text
from .inline import render_inline
from .tables import render_table
from .width import display_width, wrap_parts


@dataclass
class Options:
    heading_style: str = "plain"
    links: str = "inline"
    table_style: str = "aligned"
    wrap: int = 0
    keep_frontmatter: bool = False
    keep_html: bool = False


def _strip_trailing(lines: list[str]) -> list[str]:
    return [line.rstrip(" ") for line in lines]


def _join_blocks(blocks: list[list[str]]) -> list[str]:
    out: list[str] = []
    for block in blocks:
        if not block:
            continue
        if out and out[-1] != "":
            out.append("")
        out.extend(block)
    while out and out[-1] == "":
        out.pop()
    while out and out[0] == "":
        out.pop(0)
    return out


def _paragraph(tokens: list[Any], opts: Options, width: int, softbreak: str = " ") -> list[str]:
    parts = render_inline(tokens, opts.links, opts.keep_html, softbreak=softbreak)
    if opts.wrap and width > 0:
        return _strip_trailing(wrap_parts(parts, width))
    return _strip_trailing("".join(text for text, _ in parts).split("\n"))


def _heading(node: Any, opts: Options) -> list[str]:
    parts = render_inline(node.tokens, opts.links, opts.keep_html)
    text = "".join(part for part, _ in parts).strip()
    if opts.heading_style == "atx":
        return ["#" * node.level + " " + text]
    if opts.heading_style == "underline":
        char = "=" if node.level == 1 else "-" if node.level == 2 else "~"
        return [text, char * max(1, display_width(text))]
    return [text]


def _join_item(children: list[Any], blocks: list[list[str]]) -> list[str]:
    out: list[str] = []
    for child, block in zip(children, blocks):
        if not block:
            continue
        if out and out[-1] != "" and child.kind != "list":
            out.append("")
        out.extend(block)
    while out and out[-1] == "":
        out.pop()
    return out


def _list(node: Any, opts: Options, width: int) -> list[str]:
    out: list[str] = []
    number = node.start
    for item in node.items:
        marker = f"{number}. " if node.ordered else "- "
        number += 1
        if item.checked is not None:
            marker += "[x] " if item.checked else "[ ] "
        child_width = max(0, width - display_width(marker)) if width else 0
        inner = _join_item(item.children, [_render(child, opts, child_width) for child in item.children])
        if not inner:
            out.append(marker.rstrip())
            continue
        indent = " " * display_width(marker)
        first = True
        for line in inner:
            if first:
                out.append(marker + line)
                first = False
            elif line == "":
                out.append("")
            else:
                out.append(indent + line)
    return out


def _blockquote(node: Any, opts: Options, width: int) -> list[str]:
    child_width = max(0, width - 2) if width else 0
    inner = _join_blocks([
        _render(child, opts, child_width, softbreak="\n") for child in node.children
    ])
    out = []
    for line in inner:
        out.append("> " + line if line else ">")
    return out


def _code(node: Any) -> list[str]:
    return node.text.split("\n") if node.text else []


def _html(node: Any, opts: Options, width: int) -> list[str]:
    text = html_to_text(node.text, keep_html=opts.keep_html)
    if not text:
        return []
    paragraphs = text.split("\n\n")
    out: list[str] = []
    for para in paragraphs:
        lines = para.split("\n")
        if opts.wrap and width > 0:
            out.extend(wrap_parts([(line, False) for line in lines], width))
        else:
            out.extend(lines)
        out.append("")
    if out and out[-1] == "":
        out.pop()
    return out


def _render(node: Any, opts: Options, width: int, softbreak: str = " ") -> list[str]:
    kind = node.kind
    if kind == "paragraph":
        return _paragraph(node.tokens, opts, width, softbreak=softbreak)
    if kind == "heading":
        return _heading(node, opts)
    if kind == "code":
        return _code(node)
    if kind == "hr":
        return ["---"]
    if kind == "list":
        return _list(node, opts, width)
    if kind == "blockquote":
        return _blockquote(node, opts, width)
    if kind == "table":
        return render_table(node, opts.table_style, opts.links, opts.keep_html)
    if kind == "html":
        return _html(node, opts, width)
    return []


def render_document(nodes: list[Any], opts: Options) -> str:
    """把块节点渲染为最终文本（不含末尾换行）。"""
    blocks = [_render(node, opts, opts.wrap) for node in nodes]
    lines = _join_blocks(blocks)
    return "\n".join(lines)
