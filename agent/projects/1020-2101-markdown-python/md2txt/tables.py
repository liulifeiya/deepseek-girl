"""GFM 表格渲染：aligned / tsv / pipe 三种风格。"""

from __future__ import annotations

from typing import Any

from .inline import render_inline
from .width import display_width, pad


def _cell_text(tokens: list[Any], links: str, keep_html: bool) -> str:
    return "".join(text for text, _ in render_inline(tokens, links, keep_html))


def render_table(node: Any, style: str, links: str = "inline", keep_html: bool = False,
                 wrap: int = 0) -> list[str]:
    """渲染表格节点为若干行文本；表格不参与折行。"""
    if not node.rows:
        return []
    columns = max(len(row) for row in node.rows)
    if columns == 0:
        return []

    rows: list[list[str]] = []
    for row in node.rows:
        cells = [_cell_text(cell, links, keep_html) for cell in row]
        if len(cells) < columns:
            cells.extend([""] * (columns - len(cells)))
        rows.append(cells[:columns])

    aligns = list(node.aligns[:columns]) + ["left"] * max(0, columns - len(node.aligns))

    if style == "tsv":
        out = []
        for row in rows:
            cells = [cell.replace("\t", " ").replace("\n", " ") for cell in row]
            out.append("\t".join(cells))
        return out

    if style == "pipe":
        out = ["| " + " | ".join(row) + " |" for row in rows]
        out.insert(1, "| " + " | ".join(["---"] * columns) + " |")
        return out

    widths = [max(display_width(row[col]) for row in rows) for col in range(columns)]
    widths = [max(width, 1) for width in widths]
    out = []
    for index, row in enumerate(rows):
        cells = [pad(cell, widths[col], aligns[col]) for col, cell in enumerate(row)]
        out.append("  ".join(cells).rstrip(" "))
        if index == 0:
            out.append("  ".join("-" * widths[col] for col in range(columns)))
    return out
