# md2txt 立项规格说明（SPEC）

| 项目 | 内容 |
|---|---|
| 项目名 | md2txt —— Markdown 转纯文本命令行工具 |
| 项目目录 | `/home/ubuntu/agent/projects/1020-2101-markdown-python` |
| 规格版本 | v1.0（立项基线） |
| 状态 | 立项完成，待实施 |
| 日期 | 2026-10-20 |
| 目标平台 | Linux（Ubuntu 24.04），Python ≥ 3.10 |
| 许可证 | MIT |

---

## 1. 目标

### 1.1 一句话目标

提供一个零配置、可管道调用的 Python CLI：读取 Markdown（文件或 stdin），输出干净、稳定、对人友好的纯文本，让 Markdown 内容可以直接进入 `less`、`grep`、TTS、日志、检索和 LLM 提示词等纯文本场景。

### 1.2 可量化目标

| 编号 | 目标 | 度量 |
|---|---|---|
| G-1 | 管道可用 | `printf '# Hi\n' \| md2txt` 输出 `Hi`，退出码 0，无需临时文件 |
| G-2 | 文件可用 | 支持单文件、多文件、`-o` 输出，UTF-8（含 BOM）默认可用 |
| G-3 | 语义不丢 | CommonMark 核心块级/行内结构 + GFM 表格、删除线均按第 5 节规则转为文本 |
| G-4 | 输出稳定 | 同一输入重复运行字节一致；除 `-o` 指定的文件外不写任何文件 |
| G-5 | 依赖克制 | 运行时仅依赖 `markdown-it-py`（已预装），其余全部用标准库 |
| G-6 | 质量 | 单元测试全绿、行覆盖率 ≥ 85%，AC-01～AC-18 全部通过 |
| G-7 | 性能 | 5 MB Markdown 在本机单次转换 < 5 s，峰值内存 < 200 MB |

### 1.3 成功定义

实施完成后，在干净虚拟环境中 `pip install .`，`md2txt` 与 `python -m md2txt` 两种入口行为一致，且第 6 节全部验收标准有可复现的记录。

---

## 2. 典型使用场景

1. **管道阅读/检索**
   ```bash
   cat README.md | md2txt | less
   curl -fsSL https://example.com/post.md | md2txt --wrap 100
   ```
   无需先落盘，stdin 关闭后立即输出。

2. **批量喂给下游文本工具**
   ```bash
   md2txt docs/*.md | grep -n "TODO"
   md2txt notes.md | say   # 或任意 TTS/摘要/向量化管线
   ```
   输出不含 `#`、`**`、`[]()` 等标记，避免污染下游。

3. **多文档合并导出**
   ```bash
   md2txt intro.md body.md appendix.md -o book.txt
   ```
   文档之间以恰好一个空行分隔，末尾恰好一个换行。

4. **终端窄屏阅读**
   ```bash
   md2txt --wrap 72 long-article.md
   ```
   按显示宽度折行，中文按 2 列计算，不破坏 URL 与行内代码。

5. **保留结构的纯文本表格**
   ```bash
   md2txt --table-style aligned report.md
   md2txt --table-style tsv report.md > report.tsv
   ```
   前者供人读，后者供 `cut`/`awk` 消费。

6. **脚本/CI 中的确定性转换**
   ```bash
   md2txt --links text --heading-style atx CHANGELOG.md > /tmp/changelog.txt
   ```
   无网络、无配置、无交互，退出码可判断。

---

## 3. 范围

### 3.1 做什么（v1 必须交付）

