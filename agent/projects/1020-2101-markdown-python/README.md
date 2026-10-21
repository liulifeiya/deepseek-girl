# md2txt

把 Markdown 转成干净纯文本的命令行小工具。读文件或 stdin，输出可直接进 `less`、`grep`、TTS、日志、检索和 LLM 提示词。

- 零配置，无网络、无临时文件、无配置文件
- 基于 `markdown-it-py` 的 token 流渲染，不经过 HTML 中转
- 中文/emoji 按显示宽度对齐与折行
- 只有运行时依赖 `markdown-it-py>=3.0,<4`

## 安装

```bash
python3 -m pip install .
md2txt --version        # md2txt 0.1.0
python3 -m md2txt --version
```

离线环境可先在有网机器下载 wheel，或使用系统预装的 `markdown-it-py`：

```bash
python3 -m pip install --no-index --find-links ./wheels .
```

Python 要求 ≥ 3.10。

## 用法

```text
usage: md2txt [-h] [--version] [-o PATH] [--encoding ENC]
              [--heading-style {plain,underline,atx}]
              [--links {inline,text}]
              [--table-style {aligned,tsv,pipe}]
              [--wrap N] [--keep-frontmatter] [--keep-html]
              [FILE ...]
```

无参数或 `FILE` 为 `-` 时从 stdin 读取；支持多个文件，文档之间空一行。

| 参数 | 默认 | 说明 |
|---|---|---|
| `-o, --output PATH` | stdout | 输出文件；`-` 表示 stdout |
| `--encoding ENC` | `utf-8` | 输入编码；UTF-8 自动去 BOM |
| `--heading-style` | `plain` | `plain` 纯文本 / `underline` 下划线 / `atx` 保留 `#` |
| `--links` | `inline` | `inline` 输出 `文本 (URL)` / `text` 只留文本 |
| `--table-style` | `aligned` | `aligned` 对齐 / `tsv` 制表符 / `pipe` 管道表格 |
| `--wrap N` | `0` | 按显示宽度折行；0 关闭，N ≥ 10 |
| `--keep-frontmatter` | 关 | 保留开头 YAML frontmatter |
| `--keep-html` | 关 | 保留 HTML 标签（实体仍解码） |

## 示例

```bash
# 管道
cat README.md | md2txt | less

# 多文件合并
md2txt intro.md body.md appendix.md -o book.txt

# 窄屏折行（中文按 2 列）
md2txt --wrap 72 long-article.md

# 表格导出给 awk/cut
md2txt --table-style tsv report.md > report.tsv

# 只留链接文字
md2txt --links text CHANGELOG.md
```

行内示例：

```bash
$ printf '# 你好\n\n这是**加粗**和`代码`，见 [示例](https://example.com)。\n' | md2txt
你好

这是加粗和代码，见 示例 (https://example.com)。
```

表格示例：

```bash
$ printf '| 名称 | Qty |\n|:---|---:|\n| 苹果 | 3 |\n| apple | 12 |\n' | md2txt
名称   Qty
-----  ---
苹果     3
apple   12
```

## 输出规则

- 块之间恰好一个空行；行尾空格删除（代码块内保留）；文档末尾恰好一个 `\n`；空输入输出 0 字节。
- 标题、段落、强调、行内代码、列表（含有序、任务列表）、引用、代码块、分隔线、链接、图片、表格、HTML 清洗。
- 软换行合并为一个空格；硬换行（行尾两空格或反斜杠）保留为换行。引用块内的软换行按源行保留，便于引用诗歌/日志。
- 默认剥离开头合法的 YAML frontmatter，`--keep-frontmatter` 原样保留。
- HTML 默认去标签留文本，`<script>`/`<style>` 整段丢弃；实体只解码一次。

退出码：`0` 成功（含空输入、broken pipe），`1` 运行时错误，`2` 用法错误，`130` 被 Ctrl-C 中断。错误信息统一以 `md2txt: ` 开头写 stderr，不打印 traceback。

## 已知限制

- 不解析数学公式、脚注、定义列表、Mermaid；按普通文本处理。
- emoji 和 ZWJ 组合按 2 列近似，极少数组合可能差 1 列。
- 表格单元格内的硬换行会折叠为空格（`tsv`/`pipe`）或按行内规则处理（`aligned`）。
- 输出以本工具规则为准，不承诺与 `pandoc -t plain` 逐字节一致。
- 病态超大文档（例如几万个小表格）可能超过 5 秒/200 MB 的基准；常规 5 MB 文档在基准内。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v   # 83 个用例
bash scripts/check.sh                      # 编译 + 单测 + 冒烟
```

可选覆盖率：

```bash
python3 -m venv --system-site-packages /tmp/md2txt-venv
/tmp/md2txt-venv/bin/pip install coverage
/tmp/md2txt-venv/bin/coverage run --source=md2txt -m unittest discover -s tests
/tmp/md2txt-venv/bin/coverage report -m
```

当前覆盖率 90%（2026-10-20，83 个用例）。

## 许可证

MIT
