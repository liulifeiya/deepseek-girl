# WORKLOG

2026-10-20 22:31 重新拉起项目：原项目目录在 21:05 的 build 失败后丢失，从 selftest 备份恢复 SPEC.md，重建目录与 PLAN（6 条任务）。环境复核：Python 3.12.3、markdown-it-py 3.0.0、pip 镜像可用（需绕过失效代理）。

2026-10-20 22:33 完成 T1：包结构、pyproject、argparse 全选项、stdin/文件/多文件/`-o`、编码/BOM、退出码。冒烟：示例 A 逐字节一致。

2026-10-20 22:35 完成 T2：标题三样式、段落硬/软换行、行内元素、嵌套/有序/任务列表、引用、围栏/缩进代码、分隔线。示例 B/C 精确匹配；引用内软换行按源行保留以对齐 AC-07。

2026-10-20 22:37 完成 T3：表格 aligned/tsv/pipe、CJK/emoji 宽度、HTML 清洗、实体单次解码、frontmatter 三重判定与保留模式。示例 D/E 精确匹配。

2026-10-20 22:38 完成 T4：`--wrap` 显示宽度折行（URL/行内代码原子）、错误码 1/2/130、broken pipe、递归/二进制/10MB 单行防护。示例 F 精确匹配；`--wrap 9` 退出 2。

2026-10-20 22:39 完成 T5：83 个 unittest 全绿；coverage 90%（690 语句，68 未覆盖）；5.0MB 基准 4.08s/186MB；两次输出 cmp 一致，无网络 import。

2026-10-20 22:40 完成 T6：干净 venv `pip install .` 成功，`md2txt`/`python -m md2txt` 版本一致；README/CHANGELOG 完成；AC-01~AC-18 验收记录见 REPORT.md 与 agent/work/md2txt-acceptance.txt。
