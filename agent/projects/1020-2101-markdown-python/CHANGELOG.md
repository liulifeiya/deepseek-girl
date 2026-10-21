# Changelog

## v0.1.0 (2026-10-20)

首个版本。

- 新增 `md2txt` 命令行工具与 `python -m md2txt` 入口，支持 stdin/文件/多文件/`-o`。
- 支持 CommonMark 核心语法 + GFM 表格 + 删除线的纯文本渲染。
- 支持标题三种样式、链接两种样式、表格三种样式、按显示宽度折行。
- 支持 YAML frontmatter 剥离、HTML 清洗、UTF-8 BOM、自定义编码。
- 提供 83 个 unittest 用例，覆盖率 90%。
