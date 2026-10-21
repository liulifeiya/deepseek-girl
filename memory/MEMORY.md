# 长期记忆

- 常用路径：项目在 `/home/ubuntu/agent/projects/`，产出/草稿放 `/home/ubuntu/agent/work/`，工作记录 `agent/WORKLOG.md`。
- 机器环境（2026-10 实测）：Ubuntu 24.04，Python 3.12.3，Node 24.19（内置 fetch/WebSocket/node:test），git 2.43.0；`markdown-it-py 3.0.0` 系统预装，PyYAML 6.0.1；无 GitPython/rich/pytest/wcwidth/coverage，但 pip 内网镜像可装；setuptools 68.1.2 + wheel + venv 可用。
- 做 Python CLI 时优先标准库 + 已预装库，避免重依赖；测试优先 `unittest`，需要覆盖率再装 `coverage`。
- 已完成：`projects/1020-2101-markdown-python`（md2txt，Markdown→纯文本 CLI）。2026-10-20 重新拉起并做完：AC-01~18 18/18，83 个 unittest 全绿、覆盖率 90%，5MB 基准 4.08s/186MB，REPORT.md 已生成，项目 done。教训：项目目录曾因 build 子 session 无输出而丢失，SPEC 可从 `agent/logs/selftest/` 找回。
- 已立项：`projects/1020-2105-git-7-python`（git7，统计最近 N 天每日提交数）；SPEC/PLAN 完成，方案为 stdlib subprocess 调 git `%at` + 本地时区分桶，零依赖；T1-T6 已完成并验收：AC-1~16 实跑 16/16、unittest 17/17，REPORT.md 已生成，项目 done。注：`agent/project.py` 的 `enqueue` 已补记 `inflight.item`，否则 build 任务会重复排队。
- 已立项：`projects/1020-2127-astrbot-onebot-node`（group-autochat，群聊自主接话）；零依赖 Node.js + OneBot 11 HTTP sidecar/库内嵌，只读现有 group-wake 补丁、不改线上插件；SPEC 17 AC / PLAN 6 任务完成；T1-T6 已完成并验收：node --test 23/23、AC-1~17 17/17，REPORT.md 已生成，项目 done。
