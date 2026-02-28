"""AST analysis utilities for code review."""

from dataclasses import dataclass

import tree_sitter as ts
import tree_sitter_python as tspython

PY_LANGUAGE = ts.Language(tspython.language())
parser = ts.Parser(language=PY_LANGUAGE)

MAX_LINE_WIDTH = 200


@dataclass
class NodeInfo:
    """Information about a syntax node and its parent scope."""

    lineno: int
    type: str
    text: str
    parent_scope: ts.Node | None
    parent_scope_text: str | None


def analyze_added_code(file_path: str, added_lineno: list[int]) -> list[NodeInfo]:
    """
    Analyze added code lines using tree-sitter AST.

    Args:
        file_path: Path to the file to analyze
        added_lineno: List of line numbers that were added

    Returns:
        List of NodeInfo objects containing syntax tree information
    """
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
        parent = find_parent_scope(node)
        parent_text = parent.text.decode("utf-8") if parent and parent.text else ""
        node_info = NodeInfo(
            lineno,
            node.type,
            node.text.decode("utf-8") if node.text else "",
            parent,
            parent_text,
        )
        results.append(node_info)
    return results


def find_parent_scope(node: ts.Node) -> ts.Node | None:
    """
    Find the parent scope (function or class definition) for a node.

    Args:
        node: The tree-sitter node to find parent scope for

    Returns:
        Parent function or class definition node, or None if not found
    """
    current = node
    while current:
        if current.type in ["function_definition", "class_definition"]:
            return current
        current = current.parent
    return None


def extract_parent_scope(infos: list[NodeInfo]) -> list[str]:
    node_set = set()
    for n in infos:
        if n.parent_scope_text and n.parent_scope_text.strip():
            node_set.add(n.parent_scope_text)
    return list(node_set)
