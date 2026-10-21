# git7

统计 git 仓库最近 N 天（默认 7 天）每天提交数的命令行小工具。纯 Python 标准库，调用系统 `git`，不需要安装任何第三方包。

## 安装

要求：

- Python 3.8+
- git 2.0+，且在 `PATH` 中
- 主要面向 Linux / macOS 终端（Windows 未实测）

无需 `pip install`：把 `git7.py` 放在任意目录即可运行。可选 `chmod +x git7.py` 后直接执行 `./git7.py`。

```bash
python3 git7.py --help
```

## 3 个常用示例

### 1. 站会 / 周报：看当前仓库最近 7 天

```bash
cd ~/code/app
python3 /path/to/git7.py
```

输出固定 7 行，从最早到今天，没有提交的日期补 0：

```text
2026-10-14  0
2026-10-15  2
2026-10-16  0
2026-10-17  5
2026-10-18  1
2026-10-19  0
2026-10-20  3
```

### 2. 指定仓库、时间窗和作者，并显示合计

```bash
python3 git7.py ~/code/app --days 14 --author "alice@example.com" --total
```

`--days` 支持 1~366；`--author` 使用 git 的 `--author` 语义（匹配作者姓名或邮箱）；`--total` 在数据行后追加 `total N`。

### 3. CI / 脚本消费 JSON

```bash
python3 git7.py ~/code/app --rev release/1.2 --json | python3 -m json.tool
```

`--json` 只输出一个 JSON 对象；`--rev` 可指定分支、标签或提交。没有 jq 也能用 Python 解析。

## 选项

```text
python3 git7.py [PATH] [options]
```

| 选项 | 默认 | 说明 |
| --- | --- | --- |
| `PATH` | `.` | 仓库路径，或仓库内任意子目录 |
| `--days N` | `7` | 统计最近 N 个自然日（含今天），1~366 |
| `--rev REV` | `HEAD` | 分支、标签或提交 |
| `--author PATTERN` | 无 | 只统计作者名/邮箱匹配 `PATTERN` 的提交（git `--author`） |
| `--no-merges` | 关 | 排除 merge 提交 |
| `--json` | 关 | 输出 JSON 对象；此时 `--total` 被忽略 |
| `--total` | 关 | 文本模式末尾追加一行 `total N` |
| `-h`, `--help` | | 显示帮助 |

## 输出格式

### 文本

stdout 恰好 N 行，从最早到最近，日期 `YYYY-MM-DD` + 两个空格 + 次数，无表头、无空行、无颜色。加 `--total` 时多一行 `total N`：

```text
2026-10-14  0
2026-10-15  2
2026-10-16  0
2026-10-17  5
2026-10-18  1
2026-10-19  0
2026-10-20  3
total 11
```

### JSON

```json
{
  "repo": "/abs/path/to/repo",
  "rev": "HEAD",
  "days": [
    {"date": "2026-10-14", "count": 0},
    {"date": "2026-10-15", "count": 2}
  ],
  "total": 2
}
```

- `repo`：仓库根的绝对路径。
- `rev`：用户传入的值（默认 `"HEAD"`，不解析成 SHA）。
- `days`：长度为 N，日期连续升序；示例为节省篇幅只列 2 天。
- `total`：所有 `count` 之和。
- `--json` 下 stdout 只有这个对象，没有表头或汇总行；`--total` 被忽略。

诊断和错误只写 stderr；输出不因 stdout 是否为 TTY 而变化，便于重定向和管道。

## 日期与 merge 口径

- “最近 N 天”指今天及之前 N-1 个自然日，共 N 天（含今天），不是“过去 N×24 小时”。
- 提交归属日按 **author date**（`%at`，作者时间）在 **运行机器的本地时区** 下换算。跨时区协作时，同一提交在不同机器上可能落到不同日期。
- 只统计从 `--rev`（默认 HEAD）可到达的提交，不是全仓库所有 ref。
- merge 提交默认计入；`--no-merges` 排除。
- 没有提交的日期显式补 0；未来时间戳的提交不计入。
- 空仓库（尚无提交）输出 N 行 0，退出码 0。
- 当前时间在进程启动时确定一次，运行中跨午夜不重新计算。
- 实现上用 `git log --since`（按 committer date 粗筛）多取 2 天余量，再在 Python 里按 author date 精确过滤，避免大多数边界漏计。

## 退出码

| 码 | 含义 | 典型场景 |
| --- | --- | --- |
| `0` | 成功 | 正常输出、空仓库、`--author` 无匹配 |
| `2` | 用法/输入错误 | PATH 不存在、非 git 仓库、未知 rev、`--days` 非整数或越界 |
| `1` | 环境/运行错误 | 找不到 git、git 命令异常失败 |

自己的错误格式为一行：

```text
git7: error: <message>
```

错误时 stdout 为空；`argparse` 自身的参数错误按其默认格式输出，同样退出 2。

## 已知局限

- 不 clone/fetch，不访问网络；只统计本地已有仓库和本地可见的提交。
- 浅克隆/部分克隆可能缺少历史，计数会偏低，这是预期行为。
- 使用 author date 而非 committer date；rebase、cherry-pick、跨时区协作可能让个别提交的“归属日”与直觉不同。
- 不支持 bare 仓库；Windows 未纳入验收。
- 只支持“最近 N 天”，不支持任意起止日期；N 限制在 1~366。
- 不做跨仓库聚合、多作者排行、按目录/文件统计、图表、HTML 报告或打包发布。
- 未针对超大仓库/超深历史做性能优化；可用 `--rev` 缩小范围，但不承诺耗时。
- `--since` 的 2 天余量覆盖常见时区差；若 author/committer 日期相差超过 2 天（如异常时钟），窗口边界仍可能漏计。
- 暂不支持 `--committer-date`；JSON 模式下 `--total` 不生效。

## 测试

仅使用标准库 `unittest`，测试会自建临时 git 仓库，不会改动当前仓库：

```bash
python3 -m unittest discover -s tests -v
```

当前 17 个测试，覆盖分桶/补零/未来时间戳，以及 SPEC 的 AC-1~AC-11 和 AC-16 核心路径。AC-1~AC-16 的完整验收结果见本项目 `WORKLOG.md`。
