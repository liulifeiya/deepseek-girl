"""输入读取、编码处理与 YAML frontmatter 剥离。"""

from __future__ import annotations

import codecs
import re
import sys

_FRONTMATTER_KEY = re.compile(r"^[A-Za-z0-9_.-]+:\s*")


class InputError(Exception):
    """输入读取失败（退出码 1）。"""


def validate_encoding(name: str) -> str:
    """校验编码名；非法时抛 LookupError。"""
    codecs.lookup(name)
    return name


def decode_bytes(data: bytes, encoding: str) -> str:
    """按编码解码，UTF-8 自动去掉 BOM，换行统一为 \\n。"""
    if encoding.lower().replace("_", "-") in ("utf-8", "utf8"):
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise InputError(f"编码错误: {exc}") from exc
    except LookupError as exc:
        raise InputError(f"未知编码: {encoding}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_stream(stream: object, encoding: str, label: str) -> str:
    """从二进制流读取并解码。"""
    try:
        data = stream.read()  # type: ignore[attr-defined]
    except OSError as exc:
        raise InputError(f"{label}: 读取失败: {exc}") from exc
    try:
        return decode_bytes(data, encoding)
    except InputError as exc:
        raise InputError(f"{label}: {exc}") from exc


def read_path(path: str, encoding: str) -> str:
    """读取文件；失败时抛 InputError。"""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except FileNotFoundError as exc:
        raise InputError(f"{path}: 文件不存在") from exc
    except IsADirectoryError as exc:
        raise InputError(f"{path}: 是目录，不是文件") from exc
    except OSError as exc:
        raise InputError(f"{path}: 读取失败: {exc}") from exc
    try:
        return decode_bytes(data, encoding)
    except InputError as exc:
        raise InputError(f"{path}: {exc}") from exc


def split_frontmatter(text: str) -> tuple[str, str]:
    """把开头合法的 YAML frontmatter 与正文分开。

    仅当首行恰为 ``---``、500 行内出现闭合 ``---``/``...``、且区间内至少
    有一行形如 ``key:`` 时才识别，避免把分隔线误判为 frontmatter。
    返回 (frontmatter 原文, 正文)；未识别时返回 ("", text)。
    """
    if not text.startswith("---\n"):
        return "", text
    lines = text.split("\n")
    limit = min(len(lines), 501)
    for i in range(1, limit):
        if lines[i].strip() in ("---", "..."):
            block = lines[1:i]
            if any(_FRONTMATTER_KEY.match(line) for line in block):
                front = "\n".join(lines[: i + 1])
                body = "\n".join(lines[i + 1:])
                return front, body.lstrip("\n")
            return "", text
    return "", text


def strip_frontmatter(text: str) -> str:
    """剥离文件开头的 YAML frontmatter，返回正文。"""
    _, body = split_frontmatter(text)
    return body