- 命令行入口 `md2txt`，同时支持 `python3 -m md2txt`。
- 输入：0 个参数或参数为 `-` 时读 stdin；支持一个或多个文件路径；支持 `--encoding`；默认 UTF-8 并容忍 BOM。
- 输出：默认 stdout；`-o/--output` 写文件；统一 `\n` 换行；空输入输出空。
- 解析：CommonMark 核心语法 + GFM 表格 + 删除线（`markdown-it-py` 的 `table`、`strikethrough` 规则）。
- 渲染：标题、段落、强调/加粗/删除线、行内代码、围栏/缩进代码块、有序/无序/嵌套/任务列表、引用块、分隔线、链接、图片、自动链接、硬换行/软换行、HTML 内联与块级清洗、HTML 实体解码、YAML frontmatter 剥离、GFM 表格。
- 选项：`--heading-style`、`--links`、`--table-style`、`--wrap`、`--keep-frontmatter`、`--keep-html`、`--encoding`、`-o/--output`、`--version`、`--help`。
- 错误处理：文件不存在、编码错误、非法参数、管道提前关闭（broken pipe）均有确定行为。
- 工程化：`pyproject.toml` 可安装、README、单元测试、验收测试脚本、CHANGELOG。

### 3.2 明确不做什么（Non-goals）

- 不做 GUI、TUI、Web 服务、编辑器插件、语言服务器。
- 不做反向转换（纯文本 → Markdown）、不做 Markdown 格式化/美化。
- 不输出 ANSI 颜色、语法高亮、分页器；需要颜色/分页请自行接 `pygmentize`、`less -R`。
- 不解析/渲染数学公式（LaTeX）、脚注、定义列表、引用式脚注、Mermaid、PlantUML；遇到时按普通文本/代码处理，不报错。
- 不转换 docx/pdf/epub/html 网页；不做图片 OCR、不下载远程图片。
- 不做原地改写（`--in-place`）、不做批量递归目录遍历（交给 shell `find -exec`）。
- 不做配置文件、主题、插件系统、i18n；界面文案固定中文错误提示 + 英文 usage。
- 不对 Windows 控制台做专门适配（代码尽量跨平台，但验收只在 Linux）。
- 不保留源文件精确行号/列号，不做 AST 或位置映射。
- 不承诺与 pandoc `-t plain` 输出逐字节一致；本工具以自己的第 5 节规范为准。

---

## 4. 用户接口

### 4.1 用法

```text
usage: md2txt [-h] [--version] [-o PATH] [--encoding ENC]
              [--heading-style {plain,underline,atx}]
              [--links {inline,text}]
              [--table-style {aligned,tsv,pipe}]
              [--wrap N] [--keep-frontmatter] [--keep-html]
              [FILE ...]
```

### 4.2 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `FILE ...` | stdin | 输入文件；`-` 表示 stdin；无参数等价于 `-`；`-` 最多出现一次 |
| `-o, --output PATH` | stdout | 输出文件；`-` 表示 stdout；父目录不存在时报错，退出码 1 |
| `--encoding ENC` | `utf-8` | 输入文件编码；自动容忍 UTF-8 BOM；非法编码名退出码 2 |
| `--heading-style` | `plain` | `plain` 纯文本；`underline` 用 `=`/`-`/`~` 下划线；`atx` 保留 `#` 前缀 |
| `--links` | `inline` | `inline` 输出 `文本 (URL)`；`text` 只保留文本 |
| `--table-style` | `aligned` | `aligned` 对齐列；`tsv` 制表符分隔；`pipe` 输出规范化的管道表格 |
| `--wrap N` | `0` | 按显示宽度折行；`0` 表示不折行；`N` 必须 ≥ 10，否则退出码 2 |
| `--keep-frontmatter` | 关 | 保留开头 YAML frontmatter（默认剥离） |
| `--keep-html` | 关 | 原样保留 HTML 标签（默认清洗为纯文本） |
| `--version` | — | 输出版本号并退出 0 |
| `-h, --help` | — | 输出帮助并退出 0 |

### 4.3 输入输出语义

- **stdin**：无 FILE 或含 `-` 时读取；读取到 EOF 后处理。TTY 下不等待交互提示，直接读（由用户 Ctrl-D 结束），不打印 banner。
- **多文件**：按命令行顺序逐个解析，文档之间插入恰好一个空行；任一文件失败则整体失败，不产生半截输出（先全部读入内存再写出）。
- **编码**：默认 `utf-8`，若文件以 UTF-8 BOM 开头则去掉 BOM；解码失败打印 `md2txt: <path>: 编码错误: ...` 到 stderr，退出 1。
- **输出**：始终以 UTF-8 写出；换行统一为 `\n`；结果末尾恰好一个 `\n`；空/纯空白输入输出 0 字节。
- **broken pipe**：下游 `head`/`less` 提前关闭时静默退出 0，不打印 traceback。
- **Ctrl-C**：退出 130，不打印 traceback。
- **不写临时文件**，不读取环境变量配置，不访问网络。

