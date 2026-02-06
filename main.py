import sys
import subprocess
from dataclasses import dataclass
from tree_sitter import Language, Parser
import tree_sitter_go as tsgo
import tree_sitter_python as tspy
from unidiff import PatchSet, PatchedFile
from loguru import logger
from importlib import resources

GO_LANGUAGE = Language(tsgo.language())
PY_LANGUAGE = Language(tspy.language())
parser = Parser(PY_LANGUAGE)

func_def = {"go": "function_declaration", "py": "function_definition"}
cls_def = {"go": "type_declaration", "py": "class_definition"}


# Get the git diff output in the curent work dir
def get_git_diff() -> str:
    cmd = ["git", "diff", "HEAD~1", "HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


# Works on the git repo of current dir
@logger.catch
def get_full_file_at_commit(commit_ref, file_path):
    cmd = ["git", "show", f"{commit_ref:file_path}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


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


# Get context from a basic hunk structure
# Because the lineno is usually provided by git diff,
# the default index is one
@logger.catch
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


@logger.catch
def load_prompt_resource(name):
    # 使用 files().joinpath().read_text() 读取内容
    return resources.files("prompts").joinpath(name).read_text(encoding="utf-8")


def main():
    from jinja2 import Environment, FunctionLoader

    env = Environment(loader=FunctionLoader(load_prompt_resource))

    template = env.get_template("simple.j2")
    diff_output = get_git_diff()
    prompt = template.render(diff_content=diff_output)
    logger.info(prompt)


if __name__ == "__main__":
    main()
