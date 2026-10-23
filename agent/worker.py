#!/usr/bin/env python3
"""常挂智能体的任务执行器。

由 systemd (dsh-agent.service) 托管，断 SSH、关界面、重启都不影响。
从 inbox/ 取任务，用一条持久 session 跑 dsh headless，结果落到 done/。
"""

import fcntl
import json
import os
import pathlib
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

HOME = pathlib.Path(os.environ.get("BOT_HOME") or pathlib.Path.home())
BASE = pathlib.Path(os.environ.get("AGENT_HOME", str(HOME / "agent")))
DSH = os.environ.get("AGENT_DSH_BIN", "dsh")
DSH_HOME = os.environ.get("DSH_HOME", str(HOME / ".dsh-user"))
ENV_FILE = pathlib.Path(os.environ.get("AGENT_ENV_FILE", str(pathlib.Path(DSH_HOME) / "dsh-web.env")))
PROFILE = os.environ.get("AGENT_PROFILE", "headless")
DEFAULT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "1800"))
BEAT_MINUTES = int(os.environ.get("AGENT_BEAT_MINUTES", "180"))
MAX_BEATS_PER_DAY = int(os.environ.get("AGENT_MAX_BEATS", "8"))
POLL_SECONDS = int(os.environ.get("AGENT_POLL", "5"))

INBOX = BASE / "inbox"
DONE = BASE / "done"
FAILED = BASE / "failed"
LOGS = BASE / "logs"
STATE = BASE / "state"
WORK = BASE / "work"
WORKDIR = pathlib.Path(os.environ.get("AGENT_WORKDIR", str(HOME)))
SESSION_FILE = STATE / "session.txt"
BEATS_FILE = STATE / "beats.json"
LAST_RUN_FILE = STATE / "last-run.txt"


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGS / "worker.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def read_text(path: pathlib.Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if limit:
        lines = text.splitlines()
        text = "\n".join(lines[-limit:])
    return text.strip()


def load_env() -> dict:
    env = os.environ.copy()
    env["DSH_HOME"] = DSH_HOME
    if not env.get("DEEPSEEK_API_KEY") and ENV_FILE.exists():
        try:
            for raw in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
                raw = raw.strip()
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                key, val = raw.split("=", 1)
                env.setdefault(key.strip(), val.strip().strip('"').strip("'"))
        except OSError:
            pass
    path = env.get("PATH", "")
    if os.name == "nt":
        extras = [
            r"C:\Program Files\nodejs",
            str(HOME / "AppData" / "Roaming" / "npm"),
        ]
    else:
        extras = [
            str(HOME / ".local" / "node" / "bin"),
            str(HOME / ".local" / "share" / "pnpm"),
            "/usr/local/bin", "/usr/bin", "/bin",
        ]
    sep = os.pathsep
    for extra in extras:
        if extra and extra not in path.split(sep):
            path = f"{extra}{sep}{path}"
    env["PATH"] = path
    return env


def get_session() -> str:
    return read_text(SESSION_FILE)


def save_session(sid: str) -> None:
    if sid:
        SESSION_FILE.write_text(sid + "\n", encoding="utf-8")


def drop_session() -> None:
    try:
        SESSION_FILE.unlink()
    except OSError:
        pass


def build_prompt(task_id: str, body: str) -> str:
    goal = read_text(BASE / "GOAL.md", 100)
    memory = read_text(BASE / "MEMORY.md", 120)
    worklog = read_text(BASE / "WORKLOG.md", 60)
    parts = [
        f"[无人值守任务 {task_id}]",
        "你是一个常驻服务器上的智能体，正在无人值守地执行任务。主人可能已经关掉界面，没人会回答你的提问，所以不要反问、不要等待确认，按最合理的做法直接做完。",
        f"工作区：{WORKDIR}（可读写）；产出优先放 {WORK}",
        f"结论和进度追加到：{BASE / 'WORKLOG.md'}（每次 2~6 行，只写关键信息）",
        f"长期记忆（需要时更新）：{BASE / 'MEMORY.md'}",
    ]
    if goal:
        parts.append("长期目标：\n" + goal)
    if memory:
        parts.append("长期记忆：\n" + memory)
    if worklog:
        parts.append("之前的工作记录（末尾部分）：\n" + worklog)
    parts.append("本次任务：\n" + body.strip())
    parts.append("现在开始执行。结束时用几行说明：做了什么、结果在哪、有没有遗留问题。")
    return "\n\n".join(parts) + "\n"


