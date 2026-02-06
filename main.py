import sys
from dataclasses import dataclass
from tree_sitter import Language, Parser
import tree_sitter_go as tsgo
import tree_sitter_python as tspy

GO_LANGUAGE = Language(tsgo.language())
PY_LANGUAGE = Language(tspy.language())
parser = Parser(PY_LANGUAGE)

func_def = {"go": "function_declaration", "py": "function_definition"}
cls_def = {"go": "type_declaration", "py": "class_definition"}


@dataclass
class Function:
    name: str
    start: int
    end: int
    text: str


@dataclass
class Class:
    name: str
    start: int
    end: int
    text: str


@dataclass
class Context:
    function: Function | None = None
    class_: Class | None = None


# Because the lineno is usually provided by git diff,
# the default index is one
def get_context_from_hunk(
    source_code: str, start_line: int, end_line: int, is_zero_indexed: bool = False
) -> Context:
    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node
    if not is_zero_indexed:
        start_point = (start_line - 1, 0)
        end_point = (end_line - 1, 0)
    else:
        start_point = (start_line, 0)
        end_point = (end_line, 0)
    target_node = root_node.descendant_for_point_range(start_point, end_point)
    current = target_node
    context = Context()
    while current:
        if current.type == func_def["py"]:
            assert current.text, (
                "prog internal error: should pass bytes to tree-sitter parser"
            )
            context.function = Function(
                name=_get_node_name(current),
                start=current.start_point[0] + 1,
                end=current.end_point[0] + 1,
                text=current.text.decode(),
            )
        elif current.type == cls_def["py"]:
            assert current.text, (
                "prog internal error: should pass bytes to tree-sitter parser"
            )
            context.class_ = Class(
                name=_get_node_name(current),
                start=current.start_point[0] + 1,
                end=current.end_point[0] + 1,
                text=current.text.decode(),
            )

        current = current.parent
    return context


def _get_node_name(node) -> str:
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8")
    return "unknown"


def main():
    source_code = """
class MyCalculator:
    def add(self, a, b):
        result = a + b
        return result
"""
    start_line = 4
    end_line = 5
    print(get_context_from_hunk(source_code, start_line, end_line))


if __name__ == "__main__":
    main()
