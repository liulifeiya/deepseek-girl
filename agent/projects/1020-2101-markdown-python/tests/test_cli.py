import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from md2txt import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_main(argv, stdin_bytes=b""):
    old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes))
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = cli.main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.stdin, sys.stdout, sys.stderr = old_stdin, old_stdout, old_stderr
        # TextIOWrapper 持有 BytesIO，避免其析构时关闭底层对象
        sys.stdin = old_stdin
    return code, out.getvalue(), err.getvalue()


def run_proc(args, stdin_bytes=b"", timeout=30):
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "md2txt", *args],
        input=stdin_bytes,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


class CliTests(unittest.TestCase):
    def test_stdin_pipe(self):
        code, out, err = run_main([], "# 标题\n\nHello **world**.\n".encode())
        self.assertEqual(code, 0)
        self.assertEqual(out, "标题\n\nHello world.\n")
        self.assertEqual(err, "")

    def test_empty_stdin_zero_bytes(self):
        code, out, _ = run_main([], b"")
        self.assertEqual((code, out), (0, ""))

    def test_file_and_multi_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.md")
            b = os.path.join(tmp, "b.md")
            with open(a, "w", encoding="utf-8") as handle:
                handle.write("# A\n")
            with open(b, "w", encoding="utf-8") as handle:
                handle.write("# B\n")
            code, out, _ = run_main([a, b])
            self.assertEqual((code, out), (0, "A\n\nB\n"))
            code, single, _ = run_main([a], b"# A\n")
            self.assertEqual(single, "A\n")

    def test_dash_equals_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.md")
            with open(a, "w", encoding="utf-8") as handle:
                handle.write("# A\n")
            file_out = run_main([a])[1]
            dash_out = run_main(["-"], b"# A\n")[1]
            self.assertEqual(file_out, dash_out)

    def test_dash_twice(self):
        code, _, err = run_main(["-", "-"], b"x")
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("md2txt: "))

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.md")
            out_path = os.path.join(tmp, "out.txt")
            with open(a, "w", encoding="utf-8") as handle:
                handle.write("# A\n")
            code, out, _ = run_main(["-o", out_path, a])
            self.assertEqual((code, out), (0, ""))
            with open(out_path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "A\n")

    def test_output_dash_is_stdout(self):
        code, out, _ = run_main(["-o", "-"], b"# A\n")
        self.assertEqual((code, out), (0, "A\n"))

    def test_missing_file(self):
        code, out, err = run_main(["/nonexistent/x.md"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("md2txt: "))

    def test_output_dir_missing(self):
        code, _, err = run_main(["-o", "/nonexistent/dir/x.txt"], b"# A\n")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("md2txt: "))

    def test_unknown_encoding(self):
        code, _, err = run_main(["--encoding", "no-such-enc"], b"x")
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("md2txt: "))

    def test_bad_utf8(self):
        code, _, err = run_main([], b"\xff\xfe\x00")
        self.assertEqual(code, 1)
        self.assertIn("编码错误", err)

    def test_wrap_too_small(self):
        code, _, _ = run_main(["--wrap", "9"], b"x")
        self.assertEqual(code, 2)

    def test_unknown_option(self):
        code, _, err = run_main(["--bogus"], b"x")
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("md2txt: "))

    def test_invalid_choice(self):
        code, _, _ = run_main(["--links", "bogus"], b"x")
        self.assertEqual(code, 2)

    def test_frontmatter_stripped(self):
        source = "---\ntitle: 测试\ntags:\n  - a\n---\n正文\n"
        code, out, _ = run_main([], source.encode())
        self.assertEqual((code, out), (0, "正文\n"))

    def test_frontmatter_kept(self):
        source = "---\ntitle: 测试\n---\nbody\n"
        code, out, _ = run_main(["--keep-frontmatter"], source.encode())
        self.assertEqual(code, 0)
        self.assertIn("title: 测试", out)
        self.assertIn("---", out)
        self.assertTrue(out.endswith("body\n"))

    def test_frontmatter_false_positive(self):
        source = "---\nplain text\n---\n"
        code, out, _ = run_main([], source.encode())
        self.assertEqual(code, 0)
        self.assertIn("plain text", out)

    def test_bom(self):
        code, out, _ = run_main([], b"\xef\xbb\xbf# Hi\n")
        self.assertEqual((code, out), (0, "Hi\n"))

    def test_encoding_gbk(self):
        code, out, _ = run_main(["--encoding", "gbk"], "# 标题\n".encode("gbk"))
        self.assertEqual((code, out), (0, "标题\n"))

    def test_example_f_wrap(self):
        code, out, _ = run_main(["--wrap", "20"], b"The quick brown fox jumps over the lazy dog.\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "The quick brown fox\njumps over the lazy\ndog.\n")

    def test_version_subprocess(self):
        result = run_proc(["--version"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.decode().strip(), "md2txt 0.1.0")
        self.assertEqual(result.stderr, b"")

    def test_help_lists_options(self):
        result = run_proc(["--help"])
        self.assertEqual(result.returncode, 0)
        text = result.stdout.decode()
        for option in ("--heading-style", "--links", "--table-style", "--wrap", "--keep-html"):
            self.assertIn(option, text)

    def test_broken_pipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "big.md")
            with open(path, "w", encoding="utf-8") as handle:
                for i in range(30000):
                    handle.write(f"## 标题 {i}\n\n这是一段足够长的正文，用来撑大输出缓冲区。\n\n")
            script = (
                "import subprocess,sys;"
                f"p=subprocess.Popen([sys.executable,'-m','md2txt',{path!r}],"
                "stdout=subprocess.PIPE,stderr=subprocess.PIPE);"
                "p.stdout.readline();p.stdout.close();p.wait();"
                "print(p.returncode)"
            )
            env = dict(os.environ)
            env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            self.assertEqual(result.stdout.decode().strip(), "0")
            self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