### 4.4 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 成功（含 broken pipe、空输入） |
| 1 | 运行时错误：文件不存在/不可读、编码错误、写输出失败、内部渲染异常 |
| 2 | 用法错误：未知参数、参数值非法、`-` 重复、`--wrap` 过小、编码名非法 |
| 130 | 被 SIGINT 中断 |

错误信息统一以 `md2txt: ` 前缀写 stderr；`--help`/`--version` 写 stdout。

---

## 5. 渲染规范（规范性）

渲染分两阶段：先用 `markdown-it-py` 解析为 token 流，再构造中间块模型，最后由纯函数渲染。**禁止**先渲染 HTML 再正则去标签（会丢表格结构且难控空白）。

### 5.1 文档级规范化

1. 剥离 BOM；统一换行符为 `\n`。
2. 默认剥离位于文件开头（允许 BOM）的 YAML frontmatter：第一行恰为 `---`，在后续 500 行内找到闭合 `---` 或 `...`，且区间内至少有一行匹配 `^[A-Za-z0-9_.-]+:\s*`；三者同时满足才剥离，否则按普通 Markdown 处理（避免把分隔线误判为 frontmatter）。
3. 块与块之间恰好一个空行；行尾空格（代码块之外）删除；连续空行折叠为一个；文档首尾空行删除。
4. 输出末尾恰好一个 `\n`；空文档输出空字节串。

### 5.2 块级元素

| 元素 | 输出规则 |
|---|---|
| 标题 | 按 `--heading-style` 输出；`plain` 只输出标题文本；`underline` 一级用 `=`、二级用 `-`、三级及以下用 `~`，下划线长度等于标题显示宽度（CJK 计 2）；`atx` 输出 `#`×级别 + 空格 + 文本 |
| 段落 | 软换行（源码单换行）合并为一个空格；硬换行（行尾两个空格或反斜杠）输出 `\n`；段落内其余空白折叠为一个空格 |
| 分隔线 | 输出 `---` |
| 引用块 | 每行加 `> `；引用内空行输出 `>`（不带尾随空格）；嵌套引用重复前缀；引用内的列表/代码/标题按各自规则渲染后再逐行加前缀 |
| 代码块 | 反引号围栏、波浪线围栏与缩进代码均原样保留内容，去掉围栏行与围栏语言标记；内部空行、缩进、行尾空格保留；代码块作为一个块，前后各一个空行 |
| 列表 | 见 5.3 |
| 表格 | 见 5.4 |
| HTML 块 | 见 5.5 |

### 5.3 列表

1. 无序列表统一用 `- `；嵌套列表的 marker 从父项内容起始列开始（父项为 `- ` 时缩进 2 个空格，父项为 `N. ` 时缩进 marker 宽度）。
2. 有序列表使用 `N. `，从源列表的 `start` 值开始递增；嵌套有序列表按各自 `start` 重新计数。
3. 任务列表保留复选框：`- [x] 已完成`、`- [ ] 未完成`。
4. 列表项之间不插入空行；列表项内部若含多个块，块之间空一行；续行与子块按该项内容起始列对齐（`- ` 为 2 列，`N. ` 为 marker 宽度）。
5. 列表与前后块之间各一个空行。
6. 空列表项输出 marker 本身（如 `-`），不 panic。

### 5.4 表格（仅 GFM 管道表格）

1. `aligned`（默认）：按每列的**显示宽度**（East Asian Wide/Fullwidth 计 2，组合字符计 0）计算列宽，单元格左/中/右对齐依照分隔行 `:---`、`:---:`、`---:`；列间用 2 个空格分隔；表头后输出一行由 `-` 组成的分隔行，长度等于列宽；行尾不留空格。
2. `tsv`：每行单元格用 `\t` 连接，不输出分隔行；单元格内的 `\t` 替换为空格、换行折叠为空格。
3. `pipe`：输出规范化的 `| a | b |` 形式，分隔行用 `---`，不做宽度对齐；供再次喂给 Markdown 工具。
4. 单元格内容为空时保留空列；表格列数不一致时按表头列数截断/补空。
5. 表格作为整体不参与 `--wrap` 折行。

