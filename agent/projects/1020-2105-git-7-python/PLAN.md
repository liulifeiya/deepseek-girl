# PLAN — git7 v0.1

6 条任务，约 8 小时；每条 1~2 小时，按顺序做。第一条是能跑起来的最小版本，后面逐步补错误处理、选项、输出和测试。本阶段只做 SPEC 3.1 范围内的功能。

- [x] T1（1.5h，MVP）创建 `git7.py`：`argparse` 接收可选 `PATH`（默认 `.`），用 `git -C PATH rev-parse --show-toplevel` 定位仓库根，`git log HEAD --since=... --pretty=format:%at` 取最近 7 天的时间戳，按本地日期分桶并对 7 个自然日补零，stdout 输出 7 行 `YYYY-MM-DD  次数`（今天-6 至今天，升序），退出码 0；在一个临时仓库手工冒烟通过。
- [x] T2（1h，健壮性）补齐错误路径：PATH 不存在或不是 git 仓库、git 未安装、默认 HEAD 的空仓库、显式 rev 不存在，分别映射到 SPEC 4.5 的退出码 1/2 与单行 stderr；确保仓库子目录可运行，且运行不改动工作区。
- [x] T3（1.5h，选项）实现 `--days N`（1..366，含参数校验）、`--rev REV`、`--author PATTERN`、`--no-merges`；取数时 `--since` 多留 2 天余量，再在 Python 里按 author date 精确过滤，避免边界漏计；补上 `--days` 非法值与未知 rev 的报错。
- [x] T4（1h，输出）实现 `--json`（字段 `repo` / `rev` / `days[]` / `total`，与文本模式逐日一致）和 `--total`（文本末尾一行 `total N`）；保证 stdout 只有数据、无颜色/警告，重定向与管道下格式不变。
- [x] T5（2h，测试）新增 `tests/test_git7.py`（stdlib `unittest`）：单测 `count_by_day` 的分桶/补零/未来时间戳，集成测试用临时仓库 + 固定 `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`（当天 12:00，固定 `TZ`）覆盖 AC-1~AC-11 与 AC-16 的核心路径；`python3 -m unittest discover -s tests -v` 全绿。
- [x] T6（1h，文档与验收）写 `README.md`：安装/运行、日期与 merge 口径、退出码、已知局限、3 个常用示例；按 SPEC 第 5 节把 AC-1~AC-16 实跑一遍，把命令与结果摘要写入本项目 `WORKLOG.md`，确认无第三方依赖。

## 执行说明

- 依赖顺序：T1 → T2 → T3 → T4；T5 跟在前四条之后；T6 最后。T2/T3 改动取数与错误映射时，同步保持 T1 的默认输出格式不变。
- 每条任务完成即自测，至少运行 `python3 git7.py --help` 和一次真实仓库统计；T5 之后以测试套件为准。
- 时间盒：单条超过 2 小时就收窄到 SPEC 3.1 的最小行为，把扩展记入 v0.2，不拖长。
- v0.2 候选（本次不做）：`--committer-date`、`--graph`（ASCII 柱状图）、任意起止日期、多仓库/多作者聚合、PyPI 打包、大仓库性能优化。
- 全程不引入第三方依赖，不改仓库内容，不做打包发布与覆盖率门禁。
