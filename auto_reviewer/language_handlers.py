"""Multi-language abstraction layer for tree-sitter based code analysis.

This module provides a unified interface for analyzing code across different programming
languages, abstracting away language-specific differences in tree-sitter node types,
parser initialization, and scope detection.
"""

from abc import ABC
from dataclasses import dataclass
from enum import Enum

import tree_sitter as ts


class Language(Enum):
    PYTHON = "python"
    GOLANG = "golang"
    RUST = "rust"


@dataclass
class LanguageConfig:
    language: Language
    file_extensions: list[str]
    scope_node_types: set[str]
    function_node_types: set[str]
    class_node_types: set[str]


class LanguageHandler(ABC):
    def __init__(self, config: LanguageConfig, parser: ts.Parser):
        self.config = config
        self.parser = parser

    def is_scope_node(self, node: ts.Node) -> bool:
        """Check if a node represents a scope (function, class, etc.).

        Args:
            node: Tree-sitter node to check

        Returns:
            True if the node is a scope node
        """
        return node.type in self.config.scope_node_types

    def get_scope_type(self, node: ts.Node) -> str | None:
        """Classify a scope node as 'function', 'class', or 'other'.

        Args:
            node: Tree-sitter node to classify

        Returns:
            'function', 'class', 'other', or None if not a scope node
        """
        if node.type in self.config.function_node_types:
            return "function"
        elif node.type in self.config.class_node_types:
            return "class"
        elif node.type in self.config.scope_node_types:
            return "other"
        return None


def detect_language(file_path: str) -> Language | None:
    """Detect the programming language from a file path.

    Args:
        file_path: Path to the file

    Returns:
        Detected Language, or None if not supported
    """
    # Map file extensions to languages
    extension_map = {
        ".py": Language.PYTHON,
        ".pyi": Language.PYTHON,
        ".go": Language.GOLANG,
        ".rs": Language.RUST,
    }

    # Extract extension from file path
    for ext, lang in extension_map.items():
        if file_path.endswith(ext):
            return lang

    return None