### 5.5 HTML、实体与 frontmatter

- 默认清洗 HTML：删除标签本身，保留可见文本；`<br>`、`<p>`、`<div>`、`<li>`、`<tr>` 等块级边界转为换行；`<script>`、`<style>`、`<noscript>` 的内容整段丢弃；注释丢弃；`<pre>` 内容按代码块保留。
- 实体：`&amp;`、`&lt;`、`&gt;`、`&quot;`、`&#39;`、`&#x...;` 等解码为对应字符，且只解码一次（不出现 `&amp;amp;` 双重解码）。
- `--keep-html` 时标签原样输出，但仍解码实体（保持文本语义）。
- frontmatter 默认剥离；`--keep-frontmatter` 时原样作为普通文本块输出（不解析 YAML）。

### 5.6 行内元素

| 元素 | 输出规则 |
|---|---|
| 强调/加粗/删除线 | 去掉标记，保留文本 |
| 行内代码 | 去掉反引号，保留内容；内容首尾各一个空格时按 CommonMark 规则去掉一个 |
| 链接 | `inline`：`文本 (URL)`；若文本与 URL 相同或为自动链接，只输出 URL；文本为空输出 URL；`text`：只输出文本 |
| 图片 | `inline`：`alt (src)`；alt 为空输出 `[image] (src)`；`text`：只输出 alt，alt 为空输出 `[image]` |
| 自动链接 | 直接输出 URL/邮箱，不加括号 |
| 软换行 | 一个空格 |
| 硬换行 | `\n` |
| 反斜杠转义 | 输出被转义的字符本身 |

### 5.7 折行（`--wrap N`）

- 仅对段落、列表项文本、引用块文本折行；标题、代码块、表格不折行。
- 以显示宽度计（CJK 2 列）；按空格断词；连续 CJK 字符之间允许断开；URL 和行内代码作为不可断单元，超宽时整段保留、不强行截断。
- 列表续行缩进到内容起始列；引用块每行都带 `> ` 前缀，前缀计入宽度。
- 段落中的硬换行视为强制换行点，折行不得跨过它。

### 5.8 规范性示例

**示例 A（管道 + 行内）**

输入：

```markdown
# 你好

这是**加粗**和`代码`，见 [示例](https://example.com)。
```

输出：

```text
你好

这是加粗和代码，见 示例 (https://example.com)。
```

**示例 B（列表）**

输入：

```markdown
- 苹果
  - 青苹果
- 香蕉

3. 三
4. 四

- [x] 已完成
- [ ] 未完成
```

输出：

```text
- 苹果
  - 青苹果
- 香蕉

3. 三
4. 四

- [x] 已完成
- [ ] 未完成
```

**示例 C（引用）**

输入：

```markdown
> 第一行
> **第二行**
>
> 新段落
```

输出：

```text
> 第一行
> 第二行
>
> 新段落
```

**示例 D（表格，CJK 对齐）**

输入：

```markdown
| 名称 | Qty |
|:---|---:|
| 苹果 | 3 |
| apple | 12 |
```

输出（第一列宽 5，第二列宽 3，列间 2 空格）：

```text
名称   Qty
-----  ---
苹果     3
apple   12
```

**示例 E（frontmatter + HTML）**

输入：

```markdown
---
title: 测试
tags:
  - a
---
<div>Hello <b>世界</b><br>第二行</div>

Tom &amp; Jerry &lt;3
```

输出：

```text
Hello 世界
第二行

Tom & Jerry <3
```

**示例 F（折行）**

`md2txt --wrap 20` 输入 `The quick brown fox jumps over the lazy dog.`，输出：

```text
The quick brown fox
jumps over the lazy
dog.
```

---

## 6. 验收标准

