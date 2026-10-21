import unittest

from tests._util import render


class BlockTests(unittest.TestCase):
    def test_heading_plain(self):
        self.assertEqual(render("# 标题\n## 二级"), "标题\n\n二级")

    def test_heading_underline(self):
        self.assertEqual(render("# 标题", heading_style="underline"), "标题\n====")

    def test_heading_underline_cjk_width(self):
        self.assertEqual(render("## 中文", heading_style="underline"), "中文\n----")

    def test_heading_atx(self):
        self.assertEqual(render("### 三级", heading_style="atx"), "### 三级")

    def test_hr(self):
        self.assertEqual(render("***"), "---")

    def test_nested_list(self):
        source = "- 苹果\n  - 青苹果\n- 香蕉\n"
        self.assertEqual(render(source), "- 苹果\n  - 青苹果\n- 香蕉")

    def test_three_level_list(self):
        self.assertEqual(render("- a\n  - b\n    - c\n"), "- a\n  - b\n    - c")

    def test_ordered_start(self):
        self.assertEqual(render("3. 三\n4. 四\n"), "3. 三\n4. 四")

    def test_task_list(self):
        source = "- [x] 已完成\n- [ ] 未完成\n"
        self.assertEqual(render(source), "- [x] 已完成\n- [ ] 未完成")

    def test_loose_list_no_blank_between_items(self):
        self.assertEqual(render("- a\n\n- b\n"), "- a\n- b")

    def test_blockquote(self):
        source = "> 第一行\n> **第二行**\n>\n> 新段落\n"
        self.assertEqual(render(source), "> 第一行\n> 第二行\n>\n> 新段落")

    def test_nested_blockquote(self):
        self.assertEqual(render("> > deep\n"), "> > deep")

    def test_quote_with_list(self):
        self.assertEqual(render("> - a\n> - b\n"), "> - a\n> - b")

    def test_fenced_code_preserved(self):
        source = "```python\na\n\n  b\n```\n"
        self.assertEqual(render(source), "a\n\n  b")

    def test_tilde_fence(self):
        self.assertEqual(render("~~~js\nx\n~~~\n"), "x")

    def test_indented_code(self):
        self.assertEqual(render("    indented\n      more\n"), "indented\n  more")

    def test_code_trailing_spaces_kept(self):
        self.assertEqual(render("```\na  \n```\n"), "a  ")

    def test_paragraph_whitespace_normalized(self):
        self.assertEqual(render("\n\n\n# H\n\n\n\ntext   \n\n\n"), "H\n\ntext")

    def test_multi_block_spacing(self):
        self.assertEqual(render("# A\n\npara\n\n---\n"), "A\n\npara\n\n---")

    def test_list_item_with_code(self):
        source = "- item\n\n  ```\n  code\n  ```\n"
        self.assertEqual(render(source), "- item\n\n  code")

    def test_empty_document(self):
        self.assertEqual(render(""), "")


if __name__ == "__main__":
    unittest.main()
