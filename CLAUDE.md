# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto Code Reviewer - A GitHub Action that automatically reviews code changes using any LLM provider (OpenAI, OpenRouter, etc.) and posts comments to commits.

The project uses tree-sitter for AST-based code analysis to provide rich context (parent scopes, function/class definitions) to the LLM for more accurate reviews.

## Development Commands

```bash
# Install dependencies (uses UV package manager)
uv sync

# Run the reviewer directly
uv run auto-reviewer

# Run tests
uv run pytest

# Run specific test
uv run pytest tests/test_ast_analysis.py::TestAnalyzeAddedCode::test_python_function_scope

# Run tests with coverage
uv run pytest --cov=auto_reviewer

# Build Docker image
docker build -t auto-reviewer .

# Run locally with Docker
docker run --rm \
  -e AUTO_REVIEWER_API_KEY=your_key \
  -e AUTO_REVIEWER_BASE_URL=https://api.openai.com/v1 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOSITORY=owner/repo \
  auto-reviewer
```

## Architecture

### Core Modules

- **[config.py](auto_reviewer/config.py)** - Environment variables and logging setup via loguru
- **[github.py](auto_reviewer/github.py)** - `GitHubClient` class for posting commit comments
- **[git.py](auto_reviewer/git.py)** - Git operations (diff, commit SHA, author, message)
- **[template.py](auto_reviewer/template.py)** - Jinja2 template loading and rendering
- **[llm.py](auto_reviewer/llm.py)** - LLM API calls via OpenAI client
- **[main.py](auto_reviewer/main.py)** - Main entry point, orchestrates all modules

### AST Analysis System

The AST analysis system provides multi-language code context extraction:

- **[ast_analysis.py](auto_reviewer/ast_analysis.py)** - Core AST analysis functions
  - `CodeContext` - Dataclass containing line number, parent scope node, and scope type
  - `analyze_added_code()` - Analyzes added lines and extracts parent scope context
  - `find_contained_node()` - Custom node finding algorithm for column ranges
  - `find_parent_scope()` - Traverses AST to find function/class scopes
  - `remove_duplicate_parent_scope()` - Deduplicates scopes by node identity

- **[language_handlers.py](auto_reviewer/language_handlers.py)** - Abstract language handler interface
  - `LanguageHandler` - Base class with `is_scope_node()` and `get_scope_type()` methods
  - `Language` enum - Defines supported languages (PYTHON, GOLANG, RUST)
  - `LanguageConfig` - Configuration dataclass for scope/node type mappings
  - `detect_language()` - Detects language from file extension

- **[languages/__init__.py](auto_reviewer/languages/__init__.py)** - Concrete language implementations
  - `PythonHandler` - Python support (functions, classes, modules)
  - `GolangHandler` - Go support (functions, methods, types, interfaces)
  - `RustHandler` - Rust support (functions, structs, enums, traits, impls, closures)
  - `get_handler()` - Factory function to get appropriate handler

### LSP Integration (Experimental)

- **[lsp.py](auto_reviewer/lsp.py)** - LSP client wrapper for advanced code analysis
  - `LspClient` class - Manages LSP server lifecycle and communication
  - `get_references()` - Finds symbol references via LSP
  - Designed for future features: function call analysis and reference tracking

## Main Flow

1. **Validate environment** - Check for required API keys and tokens
2. **Get git diff** - Extract diff between `HEAD~N` and HEAD (with rich context)
3. **Parse diff** - Use `unidiff` to extract added line numbers per file
4. **AST analysis** - For each added line, find parent scope (function/class) using tree-sitter
5. **Context aggregation** - Deduplicate parent scopes and organize by file
6. **Render prompt** - Use Jinja2 template ([with_analysis.j2](auto_reviewer/prompts/with_analysis.j2)) with diff + context
7. **LLM review** - Send prompt to LLM API and get review result
8. **Post results** - Print to stdout and optionally post to GitHub commit

## Key Design Decisions

### Custom Node Finding Algorithm