> 所有命令在项目根目录执行；`md2txt` 指安装后的入口，或等价的 `python3 -m md2txt`（二者都需通过）。每条必须有可复现记录，写入实施阶段的 `WORKLOG.md`/测试报告。

| 编号 | 验收条件 | 验证方式 |
|---|---|---|
| AC-01 | 安装与入口：`pip install .` 后 `md2txt --version` 输出 `md2txt X.Y.Z` 且退出 0；`python3 -m md2txt --version` 输出一致；`md2txt --help` 含全部选项 | 干净 venv 中执行，比对版本串 |
| AC-02 | 管道：`printf '# 标题\n\nHello **world**.\n' \| md2txt` 输出 `标题\n\nHello world.\n`，退出 0，stderr 为空 | 精确 diff（`od -c` 校验末尾换行） |
| AC-03 | 文件与多文件：单文件输出同 AC-02；`a.md`（`# A`）+ `b.md`（`# B`）输出 `A\n\nB\n`；`md2txt - < a.md` 与 `md2txt a.md` 一致；`-` 出现两次退出 2 | 三个命令 + 退出码断言 |
| AC-04 | 标题三种样式：`plain`/`underline`/`atx` 分别符合 5.2；`--heading-style underline` 对 `# 标题` 输出 `标题\n====`；非法值退出 2 | 逐字节 diff |
| AC-05 | 行内：示例 A 精确匹配；`~~删除~~` 输出 `删除`；`&amp;` 只解码一次；硬换行保留为换行、软换行变空格 | 单元测试 + 示例 diff |
| AC-06 | 列表：示例 B 精确匹配；嵌套 3 层缩进为 0/2/4；`3.` 起始的有序列表保持 3、4；任务列表保留 `[x]`/`[ ]` | 示例 diff + 单元测试 |
| AC-07 | 引用：示例 C 精确匹配；嵌套 `> >` 输出 `> > `；引用内列表逐行带 `> ` | 示例 diff + 单元测试 |
| AC-08 | 代码：围栏代码内容逐字节保留（除文档末尾外），围栏行与语言标记消失；缩进代码同样；列表内代码块缩进对齐；代码块内空行不折叠 | 单元测试（含反引号/波浪线围栏） |
| AC-09 | 表格：示例 D 精确匹配；`--table-style tsv` 输出 `名称\tQty\n苹果\t3\napple\t12\n`；`pipe` 含 `\| --- \| --- \|`；CJK/emoji 列宽按显示宽度 | 示例 diff + 单元测试 |
| AC-10 | HTML/frontmatter：示例 E 精确匹配；`<script>alert(1)</script>ok` 输出 `ok`；`--keep-html` 保留 `<b>` 但实体解码；`--keep-frontmatter` 保留 `title: 测试` | 示例 diff + 单元测试 |
| AC-11 | 规范化：`printf '\n\n\n# H\n\n\n\ntext   \n\n\n' \| md2txt` 输出 `H\n\ntext\n`；空输入输出 0 字节、退出 0；`***` 输出 `---` | `wc -c` + `od -c` |
| AC-12 | 折行：示例 F 精确匹配；`--wrap 10` 对 `中文测试一二三四五六七八九十` 每行显示宽度 ≤ 10；URL 不被拆断；`--wrap 9` 退出 2 | 精确 diff + 宽度断言 |
| AC-13 | 选项组合：`--links text --table-style tsv --heading-style atx` 同时生效；`-o out.txt` 内容与 stdout 一致且 stdout 为空；`-o -` 等价 stdout | 集成测试 |
| AC-14 | 错误与退出码：不存在文件→1 且 stderr 以 `md2txt: ` 开头；未知选项→2；非法编码名→2；非法 UTF-8 字节→1；`md2txt big.md \| head -1` 退出 0 且无 traceback；Ctrl-C→130 | 子进程断言 |
| AC-15 | 性能：生成 5 MB Markdown（含标题/列表/表格/代码），单次转换 < 5 s，峰值 RSS < 200 MB | `/usr/bin/time -v` 记录 |
| AC-16 | 确定性/无副作用：同一输入连续两次输出 `cmp` 相同；运行前后除 `-o` 目标与 Python 字节码缓存外工作区无新文件；源码中无 `socket`/`requests`/`urllib` 网络调用 | `cmp`、`find -newer`、源码 grep |
| AC-17 | 测试：`python3 -m unittest discover -s tests -v` 全绿；`coverage run -m unittest discover -s tests` 行覆盖率 ≥ 85% | CI 脚本 `scripts/check.sh` |
| AC-18 | 边界鲁棒性：1 万层嵌套引用/列表不崩溃（可报错但退出码 ≤ 1 且无 traceback）；二进制垃圾输入不崩溃；超长单行（10 MB）不崩溃 | 子进程 + 超时 30 s |

