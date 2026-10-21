"""markdown-it token 流 → 中间块模型。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_TASK_PREFIX = re.compile(r"^\[([ xX])\]\s+")
_ALIGN = re.compile(r"text-align:\s*(left|right|center)")


@dataclass
class Node:
    kind: str
    level: int = 0
    tokens: list[Any] = field(default_factory=list)
    text: str = ""
    children: list["Node"] = field(default_factory=list)
    ordered: bool = False
    start: int = 1
    items: list["Node"] = field(default_factory=list)
    checked: bool | None = None
    rows: list[list[list[Any]]] = field(default_factory=list)
    aligns: list[str] = field(default_factory=list)
    header_rows: int = 0


def _attr_int(token: Any, name: str, default: int) -> int:
    raw = token.attrGet(name)
    try:
        return int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


def _parse_table(tokens: list[Any], i: int) -> tuple[Node, int]:
    node = Node(kind="table")
    row: list[list[Any]] = []
    in_head = False
    while i < len(tokens):
        token = tokens[i]
        ttype = token.type
        if ttype == "table_close":
            return node, i
        if ttype == "thead_open":
            in_head = True
        elif ttype == "thead_close":
            in_head = False
        elif ttype == "tr_open":
            row = []
        elif ttype == "tr_close":
            node.rows.append(row)
            if in_head:
                node.header_rows += 1
        elif ttype in ("th_open", "td_open"):
            style = token.attrGet("style") or ""
            match = _ALIGN.search(style)
            node.aligns.append(match.group(1) if match else "left")
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                row.append(tokens[i + 1].children)
            else:
                row.append([])
        i += 1
    return node, i


def _maybe_task(item: Node) -> None:
    if not item.children:
        return
    first = item.children[0]
    if first.kind != "paragraph" or not first.tokens:
        return
    head = first.tokens[0]
    if head.type != "text":
        return
    match = _TASK_PREFIX.match(head.content)
    if not match:
        return
    item.checked = match.group(1).lower() == "x"
    head.content = head.content[match.end():]


def _parse_blocks(tokens: list[Any], i: int, stop: str | None) -> tuple[list[Node], int]:
    nodes: list[Node] = []
    while i < len(tokens):
        token = tokens[i]
        ttype = token.type
        if stop is not None and ttype == stop:
            return nodes, i

        if ttype in ("heading_open", "paragraph_open"):
            kind = "heading" if ttype == "heading_open" else "paragraph"
            level = int(token.tag[1]) if kind == "heading" else 0
            inline = tokens[i + 1].children if i + 1 < len(tokens) else []
            close = "heading_close" if kind == "heading" else "paragraph_close"
            nodes.append(Node(kind=kind, level=level, tokens=inline))
            i += 2
            while i < len(tokens) and tokens[i].type != close:
                i += 1
            i += 1
            continue

        if ttype in ("fence", "code_block"):
            content = token.content
            lines = content.split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            nodes.append(Node(kind="code", text="\n".join(lines)))
            i += 1
            continue

        if ttype == "hr":
            nodes.append(Node(kind="hr"))
            i += 1
            continue

        if ttype == "blockquote_open":
            children, i = _parse_blocks(tokens, i + 1, "blockquote_close")
            nodes.append(Node(kind="blockquote", children=children))
            i += 1
            continue

        if ttype in ("bullet_list_open", "ordered_list_open"):
            ordered = ttype == "ordered_list_open"
            close = "ordered_list_close" if ordered else "bullet_list_close"
            start = _attr_int(token, "start", 1) if ordered else 1
            node = Node(kind="list", ordered=ordered, start=start)
            i += 1
            while i < len(tokens) and tokens[i].type != close:
                if tokens[i].type == "list_item_open":
                    children, i = _parse_blocks(tokens, i + 1, "list_item_close")
                    item = Node(kind="item", children=children)
                    _maybe_task(item)
                    node.items.append(item)
                    i += 1
                else:
                    i += 1
            nodes.append(node)
            i += 1
            continue

        if ttype == "table_open":
            node, i = _parse_table(tokens, i + 1)
            nodes.append(node)
            i += 1
            continue

        if ttype == "html_block":
            nodes.append(Node(kind="html", text=token.content))
            i += 1
            continue

        i += 1

    return nodes, i


def parse_tokens(tokens: list[Any]) -> list[Node]:
    """把 token 流解析为块节点列表。"""
    nodes, _ = _parse_blocks(tokens, 0, None)
    return nodes
