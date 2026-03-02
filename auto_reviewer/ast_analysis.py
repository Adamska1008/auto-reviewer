"""AST analysis utilities for code review.

This module provides tree-sitter based code analysis with multi-language support.
It abstracts language-specific differences through the language handler system.
"""

from dataclasses import dataclass

import tree_sitter as ts

from auto_reviewer.language_handlers import detect_language, LanguageHandler
from auto_reviewer.languages import get_handler

MAX_LINE_WIDTH = 40  # Maximum line width for finding the smallest node at a line


@dataclass
class NodeInfo:
    """Information about a syntax node and its parent scope."""

    lineno: int
    type: str
    text: str
    parent_scope: ts.Node | None
    parent_scope_text: str | None
    parent_scope_type: str | None = None  # 'function', 'class', 'other', or None


def analyze_added_code(file_path: str, added_lineno: list[int]) -> list[NodeInfo]:
    """
    Analyze added code lines using tree-sitter AST.

    Automatically detects the programming language from the file extension
    and uses the appropriate language handler.

    Args:
        file_path: Path to the file to analyze
        added_lineno: List of line numbers that were added, index from 1 (for git diff output)

    Returns:
        List of NodeInfo objects containing syntax tree information

    Raises:
        ValueError: If the file language is not supported
    """
    # Detect language and get appropriate handler
    language = detect_language(file_path)
    if language is None:
        raise ValueError(f"Unsupported file type: {file_path}")

    handler = get_handler(language)
    parser = handler.parser

    with open(file_path, "rb") as f:
        code_bytes = f.read()
    tree = parser.parse(code_bytes)
    root_node = tree.root_node

    results = []
    for lineno in added_lineno:
        target_line = lineno - 1
        node = root_node.descendant_for_point_range(
            (target_line, 0), (target_line, MAX_LINE_WIDTH)
        )
        assert node is not None
        parent = find_parent_scope(node, handler)
        parent_text = parent.text.decode("utf-8") if parent and parent.text else ""
        parent_type = handler.get_scope_type(parent) if parent else None
        node_info = NodeInfo(
            lineno,
            node.type,
            node.text.decode("utf-8") if node.text else "",
            parent,
            parent_text,
            parent_type,
        )
        results.append(node_info)
    return results


def find_parent_scope(node: ts.Node, handler: LanguageHandler) -> ts.Node | None:
    """
    Find the parent scope (function or class definition) for a node.

    Uses the language handler to determine which node types represent scopes.
    Skips module-level nodes to find the actual function or class scope.

    Args:
        node: The tree-sitter node to find parent scope for
        handler: Language handler for the current file

    Returns:
        Parent scope node, or None if not found
    """
    current = node
    while current:
        if handler.is_scope_node(current):
            return current
        current = current.parent
    return None


def extract_parent_scope(infos: list[NodeInfo]) -> list[str]:
    node_set = set()
    for n in infos:
        if n.parent_scope_text and n.parent_scope_text.strip():
            node_set.add(n.parent_scope_text)
    return list(node_set)