---

## 7. 技术选型与理由

### 7.1 环境事实（2026-10-20 实测）

| 项 | 结果 |
|---|---|
| OS | Ubuntu 24.04.4 LTS，Linux 6.8，x86_64 |
| Python | 3.12.3（`/usr/bin/python3`） |
| Node | v24.19.0（本项目不需要） |
| 已装解析库 | `markdown-it-py 3.0.0`（`/usr/lib/python3/dist-packages`）、`PyYAML 6.0.1` |
| 未装 | `markdown`、`mistune`、`commonmark`、`bs4`、`html2text`、`pytest`、`wcwidth`、`coverage` |
| 安装能力 | pip 24.0 可用，内网 PyPI 镜像可下载（实测 pytest/markdown-it-py 均可下载）；setuptools 68.1.2、wheel 0.42.0、venv 可用 |
| 结论 | 无需 Node；解析用已预装的 `markdown-it-py`；测试用标准库 `unittest` 避免额外运行时依赖；`coverage` 仅作为开发期可选依赖 |

### 7.2 选型对比

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| **markdown-it-py 3.x（选中）** | 已预装；CommonMark 合规；输出 token 流而非 HTML，天然适合结构化转文本；内置 table/strikethrough 插件；纯 Python、MIT、活跃 | 3.x 与 4.x 有 API 差异；需锁版本 | **采用**，`markdown-it-py>=3.0,<4` |
| Python-Markdown | 生态成熟 | 未安装；以 HTML 输出为中心，转纯文本需再解析 HTML；表格需扩展 | 否 |
| mistune | 快、API 简单 | 未安装；AST 渲染需额外工作；GFM 细节需插件 | 否 |
| pandoc 子进程 | 格式最全 | 外部重依赖（数百 MB）；启动慢；输出风格不可控；机器上未必有 | 否 |
| 手写正则/状态机 | 零依赖 | CommonMark 边界极多（嵌套、转义、HTML、表格），维护成本远超收益 | 否（仅用于 HTML 清洗这类局部） |
| HTML 中转（md→HTML→去标签） | 实现直观 | 表格/列表/代码结构在 HTML 里丢失语义，空白与嵌套难控；需要 HTML 解析器 | 否 |

### 7.3 其他技术决定

- **CLI**：标准库 `argparse`。子命令不需要；选项少，argparse 足够且自带 `--help`/退出码 2。
- **数据模型**：`dataclass` 定义 `Block`/`Inline` 中间结构；渲染函数纯函数、无全局状态，便于单测。
- **显示宽度**：`unicodedata.east_asian_width`（W/F 计 2，Mn/Me/Cf 计 0）+ 自有 `display_width()`；不引入 `wcwidth`，emoji 宽度按 2 近似并在 README 声明。
- **HTML 清洗**：标准库 `html.parser.HTMLParser` 子类 + `html.unescape`；不引入 bs4。
- **测试**：标准库 `unittest`；fixtures 放 `tests/fixtures/`；`coverage` 只在 `requirements-dev.txt`，不进入运行时依赖。
- **打包**：`pyproject.toml` + setuptools 后端，`[project.scripts] md2txt = "md2txt.cli:main"`；Python 下限 3.10。
- **版本**：遵循 SemVer，首个版本 `0.1.0`；`--version` 从包元数据读取，避免双份维护。
- **错误处理**：自定义 `Md2txtError` 携带退出码；`main()` 捕获后打印一行 stderr，不打印 traceback；broken pipe 单独捕获。
- **不引入**：click/typer（额外依赖）、rich（颜色非目标）、pyyaml（frontmatter 只剥离不解析）。

