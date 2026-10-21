# md2txt 验收报告（REPORT）

| 项 | 内容 |
|---|---|
| 项目 | md2txt —— Markdown 转纯文本命令行工具 |
| 项目目录 | `/home/ubuntu/agent/projects/1020-2101-markdown-python` |
| 版本 | v0.1.0 |
| 验收日期 | 2026-10-20 |
| 结论 | **通过**：AC-01 ~ AC-18 共 18/18 PASS，unittest 83/83 OK，覆盖率 90% |

## 1. 交付物

- `SPEC.md`、`PLAN.md`（6 条任务，全部完成）
- `md2txt/` 包（CLI、loader、blocks、inline、render、tables、html_text、width）
- `pyproject.toml`（setuptools 后端，入口 `md2txt`）
- `tests/` 83 个 unittest 用例
- `scripts/check.sh` 自检脚本
- `README.md`、`CHANGELOG.md`、`requirements-dev.txt`

## 2. 验收结果

证据文件：`/home/ubuntu/agent/work/md2txt-acceptance.txt`（逐条命令与输出）。

| AC | 结果 | 证据摘要 |
|---|---|---|
| AC-01 安装与入口 | PASS | 干净 venv `pip install .` 成功；`md2txt --version` 与 `python -m md2txt --version` 均为 `md2txt 0.1.0`；help 含全部选项 |
| AC-02 管道 | PASS | `# 标题` + `Hello **world**.` → `标题\n\nHello world.\n`，退出 0，stderr 空 |
| AC-03 文件/多文件 | PASS | 双文件 → `A\n\nB\n`；`-` 与文件一致；`-` 两次退出 2 |
| AC-04 标题样式 | PASS | `标题\n====`、`## 二`、plain 逐字节匹配；非法值退出 2 |
| AC-05 行内 | PASS | 示例 A 精确匹配；`~~删除~~`→`删除`；`&amp;amp;`→`&amp;`；硬换行保留、软换行变空格 |
| AC-06 列表 | PASS | 示例 B 精确匹配；三层缩进 0/2/4；`3.` 起始保持 3/4；任务列表保留 `[x]`/`[ ]` |
| AC-07 引用 | PASS | 示例 C 精确匹配；`> > deep`；引用内列表逐行带 `> ` |
| AC-08 代码 | PASS | 围栏/波浪线/缩进代码内容保留；代码行尾空格保留；围栏行与语言标记消失 |
| AC-09 表格 | PASS | 示例 D 精确匹配；tsv 精确 `名称\tQty...`；pipe 含 `\| --- \| --- \|`；CJK/emoji 按显示宽度 |
| AC-10 HTML/frontmatter | PASS | 示例 E 精确匹配；`<script>` 整段丢弃；`--keep-html` 保留 `<b>` 且实体解码；`--keep-frontmatter` 原样保留 |
| AC-11 规范化 | PASS | 多空行折叠、行尾空格删除、末尾恰一个换行；空输入 0 字节；`***`→`---` |
| AC-12 折行 | PASS | 示例 F 精确匹配；中文每行宽度 ≤10；URL 不被拆断；`--wrap 9` 退出 2 |
| AC-13 选项组合 | PASS | `--links text --table-style tsv --heading-style atx` 同时生效；`-o` 内容一致且 stdout 为空；`-o -` 等价 |
| AC-14 错误与退出码 | PASS | 缺文件 1、未知选项 2、非法编码 2、非法 UTF-8 1，均以 `md2txt: ` 开头；broken pipe 退出 0 无 traceback；SIGINT 130 |
| AC-15 性能 | PASS | 5.01 MB 文档（标题/列表/表格/代码）：4.08 s，峰值 RSS 186 MB（阈值 5 s / 200 MB） |
| AC-16 确定性/无副作用 | PASS | 同输入两次输出 `cmp` 相同；临时工作目录运行前后无新文件；源码无 socket/requests/urllib |
| AC-17 测试与覆盖率 | PASS | 83/83 unittest OK；coverage 690 语句、90%（阈值 85%） |
| AC-18 边界鲁棒性 | PASS | 1 万层嵌套引用退出 0；10 MB 单行退出 0；二进制输入退出 1 且无 traceback |

## 3. 测试与覆盖率

- 单测证据：`/home/ubuntu/agent/work/md2txt-unittest.txt`（83 tests, OK）
- 覆盖率证据：`/home/ubuntu/agent/work/md2txt-coverage.txt`（TOTAL 90%）
- 自检脚本：`bash scripts/check.sh` → `check.sh: ALL OK`

覆盖率非 100% 的部分主要是：`__main__.py`（子进程入口）、CLI 的防御性异常分支、HTML 解析兜底分支、空表/异常 token 分支；核心渲染路径均有覆盖。

## 4. 性能

基准文档 5.01 MB，含 700 节标题、长段落、列表、表格、代码块：

```text
/usr/bin/time -f '%e %M' python3 -m md2txt /tmp/md2txt-bench.md -o /tmp/b.txt
4.08 190804
```

即 4.08 秒、峰值约 186 MB，满足 AC-15。极端碎片化文档（如数万个小表格）可能超过阈值，已在 README 声明。

## 5. 已知限制

- 不解析数学公式、脚注、定义列表、Mermaid，按普通文本处理。
- emoji / ZWJ 组合按 2 列近似，个别组合可能差 1 列。
- 表格单元格内硬换行在 tsv/pipe 模式折叠为空格。
- 输出以本工具规则为准，不承诺与 `pandoc -t plain` 逐字节一致。
- 引用块内软换行按源行保留（为对齐 SPEC 示例 C），与普通段落“软换行变空格”不同；README 已说明。

## 6. 结论

v0.1.0 达到 SPEC 的完成定义：AC-01~AC-18 全部通过，83 个单测全绿、覆盖率 90%，干净环境可安装，两个入口行为一致。无遗留阻塞；后续可考虑把当前“引用内软换行”行为回写进 SPEC，并补 emoji 宽度精确表。