def parse_timeout(body: str) -> tuple[int, str]:
    """任务前几行可写 `#timeout: 秒` 覆盖默认超时。"""
    lines = body.splitlines()
    for i, line in enumerate(lines[:5]):
        if line.strip().lower().startswith("#timeout:"):
            try:
                val = int(line.split(":", 1)[1].strip())
                del lines[i]
                return max(30, val), "\n".join(lines).strip()
            except (ValueError, IndexError):
                break
    return DEFAULT_TIMEOUT, body


def run_dsh(prompt: str, timeout: int, log_path: pathlib.Path) -> dict:
    cmd = [DSH, "--profile", PROFILE, "--json"]
    sid = get_session()
    resumed = bool(sid)
    if resumed:
        cmd += ["--session-id", sid]
    cmd.append("-")

    result = {"ok": False, "text": "", "session": sid, "error": "", "resumed": resumed, "timed_out": False}
    err_path = log_path.with_suffix(".err.log")
    started = time.time()

    with open(log_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=err,
                cwd=str(WORKDIR),
                env=load_env(),
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except OSError as exc:
            result["error"] = f"启动失败: {exc}"
            return result

        q: queue.Queue = queue.Queue()

        def reader() -> None:
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    q.put(line)
            finally:
                q.put(None)

        threading.Thread(target=reader, daemon=True).start()
        try:
            assert proc.stdin is not None
            proc.stdin.write(prompt)
            proc.stdin.close()
        except OSError as exc:
            result["error"] = f"写入任务失败: {exc}"
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            return result

        deadline = started + timeout
        events = 0
        timed_out = False
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                timed_out = True
                break
            try:
                line = q.get(timeout=min(remaining, 60))
            except queue.Empty:
                if proc.poll() is not None:
                    break
                continue
            if line is None:
                break
            out.write(line)
            out.flush()
            events += 1
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = ev.get("type")
            if kind == "session" and ev.get("sessionId"):
                result["session"] = ev["sessionId"]
                save_session(ev["sessionId"])
            elif kind == "final":
                result["text"] = ev.get("text", "")
            elif kind == "status" and ev.get("reason", {}).get("kind") == "error":
                result["error"] = str(ev.get("reason", {}).get("error", {}).get("message", ""))[:500]
            elif kind == "error":
                result["error"] = str(ev.get("message", ""))[:500]

        if timed_out:
            result["timed_out"] = True
            result["error"] = f"超时 {timeout}s"
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        rc = proc.wait(timeout=30)
        result["duration"] = round(time.time() - started, 1)
        if rc != 0 and not result["text"] and not result["error"]:
            result["error"] = f"dsh 退出码 {rc}，无输出"

    # 只有明确的会话失效（工作目录变了/被清理/换机器）才重开；
    # 超时、被 kill、普通报错都保留会话，不能误伤上下文
    invalid = ("recorded in", "unknown session", "session not found", "no such session")
    if result["resumed"] and not result["text"] and not result["timed_out"] and any(k in result["error"].lower() for k in invalid):
        log(f"旧 session 失效（{result['error'][:120]}），改开新 session 重试")
        drop_session()
        retry = run_dsh(prompt, timeout, log_path.with_suffix(".retry.log"))
        retry["retried"] = True
        return retry

    result["ok"] = bool(result["text"]) and not result["error"]
    return result


def finish(task: pathlib.Path, status: str, body: str, result: dict, timeout: int) -> None:
    task_id = task.stem
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = [
        f"# 任务 {task_id}",
        "",
        f"- 状态：{status}",
        f"- 完成时间：{ts}",
        f"- 耗时：{result.get('duration', '?')}s（上限 {timeout}s）",
        f"- session：{result.get('session') or '未建立'}",
    ]
    if result.get("error"):
        md.append(f"- 错误：{result['error']}")
    md += ["", "## 原始任务", "", body.strip(), "", "## 结果", "", (result.get("text") or "（无输出）").strip(), ""]
    dest_dir = DONE if status == "done" else FAILED
    (dest_dir / f"{task_id}.md").write_text("\n".join(md), encoding="utf-8")
    shutil.move(str(task), str(dest_dir / f"{task_id}.task"))


def next_task() -> pathlib.Path | None:
    tasks = sorted(INBOX.glob("*.task"), key=lambda p: (p.stat().st_mtime, p.name))
    return tasks[0] if tasks else None


def last_run_ts() -> float:
    try:
        return float(read_text(LAST_RUN_FILE) or 0)
    except ValueError:
        return 0.0


def tick_projects() -> None:
    """把项目状态机推进一步（新任务会排进 inbox）。"""
    script = BASE / "project.py"
    if not script.exists():
        return
    try:
        with open(LOGS / "project.log", "a", encoding="utf-8") as out:
            subprocess.run(
                [sys.executable, str(script), "tick"],
                stdout=out,
                stderr=out,
                timeout=120,
                env=load_env(),
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"项目推进失败: {exc}")


def maybe_enqueue_beat() -> None:
    if not (BASE / "AUTONOMOUS").exists():
        return
    if (BASE / "GOAL.md").exists() is False or not read_text(BASE / "GOAL.md"):
        return
    if time.time() - last_run_ts() < BEAT_MINUTES * 60:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        beats = json.loads(read_text(BEATS_FILE) or "{}")
    except json.JSONDecodeError:
        beats = {}
    if beats.get("date") != today:
        beats = {"date": today, "count": 0}
    if beats.get("count", 0) >= MAX_BEATS_PER_DAY:
        return
    beats["count"] = beats.get("count", 0) + 1
    BEATS_FILE.write_text(json.dumps(beats), encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task = INBOX / f"{stamp}-beat.task"
    task.write_text(
        "没有新任务，这是自主推进的心跳。看看 GOAL.md 里还差什么，挑一件现在能做的事做完；"
        "如果目标已经完成或没什么可做的，就在 WORKLOG.md 里写一行“无待办”，不要硬凑。\n",
        encoding="utf-8",
    )
    log(f"心跳：已排队自主推进任务 {task.name}")


def main() -> None:
    for d in (INBOX, DONE, FAILED, LOGS, STATE, WORK):
        d.mkdir(parents=True, exist_ok=True)
    lock_path = STATE / "worker.lock"
    lock = open(lock_path, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("已有 worker 在跑，本实例退出")
        return
    log(f"worker 启动，pid={os.getpid()}，轮询 {POLL_SECONDS}s")
    last_tick = 0.0
    while True:
        task = next_task()
        if task is None:
            if time.time() - last_tick >= 15:
                last_tick = time.time()
                tick_projects()
            maybe_enqueue_beat()
            time.sleep(POLL_SECONDS)
            continue
        task_id = task.stem
        body = read_text(task)
        if not body:
            shutil.move(str(task), str(FAILED / f"{task_id}.task"))
            (FAILED / f"{task_id}.md").write_text(f"# {task_id}\n\n空任务，已跳过。\n", encoding="utf-8")
            continue
        timeout, body = parse_timeout(body)
        log(f"开始任务 {task_id}（超时 {timeout}s）")
        started = time.time()
        try:
            result = run_dsh(build_prompt(task_id, body), timeout, LOGS / f"{task_id}.jsonl")
        except Exception as exc:  # noqa: BLE001 - 单个任务失败不能带崩常驻进程
            result = {"ok": False, "text": "", "error": f"未捕获异常: {exc}", "session": get_session()}
            log(f"任务 {task_id} 异常: {exc}")
        status = "done" if result.get("ok") else "failed"
        try:
            finish(task, status, body, result, timeout)
        except OSError as exc:
            log(f"任务 {task_id} 写结果失败: {exc}")
        LAST_RUN_FILE.write_text(str(time.time()), encoding="utf-8")
        log(f"任务 {task_id} 结束：{status}，{round(time.time() - started, 1)}s")
        tick_projects()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
