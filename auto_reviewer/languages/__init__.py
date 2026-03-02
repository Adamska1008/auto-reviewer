"""Concrete language handler implementations.

This module provides factory functions and implementations for specific programming languages.
Each language handler encapsulates the tree-sitter parser and language-specific configuration.
"""

from auto_reviewer.language_handlers import Language, LanguageConfig, LanguageHandler
import tree_sitter as ts


class PythonHandler(LanguageHandler):
    """Handler for Python language."""

    def __init__(self):
        """Initialize Python language handler."""
        # Lazy import to avoid issues if tree-sitter-python is not installed
        import tree_sitter_python as tspython

        config = LanguageConfig(
            language=Language.PYTHON,
            file_extensions=[".py", ".pyi"],
            scope_node_types={
                "function_definition",
                "class_definition",
                "module",
            },
            function_node_types={
                "function_definition",
            },
            class_node_types={
                "class_definition",
            },
        )
        language = ts.Language(tspython.language())
        parser = ts.Parser(language)
        super().__init__(config, parser)


class GolangHandler(LanguageHandler):
    """Handler for Go language."""

    def __init__(self):
        """Initialize Go language handler."""
        import tree_sitter_go as ts_go

        config = LanguageConfig(
            language=Language.GOLANG,
            file_extensions=[".go"],
            scope_node_types={
                "function_declaration",
                "method_declaration",
                "type_declaration",
                "type_spec",
                "interface_type",
            },
            function_node_types={
                "function_declaration",
                "method_declaration",
            },
            class_node_types={
                "type_spec",
                "interface_type",
            },
        )
        language = ts.Language(ts_go.language())
        parser = ts.Parser(language)
        super().__init__(config, parser)


class RustHandler(LanguageHandler):
    """Handler for Rust language."""

    def __init__(self):
        """Initialize Rust language handler."""
        import tree_sitter_rust as ts_rust

        config = LanguageConfig(
            language=Language.RUST,
            file_extensions=[".rs"],
            scope_node_types={
                "function_item",
                "struct_item",
                "enum_item",
                "impl_item",
                "trait_item",
                "mod_item",
                "closure_expression",
            },
            function_node_types={
                "function_item",
                "closure_expression",
            },
            class_node_types={
                "struct_item",
                "enum_item",
                "impl_item",
                "trait_item",
            },
        )
        language = ts.Language(ts_rust.language())
        parser = ts.Parser(language)
        super().__init__(config, parser)


def get_handler(language: Language) -> LanguageHandler:
    """Factory function to get a language handler for a given language.

    Args:
        language: The Language enum value

    Returns:
        A LanguageHandler instance for the specified language

    Raises:
        ValueError: If the language is not supported
    """
    handlers = {
        Language.PYTHON: PythonHandler,
        Language.GOLANG: GolangHandler,
        Language.RUST: RustHandler,
    }

    handler_class = handlers.get(language)
    if handler_class is None:
        raise ValueError(f"Unsupported language: {language}")

    return handler_class()
