import unittest

from tests._util import render


class InlineTests(unittest.TestCase):
    def test_emphasis_and_strike_removed(self):
        self.assertEqual(render("**粗** *斜* ~~删除~~"), "粗 斜 删除")

    def test_inline_code(self):
        self.assertEqual(render("这是 `code` 结束"), "这是 code 结束")

    def test_link_inline(self):
        self.assertEqual(render("[示例](https://example.com)"), "示例 (https://example.com)")

    def test_link_text_mode(self):
        self.assertEqual(render("[示例](https://example.com)", links="text"), "示例")

    def test_link_text_equals_url(self):
        self.assertEqual(render("[https://e.com](https://e.com)"), "https://e.com")

    def test_autolink(self):
        self.assertEqual(render("<https://e.com>"), "https://e.com")
        self.assertEqual(render("<a@b.com>"), "a@b.com")

    def test_image(self):
        self.assertEqual(render("![图](i.png)"), "图 (i.png)")
        self.assertEqual(render("![](i.png)"), "[image] (i.png)")
        self.assertEqual(render("![](i.png)", links="text"), "[image]")

    def test_softbreak_becomes_space(self):
        self.assertEqual(render("a\nb"), "a b")

    def test_hardbreak_kept(self):
        self.assertEqual(render("a  \nb"), "a\nb")
        self.assertEqual(render("a\\\nb"), "a\nb")

    def test_entity_decoded_once(self):
        self.assertEqual(render("Tom &amp; Jerry"), "Tom & Jerry")
        self.assertEqual(render("&amp;amp;"), "&amp;")

    def test_escaped_char(self):
        self.assertEqual(render(r"\*not emphasis\*"), "*not emphasis*")

    def test_example_a(self):
        source = "# 你好\n\n这是**加粗**和`代码`，见 [示例](https://example.com)。\n"
        self.assertEqual(render(source), "你好\n\n这是加粗和代码，见 示例 (https://example.com)。")


if __name__ == "__main__":
    unittest.main()
