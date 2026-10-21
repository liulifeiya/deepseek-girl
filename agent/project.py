#!/usr/bin/env python3
"""立项 → 实施 → 验收 的项目驱动器。

不自己调模型：把每一步做成任务丢进 inbox，由 worker.py 执行；
执行完回来看结果，决定下一步。

    project.py new "想法" [--auto]
    project.py list
    project.py show <slug>
    project.py approve <slug>
    project.py pause|resume <slug>
    project.py tick            # 推进所有项目（worker 每轮自动调用）
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(os.environ.get("AGENT_HOME", "/home/ubuntu/agent"))
PROJ = BASE / "projects"
INBOX = BASE / "inbox"
DONE = BASE / "done"
FAILED = BASE / "failed"
NOTIFY = BASE / "NOTIFY.log"

POLICY = """你在无人值守地推进一个软件项目，没人会回答你的提问，按最合理的做法直接做完。
不要反问、不要等确认。机器上能装的东西有限，先看环境再决定用啥（python3/node 一般都有）。"""


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def notify(msg: str) -> None:
    line = f"[{ts()}] {msg}"
    try:
        with open(NOTIFY, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    hook = BASE / "hooks" / "on-notify.sh"
    if hook.exists():
        try:
            os.system(f"bash {hook} {json.dumps(msg)} >/dev/null 2>&1")
        except OSError:
            pass


def slugify(idea: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", idea.lower())
    core = "-".join(words[:3])[:28] or "proj"
    return f"{datetime.now().strftime('%m%d-%H%M')}-{core}"


def state_path(slug: str) -> Path:
    return PROJ / slug / "state.json"


def load(slug: str) -> dict:
    return json.loads(state_path(slug).read_text(encoding="utf-8"))


def save(slug: str, st: dict) -> None:
    st["updated"] = ts()
    state_path(slug).write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def new_project(idea: str, auto: bool = False) -> str:
    slug = slugify(idea)
    d = PROJ / slug
    d.mkdir(parents=True, exist_ok=False)
    (d / "IDEA.md").write_text(f"# 想法\n\n{idea.strip()}\n", encoding="utf-8")
    st = {
        "slug": slug,
        "idea": idea.strip(),
        "phase": "spec",
        "auto": auto,
        "created": ts(),
        "updated": ts(),
        "inflight": None,
        "attempts": {},
        "blocked": False,
        "paused": False,
    }
    save(slug, st)
    notify(f"立项：{slug} — {idea.strip()[:60]}")
    enqueue_spec(slug, st)
    return slug


def pid_file(slug: str, kind: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}-{kind}"


def enqueue(slug: str, st: dict, kind: str, body: str, item: str | None = None) -> str:
    task_id = pid_file(slug, kind)
    INBOX.mkdir(exist_ok=True)
    (INBOX / f"{task_id}.task").write_text(
        f"#project: {slug}\n" + body.strip() + "\n", encoding="utf-8"
    )
    inflight = {"task_id": task_id, "kind": kind, "since": ts()}
    if item is not None:
        inflight["item"] = item
    st["inflight"] = inflight
    save(slug, st)
    return task_id


def spec_body(slug: str, st: dict) -> str:
    d = PROJ / slug
    return f"""{POLICY}
#timeout: 2400

给下面这个想法做立项，项目目录：{d}
想法：{st['idea']}

产出两个文件（直接在项目目录里写）：
1. SPEC.md —— 目标、典型使用场景、范围（做什么 / 明确不做什么）、可检验的验收标准、技术选型与理由、主要风险。
2. PLAN.md —— 实施计划，任务清单必须是这种格式，一行一条：
- [ ] 任务描述

计划要克制：最多 6 条，每条 30 分钟到 2 小时。
第一条必须是能跑起来的最小版本（MVP），后面再逐步补功能。
不要一上来就铺边界情况、性能压测、打包发布、覆盖率门禁、完整测试矩阵——那是 v0.2 的事。

先花一两分钟看环境（python3/node 版本、有没有现成可用的库），别选装不了的东西。
这一步只立项，不写实现代码。做完往项目目录的 WORKLOG.md 追加三行摘要。"""


def build_body(slug: str, st: dict, item: str) -> str:
    d = PROJ / slug
    return f"""{POLICY}
#timeout: 3600

继续实现项目 {slug}，项目目录：{d}
SPEC.md 和 PLAN.md 都在里面，先读一遍。

本次只做这一条任务：
{item}