Uses `find_contained_node()` instead of tree-sitter's built-in `descendant_for_point_range()` to find the largest node fully contained within a column range. This is important because:
- Built-in method returns the smallest/most specific node
- Custom implementation traverses children first, then checks parent
- Returns the first matching node (deepest valid node) for better context

### CodeContext Structure

`CodeContext` is designed for LSP features (function call analysis, reference finding):
- Stores `parent_scope` as raw `ts.Node` for future LSP queries
- Provides `parent_scope_text` as a computed property (no redundant storage)
- Tracks `parent_scope_type` ('function', 'class', 'other') for quick classification
- Removed redundant fields (`type`, `text`) that were only used for display

### Language Handler Abstraction

The language handler system abstracts tree-sitter differences:
- Each language defines its own scope node types (e.g., "function_definition" vs "function_item")
- `is_scope_node()` checks if a node type is in the language's scope set
- `get_scope_type()` classifies nodes as 'function', 'class', or 'other'
- Adding new languages requires only a new handler class and config

### Multi-Commit Handling

The reviewer handles multiple commits in a single push:
- `PUSH_COMMITS_COUNT` environment variable controls how many commits to review
- Uses `HEAD~N` as base commit for diff generation
- Processes all changes across the commit range as a single review

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `AUTO_REVIEWER_API_KEY` | Yes | - | LLM API key |
| `AUTO_REVIEWER_BASE_URL` | Yes | - | LLM API base URL |
| `AUTO_REVIEWER_MODEL` | No | `gpt-4.1` | Model to use |
| `AUTO_REVIEWER_FILE_PATTERNS` | No | `*.py` | Comma-separated file patterns to review |
| `AUTO_REVIEWER_LANGUAGE` | No | `Chinese` | Output language for review |
| `AUTO_REVIEWER_DEBUG` | No | `false` | Enable debug mode (prints full prompt) |
| `GITHUB_TOKEN` | No | - | GitHub token for posting comments |
| `GITHUB_REPOSITORY` | No | - | Repository in `owner/repo` format |
| `PUSH_COMMITS_COUNT` | No | Auto-detected | Number of commits in push |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Testing

Tests are organized by functionality:
- **test_ast_analysis.py** - Tests AST analysis across all supported languages
  - Tests scope detection (function, class, module level)
  - Tests multi-line analysis and nested scopes
  - Tests unsupported file type handling
- **test_main.py** - Tests main entry point functions

Test fixtures use temporary files with realistic code samples for each language.

## Key Files

- [auto_reviewer/prompts/with_analysis.j2](auto_reviewer/prompts/with_analysis.j2) - Jinja2 template with AST context
- [action.yml](action.yml) - GitHub Action metadata and inputs
- [entrypoint.sh](entrypoint.sh) - Docker entrypoint, maps action inputs to env vars
- [Dockerfile](Dockerfile) - Multi-stage build using `ghcr.io/astral-sh/uv`
- [pyproject.toml](pyproject.toml) - Project dependencies and configuration

## Adding New Languages

To add support for a new language:

1. Install the corresponding tree-sitter language binding (e.g., `tree-sitter-javascript`)
2. Create a new handler class in [languages/__init__.py](auto_reviewer/languages/__init__.py):
   ```python
   class JavaScriptHandler(LanguageHandler):
       def __init__(self):
           import tree_sitter_javascript as ts_js
           config = LanguageConfig(
               language=Language.JAVASCRIPT,
               file_extensions=[".js", ".jsx"],
               scope_node_types={...},  # Define scope node types
               function_node_types={...},  # Define function types
               class_node_types={...},  # Define class types
           )
           language = ts.Language(ts_js.language())
           parser = ts.Parser(language)
           super().__init__(config, parser)
   ```
3. Add the language to the `Language` enum in [language_handlers.py](auto_reviewer/language_handlers.py)
4. Add file extension mapping in `detect_language()` function
5. Add the handler to `get_handler()` factory function
6. Add tests in [test_ast_analysis.py](tests/test_ast_analysis.py)
