# REPORT — git7 v0.1 验收

- 项目：`/home/ubuntu/agent/projects/1020-2105-git-7-python`
- 验收时间：2026-10-20 21:24
- 环境：Ubuntu 24.04，Python 3.12.3，git 2.43.0
- 验收方式：临时 git 仓库 + 固定 `TZ=UTC` / `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`，实跑 CLI 并与 `git log` oracle 对照
- 结论：**AC-1~AC-16 全部通过（16/16）**；unittest **17/17 通过**；本次验收未改动功能代码或 README，只新增本报告

## 一、逐条验收

| AC | 结果 | 证据 |
| --- | --- | --- |
| AC-1 | 通过 | 在含提交的临时仓库根执行 `python3 git7.py`：stdout 恰好 7 行，日期 `2026-10-14`..`2026-10-20` 连续升序，每行匹配 `^\d{4}-\d{2}-\d{2}  \d+$`；退出码 0，stderr 为空 |
| AC-2 | 通过 | 只有 2 天有提交的仓库：7 行中 5 行计数为 0，未省略日期；连续两次运行 stdout 完全一致 |
| AC-3 | 通过 | 含 merge 的仓库，7 天逐日计数与独立 oracle 完全一致；oracle 为 `git log --pretty=format:%at` 全量时间戳按本地时区分桶，误差 0 |
| AC-4 | 通过 | 在仓库 `sub/dir` 执行，stdout 与仓库根执行完全相同，stderr 为空 |
| AC-5 | 通过 | 非 git 目录执行：退出码 2，stdout 为空，stderr 为单行 `git7: error: not a git repository: <路径>`，含该路径 |
| AC-6 | 通过 | `git init` 后无提交的空仓库：退出码 0，stdout 恰好 7 行且每行为 0，stderr 为空 |
| AC-7 | 通过 | `--days 1` 输出 1 行（今天）；`--days 3` 输出 3 行且最后一行是今天；`--days 0`、`--days 367`、`--days abc` 均退出码 2、stdout 为空、stderr 含 `--days` |
| AC-8 | 通过 | `--rev feature` 的逐日计数与 `git log feature` oracle 一致；`--rev no-such-branch` 退出码 2，stderr 含 `unknown revision` |
| AC-9 | 通过 | 构造 Alice/Bob 各若干提交：`--author Alice` 与 `--author alice@example.com` 均与 oracle 一致；`--author Nobody` 输出 7 行 0、退出码 0 |
| AC-10 | 通过 | 构造 `--no-ff` merge：默认计数包含 merge，`--no-merges` 与 `git log --no-merges` oracle 一致，窗口内差值恰为 1 个 merge |
| AC-11 | 通过 | `--json` 可被 `json.loads` 解析；字段为 `repo` / `rev` / `days` / `total`；`repo` 为绝对路径，`days` 长度为 7 且升序，`total == sum(count)`；逐日计数与文本模式一致；经 `python3 -m json.tool` 验证通过 |
| AC-12 | 通过 | 源码 import 仅 `argparse` / `datetime` / `json` / `os` / `subprocess` / `sys`；`python3 -S git7.py` 在测试仓库输出与正常运行一致，退出码 0 |
| AC-13 | 通过 | `python3 git7.py >out.txt 2>err.txt`：stdout 恰好 7 行，无 ANSI 转义（无 `\x1b`），stderr 为空，退出码 0 |
| AC-14 | 通过 | `--help` 退出码 0、stderr 为空，stdout 含 `PATH`、`--days`、`--rev`、`--author`、`--no-merges`、`--json`、`--total` |
| AC-15 | 通过 | 在测试仓库执行 `env PATH=/nonexistent /usr/bin/python3 git7.py`：退出码 1，stdout 为空，stderr 为单行且含 `git` 与 `not found` |
| AC-16 | 通过 | 运行前后 `git status --porcelain` 与 `git rev-parse HEAD` 均不变；工具没有修改工作区或 HEAD |

验收明细日志：

- `/home/ubuntu/agent/work/verify-acceptance.txt`（16 条 AC 逐条 PASS）
- `/home/ubuntu/agent/work/verify-unittest.txt`（17 个测试 OK）

## 二、怎么用

### 环境

- Python 3.8+，git 2.0+，无需 `pip install`
- 把 `git7.py` 放在任意目录即可；可选 `chmod +x git7.py`

### 基本运行

```bash
python3 git7.py                  # 当前仓库，最近 7 天
python3 git7.py ~/code/app       # 指定仓库或仓库内子目录
python3 git7.py --days 14        # 最近 14 天
python3 git7.py --rev feature    # 指定分支/标签/提交
python3 git7.py --author alice@example.com  # 只看某个作者
python3 git7.py --no-merges      # 排除 merge
python3 git7.py --total          # 文本末尾加 total N
python3 git7.py --json           # JSON 输出，便于脚本消费
python3 git7.py --help           # 帮助
```

文本模式下 stdout 恰好 N 行（默认 7），日期从最早到今天，无提交日补 0；没有表头、颜色或空行。`--json` 输出对象：

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

示例只列 2 天，实际 `days` 长度为 N；`--json` 下 `--total` 被忽略。

### 口径

- 最近 N 个自然日（含今天），不是 N×24 小时。
- 按提交 **author date**（`%at`）在 **运行机器本地时区** 分日。
- 只统计从 `--rev`（默认 HEAD）可达的提交；merge 默认计入，`--no-merges` 排除。
- 空仓库输出 N 行 0、退出码 0。
- 实现用 `git log --since`（committer date 粗筛）多取 2 天余量，再按 author date 精确过滤。

### 退出码

| 码 | 含义 |
| --- | --- |
| 0 | 成功，含空仓库和 `--author` 无匹配 |
| 2 | 用法/输入错误：路径不存在、非 git 仓库、未知 rev、非法 `--days` |
| 1 | 环境/运行错误：找不到 git、git 命令异常失败 |

### 测试

```bash
python3 -m unittest discover -s tests -v
```

当前 17 个测试全部通过；更多说明见 `README.md`。

## 三、已知没做的部分

以下属于 SPEC 3.2 明确不做或已知局限，**不是 v0.1 验收失败项**：

- 不 clone/fetch、不访问网络、不调用 GitHub/GitLab API；只统计本地已有仓库。
- 不做跨仓库聚合、多作者排行、按目录/文件统计。
- 不支持任意起止日期区间；只支持最近 N 天，N 限制 1~366。
- 不统计增删行数、文件数、提交信息内容。
- 不做图形化、HTML、GUI、颜色、进度条；`--graph` 留 v0.2。
- 不做 PyPI 打包、单文件二进制、自动更新、配置文件或环境变量配置。
- 不做大仓库/超深历史性能专项优化；百万提交量级不承诺耗时。
- 浅克隆/部分克隆只统计本地可见提交，计数偏低不视为 bug。
- 固定 author date 口径；暂不支持 `--committer-date`，rebase/cherry-pick/跨时区可能影响归属日。
- 不支持 bare 仓库；Windows 未纳入验收。
- `--since` 的 2 天余量覆盖常见时区差；author/committer 日期相差超过 2 天的异常时钟仍可能漏计。
- JSON 模式下 `--total` 不生效；这是文档约定的行为。

## 四、验收结论

在 Python 3.12.3 + git 2.43.0 上，SPEC 的 AC-1~AC-16 全部实测通过，unittest 17/17 通过；`README.md` 已覆盖安装、3 个常用示例、日期/merge 口径、退出码、已知局限和测试方式。v0.1 达到 SPEC 的完成定义，无需修复功能代码，无阻塞。
