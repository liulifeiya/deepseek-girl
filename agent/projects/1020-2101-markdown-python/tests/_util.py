"""测试辅助：直接渲染 Markdown 文本。"""

from __future__ import annotations

from markdown_it import MarkdownIt

from md2txt.blocks import parse_tokens
from md2txt.render import Options, render_document


def make_md() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


def render(source: str, **options) -> str:
    opts = Options(**options)
    return render_document(parse_tokens(make_md().parse(source)), opts)
