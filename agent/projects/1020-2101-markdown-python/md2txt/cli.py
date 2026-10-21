"""命令行入口：参数解析、输入输出与退出码。"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from markdown_it import MarkdownIt

from . import __version__
from .blocks import parse_tokens
from .loader import (InputError, read_path, read_stream, split_frontmatter,
                     strip_frontmatter, validate_encoding)
from .render import Options, render_document

PROG = "md2txt"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - argparse 分支
        self.exit(2, f"{PROG}: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=PROG,
        description="把 Markdown 转成纯文本；无文件参数时从 stdin 读取。",
        epilog="示例：cat README.md | md2txt --wrap 80",
    )
    parser.add_argument("files", nargs="*", metavar="FILE", help="输入文件；- 表示 stdin")
    parser.add_argument("-o", "--output", metavar="PATH", help="输出文件；- 表示 stdout")
    parser.add_argument("--encoding", default="utf-8", metavar="ENC", help="输入编码（默认 utf-8）")
    parser.add_argument(
        "--heading-style", choices=("plain", "underline", "atx"), default="plain",
        help="标题样式（默认 plain）",
    )
    parser.add_argument(
        "--links", choices=("inline", "text"), default="inline",
        help="链接样式（默认 inline：文本 (URL)）",
    )
    parser.add_argument(
        "--table-style", choices=("aligned", "tsv", "pipe"), default="aligned",
        help="表格样式（默认 aligned）",
    )
    parser.add_argument("--wrap", type=int, default=0, metavar="N", help="按显示宽度折行，0 为不折")
    parser.add_argument("--keep-frontmatter", action="store_true", help="保留 YAML frontmatter")
    parser.add_argument("--keep-html", action="store_true", help="保留 HTML 标签")
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    return parser


def _make_md() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


def _read_inputs(files: Sequence[str], encoding: str) -> list[str]:
    if not files or list(files) == ["-"]:
        return [read_stream(sys.stdin.buffer, encoding, "<stdin>")]
    texts = []
    for path in files:
        if path == "-":
            texts.append(read_stream(sys.stdin.buffer, encoding, "<stdin>"))
        else:
            texts.append(read_path(path, encoding))
    return texts


def _render_all(sources: Sequence[str], opts: Options) -> str:
    md = _make_md()
    docs = []
    for source in sources:
        prefix = ""
        if opts.keep_frontmatter:
            front, source = split_frontmatter(source)
            if front:
                prefix = front + "\n\n"
        else:
            source = strip_frontmatter(source)
        docs.append(prefix + render_document(parse_tokens(md.parse(source)), opts))
    body = "\n\n".join(doc for doc in docs if doc != "")
    body = body.strip("\n")
    return body + "\n" if body else ""


def _write_output(text: str, output: str | None) -> None:
    if output is None or output == "-":
        sys.stdout.write(text)
        sys.stdout.flush()
        return
    parent = os.path.dirname(os.path.abspath(output))
    if not os.path.isdir(parent):
        raise InputError(f"{output}: 父目录不存在")
    try:
        with open(output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except BrokenPipeError:
        raise
    except OSError as exc:
        raise InputError(f"{output}: 写入失败: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.files.count("-") > 1:
        parser.error("'-' 最多只能出现一次")
    if args.wrap != 0 and args.wrap < 10:
        parser.error("--wrap 必须为 0 或 >= 10")
    try:
        validate_encoding(args.encoding)
    except LookupError:
        parser.error(f"未知编码: {args.encoding}")

    opts = Options(
        heading_style=args.heading_style,
        links=args.links,
        table_style=args.table_style,
        wrap=args.wrap,
        keep_frontmatter=args.keep_frontmatter,
        keep_html=args.keep_html,
    )

    try:
        sources = _read_inputs(args.files, args.encoding)
        text = _render_all(sources, opts)
        _write_output(text, args.output)
    except InputError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except OSError:
            pass
        return 0
    except KeyboardInterrupt:
        return 130
    except RecursionError:
        print(f"{PROG}: 嵌套过深或输入过于复杂", file=sys.stderr)
        return 1
    except MemoryError:
        print(f"{PROG}: 内存不足", file=sys.stderr)
        return 1
    return 0