### 7.4 依赖策略

- 运行时唯一依赖：`markdown-it-py>=3.0,<4`（系统已满足）。安装时若目标机离线，可从系统包或内网镜像获取；README 给出离线 `--no-index` 说明。
- 开发依赖（可选）：`coverage`。测试本身不依赖它。
- 所有依赖锁定上限，升级需跑全量验收。

---

## 8. 架构与工程约束

### 8.1 目录结构（计划）

```text
1020-2101-markdown-python/
├── SPEC.md
├── PLAN.md
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── requirements-dev.txt
├── md2txt/
│   ├── __init__.py        # __version__
│   ├── __main__.py        # python -m md2txt
│   ├── cli.py             # argparse、IO、退出码
│   ├── loader.py          # stdin/文件/编码/BOM/frontmatter
│   ├── blocks.py          # token → 中间块模型
│   ├── inline.py          # 行内 token → 文本
│   ├── render.py          # 块模型 → 纯文本
│   ├── tables.py          # 表格对齐
│   ├── html_text.py       # HTML 清洗
│   └── width.py           # 显示宽度与折行
├── scripts/
│   └── check.sh           # unittest + 验收冒烟
└── tests/
    ├── fixtures/
    ├── test_cli.py
    ├── test_inline.py
    ├── test_blocks.py
    ├── test_tables.py
    ├── test_html.py
    └── test_width.py
```

结构可在实施中微调，但**必须**保持：CLI 与渲染逻辑分离、解析与渲染分离、纯函数可独立测试。

### 8.2 工程约束

- Python ≥ 3.10；使用类型注解；公共函数有 docstring。
- 禁止 `eval`/`exec`/`pickle`；不执行输入中的任何代码；HTML 只做文本化。
- 不做网络请求；不读取用户 home 配置；不写日志文件。
- 渲染结果只依赖输入与显式选项，不依赖 locale、终端宽度、环境变量（`--wrap` 显式传入）。
- 单文件源码 ≤ 400 行（超了拆分）；函数 ≤ 50 行。
- 提交前 `python3 -m compileall md2txt`、`python3 -m unittest` 全绿。
- 每个任务完成即更新 `WORKLOG.md`（2～6 行关键信息）。

### 8.3 里程碑

| 里程碑 | 内容 | 出口条件 |
|---|---|---|
| M1 骨架可跑 | 包结构、pyproject、CLI 参数、stdin/stdout 最小链路 | AC-01/02/03 通过 |
| M2 核心渲染 | 段落/标题/行内/列表/引用/代码/表格 | AC-04～AC-09 通过 |
| M3 增强与边界 | HTML、frontmatter、折行、规范化、错误处理 | AC-10～AC-14、AC-18 通过 |
| M4 测试与性能 | 单测覆盖率、E2E、性能与确定性 | AC-15～AC-17 通过 |
| M5 文档与发布 | README、CHANGELOG、干净环境安装、全量验收 | AC-01～AC-18 全部通过，打 tag v0.1.0 |

---

## 9. 主要风险与对策

