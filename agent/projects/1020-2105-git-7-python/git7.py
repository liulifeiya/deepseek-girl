#!/usr/bin/env python3
"""git7 — count commits per day over the last N days.

Usage:
    python3 git7.py [PATH] [options]

Options:
    --days N          number of days, 1..366 (default: 7)
    --rev REV         branch, tag, or commit (default: HEAD)
    --author PATTERN  only count authors matching PATTERN
    --no-merges       exclude merge commits
    --json            print a JSON object instead of text lines
    --total           append a "total N" line in text mode

PATH defaults to "." and may point at a repository or any directory inside it.
Text output is exactly N lines, oldest first:

    2026-10-14  0
    2026-10-15  2
    ...

Only the Python standard library and the `git` executable are required.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

DAYS = 7
MAX_DAYS = 366
SINCE_MARGIN_DAYS = 2


def fail(message, code):
    # Keep every diagnostic on one stderr line.
    message = str(message).replace("\r", " ").replace("\n", " ")
    print("git7: error: {}".format(message), file=sys.stderr)
    raise SystemExit(code)


def git(args):
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True)
    except FileNotFoundError:
        fail("git executable not found", 1)
    except OSError as exc:
        fail("failed to run git: {}".format(exc), 1)


def repo_root(path):
    if not os.path.exists(path):
        fail("path does not exist: {}".format(path), 2)
    proc = git(["-C", path, "rev-parse", "--show-toplevel"])
    root = proc.stdout.strip()
    if proc.returncode != 0 or not root:
        fail("not a git repository: {}".format(path), 2)
    return root


def commit_exists(root, rev):
    proc = git(["-C", root, "rev-parse", "--verify", "--quiet", rev + "^{commit}"])
    return proc.returncode == 0


def parse_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        fail("--days must be an integer between 1 and 366", 2)
    if not 1 <= days <= MAX_DAYS:
        fail("--days must be an integer between 1 and 366", 2)
    return days


def fetch_timestamps(root, today, rev, days=DAYS, author=None, no_merges=False):
    # An unborn HEAD (git init with no commits) is a valid empty repository.
    if not commit_exists(root, rev):
        if rev == "HEAD":
            return []
        fail("unknown revision: {}".format(rev), 2)

    # --since filters by committer date; keep a margin and filter by author
    # date in Python so timezone / boundary cases are not silently dropped.
    start = today - timedelta(days=days - 1)
    since = start - timedelta(days=SINCE_MARGIN_DAYS)
    command = ["-C", root, "log"]
    if author:
        command.append("--author={}".format(author))
    if no_merges:
        command.append("--no-merges")
    command += [
        "--since={}T00:00:00".format(since.isoformat()),
        "--pretty=format:%at",
        rev,
    ]
    proc = git(command)
    if proc.returncode != 0:
        detail = proc.stderr.strip().splitlines()
        fail("git log failed: {}".format(detail[0] if detail else "unknown error"), 1)
    return [int(line) for line in proc.stdout.splitlines() if line.strip()]


def count_by_day(timestamps, today, days=DAYS):
    counts = {today - timedelta(days=offset): 0 for offset in range(days)}
    for ts in timestamps:
        day = datetime.fromtimestamp(ts).date()
        if day in counts:
            counts[day] += 1
    return counts


def day_series(counts, today, days):
    """Yield (date, count) pairs oldest -> newest for the requested window."""
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        yield day, counts[day]


def render_json(repo, rev, counts, today, days):
    payload = {
        "repo": repo,
        "rev": rev,
        "days": [
            {"date": day.isoformat(), "count": count}
            for day, count in day_series(counts, today, days)
        ],
        "total": sum(counts.values()),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="git7",
        description="Count git commits per day over the last N days.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        metavar="PATH",
        help="git repository or a subdirectory (default: .)",
    )
    parser.add_argument(
        "--days",
        default=str(DAYS),
        metavar="N",
        help="number of days to show, 1..366 (default: 7)",
    )
    parser.add_argument(
        "--rev",
        default="HEAD",
        metavar="REV",
        help="branch, tag, or commit to inspect (default: HEAD)",
    )
    parser.add_argument(
        "--author",
        default=None,
        metavar="PATTERN",
        help="only count commits whose author matches PATTERN (git --author)",
    )
    parser.add_argument(
        "--no-merges",
        action="store_true",
        help="exclude merge commits",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a JSON object instead of text lines",
    )
    parser.add_argument(
        "--total",
        action="store_true",
        help="append a \"total N\" line in text mode (ignored with --json)",
    )
    args = parser.parse_args(argv)

    days = parse_days(args.days)
    today = date.today()
    root = repo_root(args.path)
    timestamps = fetch_timestamps(
        root,
        today,
        args.rev,
        days=days,
        author=args.author,
        no_merges=args.no_merges,
    )
    counts = count_by_day(timestamps, today, days)

    if args.json:
        print(render_json(root, args.rev, counts, today, days))
        return 0

    for day, count in day_series(counts, today, days):
        print("{}  {}".format(day.isoformat(), count))
    if args.total:
        print("total {}".format(sum(counts.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
