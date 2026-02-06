## 需求

假设我有一个PatchSet，如何基于这个PatchSet，通过tree-sitter或者别的方案获取这个git diff涉及代码的完整定义和相关定义？

这是一个非常有挑战性但也极具价值的需求。要从 `git diff` 延伸到代码的“语义上下文”，我们需要完成从**行差异（Line-based）**到**语法树（Tree-based）**再到**符号图（Graph-based）**的跨越。

以下是一份基于 Python 的实现思路和架构方案。

---

## 1. 技术栈推荐

* **基础解析**: `unidiff` (解析 Git 输出)。
* **语法分析**: `tree-sitter` (及其对应的语言库，如 `tree-sitter-python`, `tree-sitter-go`)。它比原生 `ast` 库更强大，支持增量解析且跨语言。
* **关系发现 (符号跳转)**:
  * **轻量级**: `tree-sitter` 的 `Queries`（通过 S-expression 查找特定模式）。
  * **重量级/精准**: `Pygls` (LSP 客户端) 或 `Microsoft/pyright` (针对 Python 的静态分析)，用于跨文件的定义跳转。
* **数据存储 (可选)**: 如果涉及大规模项目，可以使用 `NetworkX` 存储代码依赖图。

---

## 2. 软件整体架构

系统可以分为四个核心层：

### A. 差异提取层 (Diff Processor)

使用 `unidiff` 解析原始 diff，提取出：

* 修改的文件路径。
* 每个 `Hunk` 的起始行号和结束行号（即“变更窗口”）。

### B. 语法映射层 (Syntax Mapper)

这是连接“行”与“代码结构”的关键。

1. 加载对应文件的完整源码（当前版本或 Base 版本）。
2. 使用 `tree-sitter` 将源码解析为 **CST (Concrete Syntax Tree)**。
3. **坐标转换**: 将 `unidiff` 的行号映射到 CST 的节点。
* 调用 `node = root_node.descendant_for_point_range((start_line, 0), (end_line, 0))`。
* 向上回溯父节点，直到找到最近的 `function_definition` 或 `class_definition`。



### C. 上下文富化层 (Context Enricher)

* **完整定义获取**: 拿到节点后，通过 `node.text` 获取该函数或类的完整代码块。
* **相关定义解析**:
  * **内部引用**: 提取当前函数内调用的变量或函数名。
  * **跨文件关联**: 利用静态分析工具（如 LSP 的 `textDocument/definition`）定位这些引用在其他文件中的位置。



### D. 输出层 (Output Formatter)

将 diff 片段及其“背后的含义”封装成 JSON 或结构化对象，供下游（如 AI 辅助代码评审、自动化测试影响分析）使用。

---

## 3. 详细实现逻辑图

---

## 4. 关键实现思路

### 如何精准获取“定义”？

仅仅拿到变动的行是不够的。你需要：

1. **向上寻找边界**: 从变动行节点向上递归查找 `parent`，直到匹配到 `type` 为 `function_definition` 或 `class_definition` 的节点。这保证了即使只改了一行 `if`，你也能拿到整个函数体。
2. **处理嵌套**: 如果改动在类的方法里，你可能需要记录 `[Class -> Method]` 的层级关系。

### 如何寻找“相关定义”？

这是最难的部分。有两种策略：

* **策略一（静态启发式）**: 在 `tree-sitter` 中运行 `Query`，提取所有 `identifier`。如果这些 identifier 在当前文件的 `import` 列表里，则去追踪对应的路径。
* **策略二（LSP 调用）**: 模拟一个 IDE 行为。针对 diff 中的每个变量，向 Language Server 发送 `definition` 请求。这是最准确的，但配置环境（如安装依赖）较重。

---

## 5. 你需要关注的核心难点

1. **版本同步**: `git diff` 可能是基于旧版本的。你需要确保 `tree-sitter` 解析的源码文件与 diff 产生的版本是一致的（通常是 `HEAD` 或 `Index`）。
2. **多语言支持**: 不同语言的 `tree-sitter` 节点名称不同（比如有的叫 `function_item`，有的叫 `function_definition`）。你需要一层抽象来抹平差异。
3. **性能**: 如果一个 diff 涉及几百个文件，频繁解析语法树和跨文件搜索会很慢。建议引入缓存机制（如针对文件内容哈希进行解析结果缓存）。

---

### 下一步建议

**你想先看看如何用 `tree-sitter` 配合行号定位到一个具体的函数定义，还是直接看如何处理跨文件的“相关定义”跳转？**