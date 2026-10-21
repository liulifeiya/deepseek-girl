import unittest

from tests._util import render


class HtmlTests(unittest.TestCase):
    def test_block_html_cleaned(self):
        self.assertEqual(render("<div>Hello <b>世界</b></div>"), "Hello 世界")

    def test_br_becomes_newline(self):
        self.assertEqual(render("<div>a<br>b</div>"), "a\nb")

    def test_script_dropped(self):
        self.assertEqual(render("<script>alert(1)</script>ok"), "ok")
        self.assertEqual(render("<style>x{}</style>ok"), "ok")

    def test_comment_dropped(self):
        self.assertEqual(render("a<!-- hidden -->b"), "ab")

    def test_keep_html(self):
        self.assertEqual(render("a <b>bold</b> &amp; c", keep_html=True), "a <b>bold</b> & c")

    def test_inline_entity(self):
        self.assertEqual(render("Tom &amp; Jerry &lt;3"), "Tom & Jerry <3")

    def test_pre_content(self):
        self.assertEqual(render("<pre>a\nb</pre>"), "a\nb")

    def test_example_e(self):
        source = "<div>Hello <b>世界</b><br>第二行</div>\n\nTom &amp; Jerry &lt;3\n"
        self.assertEqual(render(source), "Hello 世界\n第二行\n\nTom & Jerry <3")


if __name__ == "__main__":
    unittest.main()
