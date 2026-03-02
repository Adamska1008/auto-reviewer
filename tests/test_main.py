"""Tests for auto_reviewer.main module."""

from auto_reviewer.main import get_added_line_number_from_diff


def test_simple_addition():
    """Test simple line addition."""
    diff = """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -1,4 +1,5 @@
 def hello():
-    # whatever
+    print("added line")
+    print("Hello, world!")
     pass
 end
"""
    result = get_added_line_number_from_diff(diff)
    assert result == {"example.py": [2, 3]}
