# SPEC — git7：统计 git 仓库最近 7 天每日提交数

- 项目：`/home/ubuntu/agent/projects/1020-2105-git-7-python`
- 状态：v0.1 立项（2026-10-20）
- 工具名：`git7`，入口 `git7.py`

## 1. 目标

`git7` 是一个零第三方依赖的 Python 命令行小工具：在任意 git 仓库（含其子目录）执行一条命令，按天列出最近 7 个自然日（含今天）的提交数；没有提交的日期显式补 0；可选用 JSON 输出供脚本消费。

设计目标：

1. **零配置、零安装**：系统有 Python 3.8+ 和 git，`python3 git7.py` 即可用，不需要 pip。
2. **结果可核对**：日期口径、时区、merge 处理方式固定并写入文档，输出可被测试断言。
3. **对机器友好**：默认 stdout 只有数据行，诊断只走 stderr；`--json` 输出稳定结构。
4. **克制**：只回答“最近 N 天每天多少提交”，不做代码分析、图表、打包、跨仓库聚合。

成功标准：新用户照 README 的 3 行示例就能得到正确结果；普通仓库（十万提交量级）默认命令秒级返回（体验目标，非硬性验收项）。

## 2. 典型使用场景

1. **站会/周报**：周五下午在项目根目录跑 `python3 git7.py`，一眼看出本周提交节奏和空档。
2. **指定仓库或分支**：`python3 git7.py ~/code/app --rev release/1.2`。
3. **只看自己的提交**：`python3 git7.py --author "zhangsan@example.com"`（git `--author` 语义，匹配作者名或邮箱）。
4. **CI / 看板取数**：`python3 git7.py --json | jq '.total'`。
5. **排除 merge 噪音**：`python3 git7.py --no-merges --days 14`。
6. **多仓库巡检**：`for d in ~/code/*/; do echo "== $d"; python3 git7.py "$d" --total; done`（聚合由 shell 完成，工具本身不做）。

## 3. 范围

### 3.1 做什么（v0.1）

- 统计本地已有仓库中、从 `rev`（默认 `HEAD`）可达的提交。
- 最近 N 个自然日（默认 7，含今天），按时间升序输出；无提交日补 0。
- 按提交的 **author date**（`%at`）分桶，使用运行机器的 **本地时区**。
- 默认包含 merge 提交；`--no-merges` 排除。
- `--author PATTERN` 透传 `git log --author`，只统计匹配作者。
- `--rev REV` 支持分支、标签、SHA。
- 文本输出（默认）、`--json`、`--total` 合计行。
- 明确的退出码与 stderr 错误提示；在仓库任意子目录可运行。
- 只读：不修改工作区、不写 refs、不 fetch、不联网。

### 3.2 明确不做（v0.1；部分留 v0.2）

- 不 clone/fetch，不访问网络，不调用 GitHub/GitLab API。
- 不做跨仓库聚合、多作者排行、按目录/文件统计。
- 不支持任意起止日期区间，只支持“最近 N 天”（1 ≤ N ≤ 366）。
- 不统计增删行数、文件数、提交信息内容。
- 不做图形化、HTML、GUI、颜色、进度条；`--graph` 留 v0.2。
- 不做 PyPI 打包、单文件二进制、自动更新、配置文件、环境变量配置。
- 不做大仓库性能专项优化，不承诺百万提交/超深历史的耗时。
- 不补齐浅克隆/部分克隆缺失的历史：只统计本地可见提交，结果偏低不视为 bug。
- 不提供 committer date 口径；`--committer-date` 留 v0.2。
- 不支持 bare 仓库（无工作区，`--show-toplevel` 不可用）；普通仓库和 worktree 支持。
- Windows 不纳入验收（代码避免平台特定 API，理论可用）。

### 3.3 运行环境

- Python ≥ 3.8，仅标准库（`argparse`、`subprocess`、`datetime`、`json`、`os`、`sys`、`pathlib`）。
- 系统 git ≥ 2.0（本机实测 2.43.0）。
- 主要目标 Linux/macOS 终端，UTF-8 环境。
- 无第三方 Python 依赖，不需要 pip / 虚拟环境。

## 4. 行为约定

### 4.1 命令行

