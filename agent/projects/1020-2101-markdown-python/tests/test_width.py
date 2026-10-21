import unittest

from md2txt.width import char_width, display_width, pad, wrap_parts


class WidthTests(unittest.TestCase):
    def test_ascii_width(self):
        self.assertEqual(display_width("hello"), 5)
        self.assertEqual(char_width("a"), 1)

    def test_cjk_width(self):
        self.assertEqual(display_width("中文"), 4)
        self.assertEqual(char_width("中"), 2)

    def test_combining_and_zero_width(self):
        self.assertEqual(display_width("e\u0301"), 1)
        self.assertEqual(char_width("\u200b"), 0)

    def test_emoji_approximated_as_two(self):
        self.assertEqual(display_width("🍎"), 2)

    def test_pad_alignments(self):
        self.assertEqual(pad("中", 4), "中  ")
        self.assertEqual(pad("中", 4, "right"), "  中")
        self.assertEqual(pad("中", 4, "center"), " 中 ")

    def test_pad_never_truncates(self):
        self.assertEqual(pad("abcdef", 3), "abcdef")

    def test_wrap_ascii(self):
        lines = wrap_parts([("The quick brown fox jumps over the lazy dog.", False)], 20)
        self.assertEqual(
            lines,
            ["The quick brown fox", "jumps over the lazy", "dog."],
        )

    def test_wrap_cjk(self):
        lines = wrap_parts([("中文测试一二三四五六七八九十", False)], 10)
        for line in lines:
            self.assertLessEqual(display_width(line), 10)
        self.assertEqual("".join(lines), "中文测试一二三四五六七八九十")

    def test_wrap_atomic_not_split(self):
        url = "https://example.com/" + "a" * 40
        lines = wrap_parts([("see ", False), (url, True), (" now", False)], 20)
        self.assertIn(url, lines)

    def test_wrap_hard_break(self):
        lines = wrap_parts([("first line", False), ("\n", False), ("second", False)], 40)
        self.assertEqual(lines, ["first line", "second"])

    def test_wrap_indent(self):
        lines = wrap_parts([("aaa bbb ccc", False)], 7, first_indent="- ", next_indent="  ")
        self.assertEqual(lines, ["- aaa", "  bbb", "  ccc"])

    def test_wrap_zero_keeps_text(self):
        lines = wrap_parts([("a b\nc", False)], 0)
        self.assertEqual(lines, ["a b", "c"])


if __name__ == "__main__":
    unittest.main()