要求：真做完并自测（能跑的跑一遍），代码放在项目目录里合适的位置，顺手补上怎么运行。
不要改动 PLAN.md 的勾选状态，完成情况追加一行到项目目录的 WORKLOG.md。"""


def verify_body(slug: str, st: dict) -> str:
    d = PROJ / slug
    return f"""{POLICY}
#timeout: 2400

项目 {slug} 的实现任务都已做完，现在验收。项目目录：{d}

按 SPEC.md 的验收标准逐条核对，能实际运行的就真跑一遍。
产出 REPORT.md：每条验收标准 → 通过/不通过 + 证据；再写「怎么用」和「已知没做的部分」。
除非发现明显 bug，否则不改功能代码；改了要在 REPORT.md 里写明。"""


def replan_body(slug: str, st: dict) -> str:
    d = PROJ / slug
    n = len(parse_plan(slug))
    return f"""{POLICY}
#timeout: 1200

项目 {slug} 的 PLAN.md 现在有 {n} 条任务，太多了，跑不完也看不清进展。
项目目录：{d}

请重写 PLAN.md：最多 6 条，按依赖排序，第一条是能跑的最小版本，后面每条是能在一次会话里做完的量。
已经完成的部分保留为已完成（- [x]），不要丢。
只改 PLAN.md，不要动代码，也不要动 SPEC.md 的验收标准（可以精简到 v0.1 范围，但要在文件里标明哪些是 v0.2）。"""


def enqueue_spec(slug: str, st: dict) -> None:
    enqueue(slug, st, "spec", spec_body(slug, st))


def parse_plan(slug: str) -> list[tuple[int, str, str]]:
    """返回 [(行号, 状态, 任务文本)]，状态是 ' ' 或 'x'。"""
    path = PROJ / slug / "PLAN.md"
    if not path.exists():
        return []
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        m = re.match(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$", line)
        if m:
            out.append((i, m.group(1).lower(), m.group(2)))
    return out


def check_off(slug: str, item: str) -> None:
    path = PROJ / slug / "PLAN.md"
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*[-*]\s*\[)( |x|X)(\]\s*)(.*)$", line)
        if m and m.group(4).strip() == item.strip():
            lines[i] = f"{m.group(1)}x{m.group(3)}{m.group(4)}"
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def result_status(task_id: str) -> str | None:
    if (DONE / f"{task_id}.md").exists():
        return "done"
    if (FAILED / f"{task_id}.md").exists():
        return "failed"
    return None


def bump(st: dict, key: str) -> int:
    n = st["attempts"].get(key, 0) + 1
    st["attempts"][key] = n
    return n


def block(slug: str, st: dict, why: str) -> None:
    st["blocked"] = True
    st["inflight"] = None
    st["blocked_reason"] = why
    save(slug, st)
    d = PROJ / slug
    (d / "NEED-HELP.md").write_text(
        f"# 需要人看一下\n\n- 时间：{ts()}\n- 阶段：{st['phase']}\n- 原因：{why}\n\n恢复：修掉问题后 `~/agent/bin/agent --project-resume {slug}`\n",
        encoding="utf-8",
    )
    notify(f"项目 {slug} 卡住了：{why}")


def tick_one(slug: str) -> None:
    st = load(slug)
    if st.get("paused") or st.get("blocked") or st["phase"] == "done":
        return
    d = PROJ / slug
    inflight = st.get("inflight")

    # 1) 处理上一轮的结果
    if inflight:
        status = result_status(inflight["task_id"])
        if status is None:
            return  # 还在跑
        kind = inflight["kind"]
        st["inflight"] = None
        if status == "failed":
            n = bump(st, f"{kind}:{inflight.get('item', '')}")
            if n >= 3:
                block(slug, st, f"{kind} 连续失败 {n} 次，最后一次看 {FAILED / (inflight['task_id'] + '.md')}")
                return
            notify(f"{slug}：{kind} 失败一次（第 {n} 次），稍后重试")
            save(slug, st)
            return
        # 成功
        if kind == "spec":
            spec_ok = (d / "SPEC.md").exists() and (d / "SPEC.md").stat().st_size > 200
            plan_ok = len(parse_plan(slug)) > 0
            if not (spec_ok and plan_ok):
                n = bump(st, "spec")
                if n >= 3:
                    block(slug, st, "立项产出不完整（SPEC.md 或 PLAN.md 缺失/为空）")
                    return
                save(slug, st)
                enqueue_spec(slug, st)
                return
            if len(parse_plan(slug)) > 8 and bump(st, "replan") <= 1:
                save(slug, st)
                enqueue(slug, st, "replan", replan_body(slug, st))
                return
            st["phase"] = "build" if st.get("auto") else "review"
            if st["phase"] == "review":
                notify(f"{slug}：立项完成，等你点头（agent --project-approve {slug}）")
        elif kind == "replan":
            if len(parse_plan(slug)) > 10:
                block(slug, st, f"计划压缩失败，仍有 {len(parse_plan(slug))} 条任务")
                return
            st["phase"] = "build" if st.get("auto") else "review"
        elif kind == "build":
            check_off(slug, inflight.get("item", ""))
            if not parse_plan(slug):
                pass
        elif kind == "verify":
            if (d / "REPORT.md").exists():
                st["phase"] = "done"
                notify(f"{slug}：验收完成，看 {d / 'REPORT.md'}")
                save(slug, st)
                return
            n = bump(st, "verify")
            if n >= 2:
                block(slug, st, "验收没产出 REPORT.md")
                return
        save(slug, st)

    # 2) 排下一步
    if st["phase"] == "spec":
        if not (d / "PLAN.md").exists() or not (d / "SPEC.md").exists():
            enqueue_spec(slug, st)
        else:
            st["phase"] = "build" if st.get("auto") else "review"
            save(slug, st)
    elif st["phase"] == "review":
        return
    elif st["phase"] == "build":
        pending = [(i, t) for i, s, t in parse_plan(slug) if s == " "]
        if pending:
            st["steps"] = st.get("steps", 0) + 1
            if st["steps"] > 40:
                block(slug, st, "实施步数超过 40，疑似计划失控")
                return
            enqueue(
                slug,
                st,
                "build",
                build_body(slug, st, pending[0][1]),
                item=pending[0][1],
            )
        else:
            st["phase"] = "verify"
            save(slug, st)
            enqueue(slug, st, "verify", verify_body(slug, st))
    elif st["phase"] == "verify":
        enqueue(slug, st, "verify", verify_body(slug, st))


def tick() -> None:
    PROJ.mkdir(exist_ok=True)
    for d in sorted(PROJ.iterdir()):
        if not (d / "state.json").exists():
            continue
        try:
            tick_one(d.name)
        except Exception as exc:  # noqa: BLE001
            notify(f"项目 {d.name} tick 异常：{exc}")


def cmd_show(slug: str) -> None:
    st = load(slug)
    d = PROJ / slug
    print(f"项目 {slug}  阶段={st['phase']}  自动={st['auto']}  卡住={st['blocked']}  暂停={st['paused']}")
    print(f"目录：{d}")
    if st.get("blocked_reason"):
        print(f"原因：{st['blocked_reason']}")
    if st.get("inflight"):
        print(f"进行中：{st['inflight']['task_id']}")
    plan = parse_plan(slug)
    if plan:
        done = sum(1 for _, s, _ in plan if s == "x")
        print(f"进度：{done}/{len(plan)}")
        for _, s, t in plan:
            print(f"  [{'x' if s == 'x' else ' '}] {t}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "new":
        auto = "--auto" in args
        idea = " ".join(a for a in args[1:] if a != "--auto").strip()
        if not idea:
            sys.exit("用法: project.py new \"想法\" [--auto]")
        slug = new_project(idea, auto)
        print(f"已立项：{slug}")
        print(f"目录：{PROJ / slug}")
    elif cmd == "tick":
        tick()
    elif cmd == "list":
        for d in sorted(PROJ.iterdir()):
            if (d / "state.json").exists():
                st = load(d.name)
                flag = "卡住" if st["blocked"] else st["phase"]
                print(f"{d.name:32s} {flag:8s} {st['idea'][:50]}")
    elif cmd == "show":
        cmd_show(args[1])
    elif cmd == "approve":
        slug = args[1]
        st = load(slug)
        if st["phase"] == "review":
            st["phase"] = "build"
            st["auto"] = True
            save(slug, st)
            notify(f"{slug}：已批准，开始实施")
        print(f"{slug} 现在是 {st['phase']}")
        tick()
    elif cmd in ("pause", "resume"):
        slug = args[1]
        st = load(slug)
        st["paused"] = cmd == "pause"
        if cmd == "resume":
            st["blocked"] = False
            st["blocked_reason"] = ""
        save(slug, st)
        print(f"{slug} paused={st['paused']} blocked={st['blocked']}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