| 编号 | 风险 | 概率 | 影响 | 对策 / 触发条件 |
|---|---|---|---|---|
| R-1 | `markdown-it-py` 3.x/4.x API 差异导致升级后行为变化 | 中 | 高 | 依赖锁 `<4`；CI 固定 3.0.0 跑全量；升级另开任务 |
| R-2 | CJK/emoji 显示宽度计算不准，表格错位 | 中 | 中 | `east_asian_width` 为主，emoji 近似 2；单测覆盖中文/全角/组合字符；README 声明局限 |
| R-3 | HTML 清洗丢内容或残留标签（嵌套、script、注释） | 中 | 中 | 用 `HTMLParser` 而非正则；固定 fixtures；`--keep-html` 兜底 |
| R-4 | 嵌套列表/引用/代码的缩进规则组合爆炸 | 高 | 中 | 中间块模型统一携带 depth；表格驱动单测；先实现 3 层再压测 |
| R-5 | 折行破坏 URL/行内代码或 CJK 边界 | 中 | 中 | 不可断单元 token 化；宽度断言；超宽保留不截断 |
| R-6 | 大文件/病态嵌套导致慢或递归崩溃 | 低 | 高 | 5 MB 基准；深度上限保护；异常转退出 1 不 traceback |
| R-7 | broken pipe 打印 traceback 污染管道 | 中 | 低 | 捕获 `BrokenPipeError`，`dup2` 到 devnull；`\| head` 回归测试 |
| R-8 | frontmatter 误判（把 `---` 分隔线当 frontmatter） | 中 | 低 | 三重判定（起始、闭合、含 key:）；单测覆盖分隔线场景 |
| R-9 | 范围蔓延（公式、脚注、TUI、颜色） | 中 | 中 | Non-goals 写死；新需求进 backlog，不进 v1 |
| R-10 | 干净环境安装失败（build 后端/离线） | 低 | 中 | 固定 setuptools 后端；README 给离线安装；M5 用干净 venv 验证 |
| R-11 | 默认样式不符合用户预期 | 中 | 低 | 选项覆盖三种标题/链接/表格风格；README 给推荐组合 |
| R-12 | 输出与 pandoc 等工具不一致引发争议 | 低 | 低 | 以本 SPEC 第 5 节为唯一标准；README 声明差异 |

---

## 10. 交付物与完成定义

### 10.1 交付物

1. `SPEC.md`（本文件）、`PLAN.md`。
2. 可安装的 `md2txt` 包与 `pyproject.toml`。
3. `README.md`：安装、用法、全部选项、示例、已知限制、与 pandoc 差异。
4. `CHANGELOG.md`（v0.1.0）。
5. `tests/` 单元测试与 `scripts/check.sh` 验收脚本。
6. 实施期 `WORKLOG.md`（每任务 2～6 行）与最终验收记录。

### 10.2 Definition of Done

- AC-01～AC-18 全部通过，记录命令与结果。
- `python3 -m unittest discover -s tests` 全绿，覆盖率 ≥ 85%。
- 干净 venv 中 `pip install .` 成功，`md2txt` 与 `python -m md2txt` 均可用。
- README 中的每个示例都能直接复制运行且输出与文档一致。
- 无已知 P0/P1 缺陷；R-1～R-12 均有对应测试或文档说明。

### 10.3 决策记录（立项时已定，实施期不再反复）

| 决策 | 选择 | 理由 |
|---|---|---|
| 解析器 | markdown-it-py 3.x token 流 | 已预装、结构化、避免 HTML 中转 |
| 默认标题样式 | `plain` | 最“纯文本”，需要结构时用 `underline`/`atx` |
| 默认链接样式 | `inline`（`文本 (URL)`） | 不丢链接信息；`--links text` 可关闭 |
| 默认表格样式 | `aligned` | 人读友好；机器消费用 `tsv` |
| 默认折行 | 关闭（`--wrap 0`） | 不擅自改变段落形态，宽度交给用户 |
| 测试框架 | 标准库 unittest | 零额外依赖，任何机器可跑 |
| 包名/命令 | `md2txt` | 简短、无歧义、易记 |
| Python 下限 | 3.10 | 覆盖 Ubuntu 22.04+，可用现代类型语法 |

---

## 11. 待实施阶段验证的问题（不阻塞立项）

1. `markdown-it-py` 对表格单元格内行内标记（链接、代码）的 token 细节，需在表格渲染时递归行内渲染而非取 `token.content`。
2. `html_block` 中 `<pre>` 与 `<br>` 的边界处理需用 fixtures 固化。
3. emoji/ZWJ 组合的显示宽度在 `unicodedata` 下的实际值，需单测记录并在 README 声明近似策略。
4. 5 MB 基准在目标机上的实际耗时，用于校准 AC-15 阈值（当前阈值已留 2 倍余量）。
5. 干净 venv 离线安装路径（系统 `--system-site-packages` vs 内网镜像），在 M5 固化到 README。