```
python3 git7.py [PATH] [options]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `PATH` | `.` | 仓库路径，或仓库内任意子目录 |
| `--days N` | `7` | 统计最近 N 个自然日（含今天），1..366 |
| `--rev REV` | `HEAD` | 分支 / 标签 / SHA |
| `--author PATTERN` | 无 | 透传 `git log --author`，匹配作者名或邮箱 |
| `--no-merges` | 关 | 排除 merge 提交 |
| `--json` | 关 | 输出 JSON；此时 `--total` 被忽略 |
| `--total` | 关 | 文本模式末尾追加 `total N` |
| `-h`, `--help` | | 打印帮助 |

位置参数最多一个；选项与 PATH 顺序不限。

### 4.2 日期与计数口径（关键）

1. **“最近 7 天”** = 今天及之前 6 个自然日，共 7 天；不是“过去 168 小时”。今天从本地 00:00 起算。
2. **归属日** = 提交的 author timestamp（`%at`，UTC 秒）在运行机器本地时区对应的日期。跨时区协作时，同一提交在不同机器上可能落到不同日期，这是预期行为。
3. **可达性**：只统计从 `rev` 可到达的提交（`git log REV` 语义），不是全仓库所有 ref。
4. **merge**：默认计入（与 `git log` 默认一致）；`--no-merges` 用 git 同名选项排除。
5. **空仓库**（尚无提交）：输出 N 行 0，退出码 0。
6. **未来时间戳**：不在目标日期集合内，不计入任何一天。
7. **“今天”在进程启动时确定一次**；运行中跨午夜不重新计算。

### 4.3 文本输出

stdout 恰好 N 行，从最早到最近；日期 `YYYY-MM-DD`，两个空格，十进制次数（不补前导零），无表头、无空行、无颜色：

```
2026-10-14  0
2026-10-15  2
2026-10-16  0
2026-10-17  5
2026-10-18  1
2026-10-19  0
2026-10-20  3
```

加 `--total` 时，在数据行后追加一行：`total 11`。

诊断和错误只写 stderr；输出不因 stdout 是否为 TTY 而变化，便于重定向和管道。

### 4.4 JSON 输出

`--json` 时 stdout 只有一个 JSON 对象（UTF-8，缩进 2 空格），无其他内容：

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

> 示例为节省篇幅只列 2 天；实际 `days` 长度等于 N（默认 7）。

- `repo`：`git rev-parse --show-toplevel` 得到的绝对路径。
- `rev`：用户传入值（默认 `"HEAD"`，不解析成 SHA）。
- `days`：长度为 N，日期连续升序，每项含 `date`、`count`。
- `total`：所有 `count` 之和。
- 不输出 `generated_at` 等时间戳，避免测试和缓存噪声。

### 4.5 退出码与错误

| 码 | 含义 | 例子 |
| --- | --- | --- |
| 0 | 成功（含空仓库、author 无匹配） | |
| 2 | 用法/输入错误 | PATH 不存在、非 git 仓库、rev 不存在、`--days` 越界或非整数 |
| 1 | 环境/运行时错误 | 找不到 git、git 命令异常失败 |

错误写 stderr，单行，格式：

```
git7: error: <message>
```

`argparse` 自身的参数解析错误（如 `--days abc`、未知选项）按 argparse 默认格式输出，同样退出 2；`git7` 自己抛出的错误统一用上述 `git7: error:` 前缀。

典型 message：

- `not a git repository: /tmp/x`
- `unknown revision: no-such-branch`
- `--days must be an integer between 1 and 366`
- `git executable not found`
- `git log failed: <git stderr 首行>`

用法错误时 stdout 必须为空。

## 5. 可检验的验收标准

测试仓库用 `git init` + `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE` 构造固定日期的提交；涉及“今天”的断言由测试进程的本地日期计算，测试固定 `TZ`，提交时间取当天 12:00，避免午夜边界抖动。

| 编号 | 验收标准 | 验证方法 |
| --- | --- | --- |
| AC-1 | 默认输出恰好 7 行，日期为今天往前 6 天至今天、连续升序，每行匹配 `^\d{4}-\d{2}-\d{2}  \d+$`，退出码 0，stderr 为空 | 在含提交的测试仓库根执行 `python3 git7.py`，逐行断言 |
| AC-2 | 无提交的日期不被省略，次数为 0；行数恒为 7 | 构造只有 2 天有提交的仓库，其余 5 行断言为 0；重复运行输出一致 |
| AC-3 | 每日计数准确：包含 merge 的默认口径下，与独立 oracle 完全一致 | oracle：`git log --pretty=%at` 全量取时间戳，按同一本地时区规则分桶；逐日比对，误差为 0 |
| AC-4 | 在仓库任意子目录运行，结果与仓库根一致 | 在 `sub/dir` 下执行，stdout 与根目录执行完全相同 |
| AC-5 | 非 git 目录：退出码 2，stdout 为空，stderr 含 `not a git repository` 和该路径 | `mktemp -d` 后执行 |
| AC-6 | 空仓库（`git init` 后无提交）：退出码 0，N 行全 0，stderr 为空 | 临时空仓库执行 |
| AC-7 | `--days 1` 输出 1 行（今天）；`--days 3` 输出 3 行且最后一行是今天；`--days 0`、`--days 367`、`--days abc` 均退出码 2、stdout 为空、stderr 含 `--days` | 分别执行并断言 |
| AC-8 | `--rev <branch>` 只统计该分支可达提交；不存在的 rev 退出码 2，stderr 含 `unknown revision` | 构造含 `feature` 分支的仓库；与 `git log feature` oracle 比对；再传 `--rev no-such-branch` |
| AC-9 | `--author` 只统计匹配作者；无匹配时输出 N 行 0、退出码 0 | 构造 Alice、Bob 各若干提交；传两者邮箱分别执行，与 oracle 比对；再传不存在作者 |
| AC-10 | 默认包含 merge；`--no-merges` 后计数减少，差值等于窗口内 merge 提交数 | 构造带 `--no-ff` merge 的仓库，与 `git log --no-merges` oracle 比对 |
| AC-11 | `--json` 输出可被 `json.loads` 解析；含 `repo`（绝对路径）、`rev`、长度为 N 的 `days`、`total`；`total == sum(count)`；逐日计数与文本模式一致；退出码 0 | `python3 git7.py --json \| python3 -m json.tool`，再解析断言 |
| AC-12 | 仅使用 Python 标准库：加 `-S`（禁用 site-packages）仍可运行；源码 import 均为标准库 | `python3 -S git7.py` 在测试仓库执行成功；检查源码 import 列表 |
| AC-13 | 重定向/管道安全：stdout 恰好 N 行、无 ANSI 转义（`\x1b`）、无警告，stderr 为空，退出码 0 | `python3 git7.py >out.txt 2>err.txt` 后断言 |
| AC-14 | `--help` 退出码 0，stdout 列出 PATH、`--days`、`--rev`、`--author`、`--no-merges`、`--json`、`--total`，stderr 为空 | 执行 `python3 git7.py --help` 并检查关键字 |
| AC-15 | git 不可用：退出码 1，stdout 为空，stderr 含 `git` 与 `not found` | 在测试仓库执行 `env PATH=/nonexistent /usr/bin/python3 git7.py` |
| AC-16 | 只读：运行前后 `git status --porcelain` 与 `git rev-parse HEAD` 不变 | 运行前后各取一次并比对 |

## 6. 技术选型与理由

### 6.1 选型

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 语言/运行时 | Python 3.8+，仅标准库 | 本机已装 3.12.3；小工具无需依赖；`-S` 可证明零第三方 |
| 取数方式 | `subprocess` 调用系统 `git`，参数列表传参 | 本机 git 2.43.0；git 原生支持 `--since`、`--author`、`--no-merges`；不拼 shell，路径含空格安全 |
| 时间字段 | `%at` + Python `datetime.fromtimestamp` | 统一按本地时区切日；避免 `--date=short` 按每个提交自带偏移分桶导致跨时区不一致 |
| 参数解析 | `argparse` | 标准库，自动 help/报错，足够 |
| 测试 | `unittest` + 临时仓库 | 标准库即可；用固定 `GIT_AUTHOR_DATE` 构造确定性历史 |
| 代码组织 | 单文件 `git7.py` + `tests/test_git7.py` | 体量小，复制即用；不引入包/打包 |

### 6.2 被否方案

- **GitPython**：本机未安装；为一次 `git log` 引入依赖不划算，且仍要处理同一套日期口径。
- **pygit2 / libgit2**：需编译或安装二进制，超出小工具需求。
- **直接解析 `.git` 对象**：packfile、worktree、SHA-256 仓库等兼容性差，等于重写 git。
- **`git log --date=short | sort | uniq -c` 管道**：按提交自带时区偏移切日，与本机“每天”口径不一致；补零和跨平台都麻烦。
- **`git shortlog`**：按作者聚合，拿不到“零提交日”，不适合本需求。
- **click/rich 等 CLI 库**：只为一个命令引入依赖，违背零安装目标。

### 6.3 实现要点（供 build 阶段参考）

1. 用 `git -C PATH rev-parse --show-toplevel` 定位仓库根；失败则按“非仓库/路径不存在”报错退出 2。
2. 取数：`git -C root log REV --since=<start-2d>T00:00:00 --pretty=format:%at`；`--since` 按 committer date 粗筛，因此多留 2 天余量，再在 Python 里按 author date 精确过滤。`--author`、`--no-merges` 直接追加为 git 参数。
3. 目标日期集合 `{today-(N-1), …, today}`；不在集合内的时间戳丢弃；输出固定按日期升序。
4. 空仓库：未显式传 `--rev`（或显式传 `HEAD`）且 `git rev-parse --verify HEAD` 失败时按全 0 处理（退出 0）；其他显式 rev 不存在报 `unknown revision`（退出 2）。
5. 纯函数 `count_by_day(timestamps, today, days)` 负责分桶，便于单测；CLI 只做参数、IO 和错误映射。
6. 不打印表头，不做 TTY 检测，不输出颜色。
7. 所有 git 调用设置 `text=True`、捕获 stderr；错误消息取 stderr 首行，避免多行污染。

### 6.4 目录结构（计划）

```
git7.py                 # CLI 入口（T1 起）
tests/test_git7.py      # unittest（T5）
README.md               # 用法、口径、局限（T6）
SPEC.md
PLAN.md
WORKLOG.md
```

## 7. 主要风险

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 日期口径歧义（author vs committer、时区） | 用户觉得“数字不对” | 文档固定为 author date + 本地时区；JSON/文本同一口径；测试固定 TZ；v0.2 再加 `--committer-date` |
| `--since` 按 committer date 粗筛，与 author date 分桶不一致 | 窗口边界漏计 | 多取 2 天余量后在 Python 精确过滤；测试覆盖边界提交 |
| 跨时区提交归属日与用户直觉不同 | 个别提交落错天 | 明确“以运行机器本地时区为准”；文档举例说明 |
| 大仓库/超深历史遍历慢 | 命令等待 | 7 天窗口 + git 原生过滤；`--rev` 可缩小范围；不承诺大仓性能（非 v0.1 目标） |
| 浅克隆/部分克隆历史不全 | 计数偏低 | 文档声明只统计本地可见提交，不视为 bug |
| rebase / cherry-pick 改变提交时间 | 历史统计变化 | 采用 author date（rebase 通常保留），并在文档说明数字可能随历史改写变化 |
| git 版本/平台差异（旧版缺参数） | 命令失败 | 要求 git ≥ 2.0；失败时原样返回 git stderr 首行，退出 1 |
| 空仓库、非法 rev、非法 `--days` 混淆 | 误报或错误码不一致 | 明确 0/2/1 退出码与消息；AC-5~AC-8 覆盖 |
| 测试依赖“今天”，午夜附近抖动 | CI 偶发失败 | 分桶函数注入 `today`；测试固定 `TZ`，提交时间取 12:00，必要时冻结日期参数 |
| 输出被终端编码/颜色污染 | 管道解析失败 | 纯 ASCII 文本、无颜色；AC-13 检查 `\x1b` |

## 8. 交付与完成定义

v0.1 交付物：

- `git7.py`：可执行入口，覆盖 3.1 全部功能。
- `tests/test_git7.py`：`python3 -m unittest discover -s tests -v` 全绿，覆盖 AC-1~AC-11、AC-16 的核心路径。
- `README.md`：安装/运行、日期口径、退出码、已知局限、3 个示例。
- `SPEC.md`、`PLAN.md`、`WORKLOG.md`。

完成定义：AC-1~AC-16 在 Linux + Python 3.12 + git 2.43 上实测通过；不安装任何第三方包；仓库工作区未被修改。未完成项只能来自 3.2 的“明确不做”，且需在 README 中列为已知限制。
