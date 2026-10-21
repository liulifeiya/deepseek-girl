2026-10-20 完成 1020-2105-git-7-python 立项：SPEC.md 定义 16 条可检验验收标准，固定文本/JSON 输出、退出码与日期口径（author date + 本地时区）。
技术选型：Python 3.8+ 标准库 + subprocess 调用系统 git（本机 2.43.0），用 `%at` 在本地时区分桶，零第三方依赖；已确认无 GitPython/rich 也能做。
PLAN.md 拆 6 条任务约 8h，首条为可运行 MVP；本阶段只立项未写实现，下一步按 T1 落地 git7.py。
2026-10-20 T1 完成：git7.py 支持 PATH 定位仓库、`git log %at` 取数、7 天本地日期分桶补零与文本输出；临时仓库冒烟通过（根目录/子目录/`-S`），运行 `python3 git7.py [PATH]`，并加最小 README。
2026-10-20 21:11 T1 复跑确认冒烟通过；顺带修复调度器 `enqueue` 未记录 `inflight.item` 导致同一任务重复排队的问题（仅改 `agent/project.py`，未动 PLAN 勾选）。
2026-10-20 21:14 T2 完成：新增 `--rev`；PATH 不存在/非仓库/未知 rev 退出 2，git 缺失退出 1，空仓库 7 行 0 退出 0；所有错误单行 stderr，子目录与只读验证通过。
2026-10-20 21:16 T3 完成：新增 `--days`（1..366）/`--author`/`--no-merges`；`--since` 留 2 天余量 + 作者日期精确过滤；非法天数与未知 rev 单行报错，矩阵测试通过。
2026-10-20 21:18 T4 完成：新增 `--json`（repo/rev/days/total）与 `--total`；JSON 与文本逐日一致，stdout 纯数据，空仓库/过滤/rev/重定向/`-S` 矩阵通过。
2026-10-20 21:20 T5 完成：新增 `tests/test_git7.py`（17 个 stdlib unittest）；固定 TZ=UTC + 临时仓库/固定提交时间，覆盖 count_by_day 与 AC-1~AC-11、AC-16；`discover -v` 全绿。
2026-10-20 21:22 T6 完成：README 全文（安装/3 示例/选项/输出/日期与 merge/退出码/局限/测试）；单元测试 `python3 -m unittest discover -s tests -v` 17/17 OK，AC-1~AC-16 用 `python3 /home/ubuntu/agent/work/t6_verify.py` 实跑 16/16 PASS（日志 `/home/ubuntu/agent/work/t6-acceptance.txt`）。
2026-10-20 21:24 验收完成：AC-1~AC-16 实跑 16/16 PASS，unittest 17/17 OK；REPORT.md 已生成，证据 `/home/ubuntu/agent/work/verify-acceptance.txt` 与 `verify-unittest.txt`。
