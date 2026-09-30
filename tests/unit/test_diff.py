from docheal.diff import DiffAnalyzer
from docheal.parser import PythonParser


def test_parse_unified_diff_line_numbers():
    diff = """diff --git a/src/a.py b/src/a.py
index 1..2 100644
--- a/src/a.py
+++ b/src/a.py
@@ -1,2 +1,2 @@
-def f(x):
+def f(x, y=1):
     return x
"""
    changed = DiffAnalyzer().parse_unified_diff(diff)[0]
    assert changed.new_path == "src/a.py"
    assert changed.added_lines == [1]
    assert changed.removed_lines == [1]


def test_signature_change_is_high_significance():
    parser = PythonParser()
    old = parser.parse_text("def f(x):\n    return x\n", "a.py")
    new = parser.parse_text("def f(x, y=1):\n    return x + y\n", "a.py")
    change = DiffAnalyzer().compare_entities(old, new)[0]
    assert change.change_type == "signature_changed"
    assert change.significance == 0.98


def test_comments_and_whitespace_are_ignored():
    parser = PythonParser()
    old = parser.parse_text("def f(x):\n    return x\n", "a.py")
    new = parser.parse_text("def f(x):\n    # explanation\n    return x\n", "a.py")
    assert DiffAnalyzer().compare_entities(old, new) == []

