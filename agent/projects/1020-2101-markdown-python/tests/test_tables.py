import unittest

from tests._util import render


class TableTests(unittest.TestCase):
    SOURCE = "| 名称 | Qty |\n|:---|---:|\n| 苹果 | 3 |\n| apple | 12 |\n"

    def test_aligned(self):
        expected = "名称   Qty\n-----  ---\n苹果     3\napple   12"
        self.assertEqual(render(self.SOURCE), expected)

    def test_tsv(self):
        self.assertEqual(
            render(self.SOURCE, table_style="tsv"),
            "名称\tQty\n苹果\t3\napple\t12",
        )

    def test_pipe(self):
        self.assertEqual(
            render(self.SOURCE, table_style="pipe"),
            "| 名称 | Qty |\n| --- | --- |\n| 苹果 | 3 |\n| apple | 12 |",
        )

    def test_center_align(self):
        source = "| a | b |\n|:---:|:---|\n| 1 | 2 |\n"
        self.assertEqual(render(source), "a  b\n-  -\n1  2")

    def test_ragged_rows_filled(self):
        source = "| a | b |\n|---|---|\n| 1 |\n"
        self.assertEqual(render(source), "a  b\n-  -\n1")

    def test_inline_markup_in_cell(self):
        source = "| a |\n|---|\n| **粗** |\n"
        self.assertEqual(render(source), "a\n--\n粗")

    def test_cjk_and_emoji_width(self):
        source = "| a | b |\n|---|---|\n| 中 | 1 |\n| 🍎 | 22 |\n"
        lines = render(source).split("\n")
        self.assertEqual(len(lines), 4)


if __name__ == "__main__":
    unittest.main()
