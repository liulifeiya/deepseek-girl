"""HTML 转纯文本：删除标签、保留可见文本、清理脚本与样式。"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
        "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4",
        "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
    }
)
SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "canvas"})

_TRAILING_SPACE = re.compile(r"[ \t]+\n")
_INLINE_SPACE = re.compile(r"[ \t]{2,}")
_MANY_NEWLINES = re.compile(r"\n{3,}")


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0
        self._pre_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "pre":
            self._pre_depth += 1
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if tag == "pre" and self._pre_depth:
            self._pre_depth -= 1
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self.parts.append(data)

    def handle_comment(self, data: str) -> None:
        return

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        raw = _TRAILING_SPACE.sub("\n", raw)
        raw = _INLINE_SPACE.sub(" ", raw)
        raw = _MANY_NEWLINES.sub("\n\n", raw)
        return raw.strip("\n")


def html_to_text(raw: str, keep_html: bool = False) -> str:
    """把一段 HTML 转为纯文本。

    keep_html=True 时保留标签本身，但仍然解码实体。
    """
    if keep_html:
        return html.unescape(raw)
    parser = _Extractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:  # 病态 HTML 不应让转换崩溃
        return html.unescape(re.sub(r"<[^>]*>", "", raw))
    return parser.text()
