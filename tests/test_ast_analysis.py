"""Tests for auto_reviewer.ast_analysis module."""

import tempfile
import os
from auto_reviewer.ast_analysis import analyze_added_code, NodeInfo


class TestAnalyzeAddedCode:
    """Test suite for analyze_added_code function."""

    def setup_method(self):
        """Create a temporary test file for each test."""
        self.temp_files = []

    def teardown_method(self):
        """Clean up temporary files after each test."""
        for temp_path in self.temp_files:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def create_temp_file(self, content: str, suffix: str = ".py") -> str:
        """Helper to create a temporary file with given content.

        Args:
            content: File content to write
            suffix: File suffix/extension

        Returns:
            Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(content)
            temp_path = f.name
        self.temp_files.append(temp_path)
        return temp_path

    def test_python_class_scope(self):
        """Test analyzing code inside a Python class."""
        code = """class MyClass:
    def my_method(self):
        x = 1
        return x
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [3])

        assert len(results) == 1
        info = results[0]
        assert info.lineno == 3
        assert info.parent_scope_type == "class"
        assert info.parent_scope is not None
        assert info.parent_scope_text is not None
        assert "class MyClass" in info.parent_scope_text

    def test_python_function_scope(self):
        """Test analyzing code inside a Python function."""
        code = """def my_function():
    y = 2
    return y
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [2])

        assert len(results) == 1
        info = results[0]
        assert info.lineno == 2
        assert info.parent_scope_type == "function"
        assert info.parent_scope is not None
        assert info.parent_scope_text is not None
        assert "def my_function" in info.parent_scope_text

    def test_python_nested_scopes(self):
        """Test analyzing code with nested scopes (class containing function)."""
        code = """class MyClass:
    def my_method(self):
        z = 3
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [3])

        assert len(results) == 1
        info = results[0]
        # Should find the innermost scope (the method, which is a function)
        # Note: Currently finds method (function) inside class
        assert info.parent_scope_type in ["function", "class"]

    def test_python_module_level(self):
        """Test analyzing code at module level (no parent scope)."""
        code = """import os
x = 1
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [2])

        assert len(results) == 1
        info = results[0]
        # Module level code should have no parent scope (or module scope)
        assert info.parent_scope is None or info.parent_scope.type == "module"
        assert info.parent_scope_type is None

    def test_python_multiple_lines(self):
        """Test analyzing multiple lines in different scopes."""
        code = """class MyClass:
    def method1(self):
        a = 1

def function1():
    b = 2
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [3, 6])

        assert len(results) == 2

        # Line 3 is inside method1 (function scope inside class)
        info1 = results[0]
        assert info1.lineno == 3
        assert info1.parent_scope_type == "function"

        # Line 6 is inside function1 (top-level function)
        info2 = results[1]
        assert info2.lineno == 6
        assert info2.parent_scope_type == "function"

    def test_python_lambda_scope(self):
        """Test analyzing code inside a lambda (should be function scope)."""
        code = """my_lambda = lambda x: x + 1
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [1])

        assert len(results) == 1
        info = results[0]
        # Lambda should be classified as function
        assert info.parent_scope_type == "function"

    def test_unsupported_file_type(self):
        """Test that unsupported file types raise ValueError."""
        code = """some content here
"""
        temp_path = self.create_temp_file(code, suffix=".unknown")

        try:
            analyze_added_code(temp_path, [1])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unsupported file type" in str(e)

    def test_golang_function_scope(self):
        """Test analyzing Go code inside a function."""
        code = """package main

func myFunction() int {
    x := 1
    return x
}
"""
        temp_path = self.create_temp_file(code, suffix=".go")
        results = analyze_added_code(temp_path, [4])

        assert len(results) == 1
        info = results[0]
        assert info.lineno == 4
        assert info.parent_scope_text is not None
        assert info.parent_scope_type == "function"
        assert "func myFunction" in info.parent_scope_text

    def test_golang_type_declaration(self):
        """Test analyzing Go code inside a type declaration."""
        code = """package main

type MyStruct struct {
    Field int
}
"""
        temp_path = self.create_temp_file(code, suffix=".go")
        results = analyze_added_code(temp_path, [4])

        assert len(results) == 1
        info = results[0]
        assert info.lineno == 4
        # Type spec should be classified as class
        assert info.parent_scope_type == "class"

    def test_rust_function_scope(self):
        """Test analyzing Rust code inside a function."""
        code = """fn main() {
    let x = 1;
}
"""
        temp_path = self.create_temp_file(code, suffix=".rs")
        results = analyze_added_code(temp_path, [2])

        assert len(results) == 1
        info = results[0]
        assert info.lineno == 2
        assert info.parent_scope_text is not None
        assert info.parent_scope_type == "function"
        assert "fn main" in info.parent_scope_text

    def test_rust_struct_scope(self):
        """Test analyzing Rust code inside a struct."""
        code = """struct MyStruct {
    field: i32,
}
"""
        temp_path = self.create_temp_file(code, suffix=".rs")
        results = analyze_added_code(temp_path, [2])

        assert len(results) == 1
        info = results[0]
        assert info.lineno == 2
        # Struct should be classified as class
        assert info.parent_scope_type == "class"

    def test_node_info_fields(self):
        """Test that NodeInfo contains all expected fields."""
        code = """def my_function():
    x = 1
"""
        temp_path = self.create_temp_file(code)
        results = analyze_added_code(temp_path, [2])

        assert len(results) == 1
        info = results[0]

        # Check all fields are present
        assert hasattr(info, "lineno")
        assert hasattr(info, "type")
        assert hasattr(info, "text")
        assert hasattr(info, "parent_scope")
        assert hasattr(info, "parent_scope_text")
        assert hasattr(info, "parent_scope_type")

        # Check field values
        assert info.lineno == 2
        assert isinstance(info.type, str)
        assert isinstance(info.text, str)
        assert info.parent_scope_type == "function"
