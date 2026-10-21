"""Tests for git7.

Run from the project root:

    python3 -m unittest discover -s tests -v

The process timezone is pinned to UTC and all fixture commits use explicit
+00:00 dates, so day bucketing is deterministic.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import git7  # noqa: E402

SCRIPT = Path(git7.__file__).resolve()
TODAY = date.today()
BASE = datetime.combine(TODAY, dtime(12, 0))
LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})  (\d+)$")


def parse_text(stdout):
    counts = {}
    for line in stdout.splitlines():
        match = LINE_RE.match(line)
        if match is None:
            raise AssertionError("unexpected output line: {!r}".format(line))
        counts[match.group(1)] = int(match.group(2))
    return counts


def date_range(days):
    return [(TODAY - timedelta(days=offset)).isoformat()
            for offset in range(days - 1, -1, -1)]


class GitRepo:
    """Small temporary git repository used by the integration tests."""

    def __init__(self, name="repo"):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / name
        self.path.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.default_branch = self.git(
            "symbolic-ref", "--short", "HEAD"
        ).stdout.strip()

    def close(self):
        self._tmp.cleanup()

    def git(self, *args, env=None):
        proc = subprocess.run(
            ["git", "-C", str(self.path)] + list(args),
            capture_output=True,
            text=True,
            env=env,
        )
        if proc.returncode != 0:
            raise AssertionError(
                "git {} failed ({}): {}".format(args, proc.returncode, proc.stderr)
            )
        return proc

    def _stamp(self, days_ago=0, minute=0):
        moment = BASE - timedelta(days=days_ago) + timedelta(minutes=minute)
        return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    def _commit_env(self, author, email, days_ago, minute):
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "GIT_AUTHOR_DATE": self._stamp(days_ago, minute),
            "GIT_COMMITTER_DATE": self._stamp(days_ago, minute),
        })
        return env

    def commit(self, days_ago=0, minute=0, message="commit",
               author="Test", email="test@example.com"):
        env = self._commit_env(author, email, days_ago, minute)
        return self.git(
            "commit", "-q", "--allow-empty", "-m", message, env=env
        )

    def merge(self, branch="feature", days_ago=0, minute=0, message="merge"):
        env = self._commit_env("Merger", "merger@example.com", days_ago, minute)
        return self.git(
            "merge", "--no-ff", "-m", message, branch, env=env
        )

    def run(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT)] + list(args),
            cwd=str(cwd or self.path),
            capture_output=True,
            text=True,
        )


class CountByDayTests(unittest.TestCase):
    def timestamp(self, day, hour=12):
        return datetime.combine(day, dtime(hour, 0)).timestamp()

    def test_buckets_and_zero_fills(self):
        today = date(2026, 10, 20)
        timestamps = [
            self.timestamp(today),
            self.timestamp(today),
            self.timestamp(today - timedelta(days=1)),
            self.timestamp(today - timedelta(days=6)),
            self.timestamp(today - timedelta(days=7)),
            self.timestamp(today + timedelta(days=1)),
        ]
        counts = git7.count_by_day(timestamps, today, 7)

        self.assertEqual(len(counts), 7)
        self.assertEqual(counts[today], 2)
        self.assertEqual(counts[today - timedelta(days=1)], 1)
        self.assertEqual(counts[today - timedelta(days=6)], 1)
        self.assertEqual(sum(counts.values()), 4)

    def test_empty_input_is_all_zero(self):
        today = date(2026, 10, 20)
        counts = git7.count_by_day([], today, 7)
        self.assertEqual(len(counts), 7)
        self.assertEqual(set(counts.values()), {0})

    def test_days_one_only_counts_today(self):
        today = date(2026, 10, 20)
        timestamps = [
            self.timestamp(today),
            self.timestamp(today - timedelta(days=1)),
        ]
        counts = git7.count_by_day(timestamps, today, 1)
        self.assertEqual(list(counts), [today])
        self.assertEqual(counts[today], 1)

    def test_custom_window_ignores_older_commits(self):
        today = date(2026, 10, 20)
        timestamps = [
            self.timestamp(today - timedelta(days=2)),
            self.timestamp(today - timedelta(days=3)),
        ]
        counts = git7.count_by_day(timestamps, today, 3)
        self.assertEqual(set(counts), {
            today - timedelta(days=2),
            today - timedelta(days=1),
            today,
        })
        self.assertEqual(counts[today - timedelta(days=2)], 1)
        self.assertEqual(sum(counts.values()), 1)

    def test_day_series_runs_oldest_to_newest(self):
        today = date(2026, 10, 20)
        counts = {today - timedelta(days=offset): offset
                  for offset in range(7)}
        series = list(git7.day_series(counts, today, 7))
        self.assertEqual([day for day, _ in series],
                         [today - timedelta(days=offset)
                          for offset in range(6, -1, -1)])
        self.assertEqual([count for _, count in series], [6, 5, 4, 3, 2, 1, 0])


class Git7IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo()
        self.addCleanup(self.repo.close)

    def run_cli(self, *args, cwd=None):
        return self.repo.run(*args, cwd=cwd)

    def assert_cli_error(self, proc, code, needle):
        self.assertEqual(proc.returncode, code, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(len(proc.stderr.splitlines()), 1, proc.stderr)
        self.assertIn(needle, proc.stderr)

    def oracle(self, no_merges=False):
        args = ["log", "--pretty=format:%at"]
        if no_merges:
            args.insert(1, "--no-merges")
        output = self.repo.git(*args).stdout
        counts = {TODAY - timedelta(days=offset): 0 for offset in range(7)}
        for line in output.splitlines():
            if not line.strip():
                continue
            day = datetime.fromtimestamp(int(line)).date()
            if day in counts:
                counts[day] += 1
        return {day.isoformat(): count for day, count in counts.items()}

    def test_ac1_default_output(self):
        self.repo.commit(days_ago=6)
        self.repo.commit(days_ago=0)

        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 7)
        for line in lines:
            self.assertRegex(line, LINE_RE)
        counts = parse_text(proc.stdout)
        self.assertEqual(list(counts), date_range(7))
        self.assertEqual(counts[TODAY.isoformat()], 1)
        self.assertEqual(counts[(TODAY - timedelta(days=6)).isoformat()], 1)

    def test_ac2_zero_fill_and_stable(self):
        self.repo.commit(days_ago=6)
        self.repo.commit(days_ago=1)

        first = self.run_cli()
        second = self.run_cli()
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stderr, "")
        self.assertEqual(first.stdout, second.stdout)
        counts = parse_text(first.stdout)
        zero_days = [
            (TODAY - timedelta(days=offset)).isoformat()
            for offset in (5, 4, 3, 2, 0)
        ]
        self.assertEqual([counts[day] for day in zero_days], [0, 0, 0, 0, 0])

    def test_ac3_counts_match_oracle(self):
        self.repo.commit(days_ago=6)
        self.repo.commit(days_ago=3)
        self.repo.commit(days_ago=1)
        self.repo.commit(days_ago=0)
        self.repo.commit(days_ago=0, minute=15)

        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(parse_text(proc.stdout), self.oracle())
        self.assertEqual(parse_text(proc.stdout)[TODAY.isoformat()], 2)

    def test_ac4_subdirectory_matches_root(self):
        self.repo.commit(days_ago=0)
        subdir = self.repo.path / "a" / "b"
        subdir.mkdir(parents=True)

        root = self.run_cli()
        nested = self.run_cli(cwd=subdir)
        self.assertEqual(root.returncode, 0)
        self.assertEqual(nested.returncode, 0)
        self.assertEqual(nested.stdout, root.stdout)
        self.assertEqual(nested.stderr, "")

    def test_ac5_non_repository(self):
        plain = self.repo.path.parent / "plain dir"
        plain.mkdir()
        proc = self.repo.run(str(plain), cwd=self.repo.path.parent)
        self.assert_cli_error(proc, 2, "not a git repository")
        self.assertIn(str(plain), proc.stderr)

    def test_ac6_empty_repository(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertTrue(all(line.endswith("  0") for line in lines))
        self.assertEqual([line.split("  ")[0] for line in lines], date_range(7))

    def test_ac7_days_option_and_validation(self):
        self.repo.commit(days_ago=0)

        one = self.run_cli("--days", "1")
        self.assertEqual(one.returncode, 0)
        self.assertEqual(one.stdout.splitlines(), [
            "{}  1".format(TODAY.isoformat())
        ])

        three = self.run_cli("--days", "3")
        self.assertEqual(three.returncode, 0)
        self.assertEqual(len(three.stdout.splitlines()), 3)
        self.assertEqual(
            [line.split("  ")[0] for line in three.stdout.splitlines()],
            date_range(3),
        )

        for bad in ("0", "367", "abc", "-1"):
            proc = self.run_cli("--days", bad)
            self.assert_cli_error(proc, 2, "--days")

    def test_ac8_rev_branch_and_unknown(self):
        self.repo.commit(days_ago=0)
        self.repo.git("checkout", "-q", "-b", "feature")
        self.repo.commit(days_ago=0, minute=60, author="Alice")
        self.repo.git("checkout", "-q", self.repo.default_branch)

        default = parse_text(self.run_cli().stdout)
        feature = parse_text(self.run_cli("--rev", "feature").stdout)
        self.assertEqual(feature[TODAY.isoformat()],
                         default[TODAY.isoformat()] + 1)

        proc = self.run_cli("--rev", "no-such-branch")
        self.assert_cli_error(proc, 2, "unknown revision: no-such-branch")

    def test_ac9_author_filter(self):
        self.repo.commit(days_ago=6, author="Alice", email="alice@example.com")
        self.repo.commit(days_ago=1, author="Bob", email="bob@example.com")
        self.repo.commit(days_ago=0, author="Alice", email="alice@example.com")
        self.repo.commit(days_ago=0, minute=30, author="Bob", email="bob@example.com")

        by_name = parse_text(self.run_cli("--author", "Alice").stdout)
        by_email = parse_text(self.run_cli("--author", "alice@example.com").stdout)
        self.assertEqual(by_name, by_email)
        self.assertEqual(by_name[TODAY.isoformat()], 1)
        self.assertEqual(by_name[(TODAY - timedelta(days=6)).isoformat()], 1)
        self.assertEqual(sum(by_name.values()), 2)

        none = self.run_cli("--author", "Nobody")
        self.assertEqual(none.returncode, 0)
        self.assertEqual(none.stderr, "")
        self.assertEqual(set(parse_text(none.stdout).values()), {0})

    def test_ac10_no_merges(self):
        self.repo.commit(days_ago=6)
        self.repo.commit(days_ago=0)
        self.repo.git("checkout", "-q", "-b", "feature")
        self.repo.commit(days_ago=0, minute=60, author="Alice")
        self.repo.git("checkout", "-q", self.repo.default_branch)
        self.repo.merge(branch="feature", days_ago=0, minute=120)

        with_merges = parse_text(self.run_cli().stdout)
        without_merges = parse_text(self.run_cli("--no-merges").stdout)
        self.assertEqual(with_merges, self.oracle())
        self.assertEqual(without_merges, self.oracle(no_merges=True))
        self.assertEqual(with_merges[TODAY.isoformat()],
                         without_merges[TODAY.isoformat()] + 1)

    def test_ac11_json_output(self):
        self.repo.commit(days_ago=6)
        self.repo.commit(days_ago=0)
        self.repo.commit(days_ago=0, minute=15)

        text = parse_text(self.run_cli().stdout)
        proc = self.run_cli("--json")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        payload = json.loads(proc.stdout)
        self.assertEqual(list(payload), ["repo", "rev", "days", "total"])
        self.assertEqual(payload["repo"], self.repo.git(
            "rev-parse", "--show-toplevel"
        ).stdout.strip())
        self.assertEqual(payload["rev"], "HEAD")
        self.assertEqual(len(payload["days"]), 7)
        self.assertEqual([item["date"] for item in payload["days"]],
                         date_range(7))
        self.assertEqual(
            {item["date"]: item["count"] for item in payload["days"]},
            text,
        )
        self.assertEqual(payload["total"], sum(text.values()))
        self.assertEqual(payload["total"], 3)

        short = json.loads(self.run_cli("--json", "--days", "3").stdout)
        self.assertEqual(len(short["days"]), 3)
        self.assertEqual(short["total"], 2)

        both = self.run_cli("--json", "--total")
        self.assertEqual(both.returncode, 0)
        self.assertNotIn("total ", both.stdout)
        self.assertEqual(json.loads(both.stdout)["total"], 3)

    def test_ac16_does_not_modify_worktree(self):
        self.repo.commit(days_ago=0)
        before_status = self.repo.git("status", "--porcelain").stdout
        before_head = self.repo.git("rev-parse", "HEAD").stdout

        proc = self.run_cli("--days", "14")
        self.assertEqual(proc.returncode, 0)

        self.assertEqual(self.repo.git("status", "--porcelain").stdout,
                         before_status)
        self.assertEqual(self.repo.git("rev-parse", "HEAD").stdout,
                         before_head)


if __name__ == "__main__":
    unittest.main()
