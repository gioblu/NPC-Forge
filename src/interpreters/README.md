
## Interpreters

The Interpreter is just a class capable of interpreting a list of subtasks provided by a Decomposer. In this case interpreting means translating a subtask to a response and or one or more tool calls.

### Base class
The foundation of the interpreter system relies on two key data structures and an abstract base class:

* **`ExecutionContext`**: The environment passed to every interpreter. It holds the Rich `Console`, `TuiTools`, CLI arguments, configuration dictionaries, and file paths (`current_bot_dir`, `context_path`).
* **`ExecutionResult`**: A unified dataclass returned by all interpreters. It tracks:
  * `responses`: List of text outputs.
  * `status`: `"success"`, `"rejected"`, `"partial"`, or `"busy"`.
  * `exit_code`: The final bash/process exit code.
  * `ndf_objects`: A list of Neuro-Deterministic Format (NDF) traces for auditing and dataset saving.
  * `is_complete`: A property that checks if the last NDF object explicitly marked the task as `"done"` or called the `"finish"` tool.
  * `merge()`: A method to safely combine results from multiple subprompts or fallback attempts.
* **`Interpreter`**: The abstract base class enforcing the `interpret(user_input, context, exec_ctx)` signature.

---

### `DeterministicInterpreter`
Optimized for speed, predictability, and direct system interaction.

* **Workflow**: 
  1. Queries the `ApiProvider` (NPC-Forge server). Falls back to `LocalProvider` if offline.
  2. Parses the response for `tools`, `command`, and `explanation`.
  3. Concatenates multiple bash commands using `&&`.
  4. Executes via `subprocess.run` (with `/bin/bash`).
* **Smart Context Sync**: Before saving context to disk, it *reloads* from disk first. This ensures that any state changes made by bash scripts (e.g., via a `termy_set_context` helper) are preserved and merged with the in-memory state before appending new `[Deterministic]` summary entries.
* **Best for**: Simple greetings, direct file operations, known CLI commands.

---

### `ProbabilisticInterpreter`
Powered by LLM agents for complex, multi-step reasoning and dynamic tool calling.

* **Workflow**:
  1. Resolves the configured Agent (e.g., `"self-reflecting"`) and Provider (e.g., `"ollama"`).
  2. Enters an execution loop (1 iteration by default, up to 50 if the `--agent` flag is used).
  3. Calls `agent.run_step()`, receiving an output and an `ndf_object`.
  4. Iterates through requested tools, rendering TUI actions, prompting for user permission (unless `yolo`/`auto`), and executing the tool.
  5. Breaks the loop if the tool is `"finish"` or status is `"done"`.
* **Dataset Persistence**: Upon successful completion, it prompts the user to save the final `ndf_object` to the local `dataset/` directory, enabling continuous learning and few-shot prompting improvements.
* **Best for**: Complex refactoring, multi-step reasoning, ambiguous natural language requests.

---

### `HybridInterpreter`
Orchestrates the deterministic and probabilistic interpreters using a `Decomposer`.

* **Workflow**:
  1. Uses the injected `Decomposer` to split the user prompt into sequential subprompts.
  2. Iterates through each subprompt:
     * **Step A**: Tries the `DeterministicInterpreter` first (fast, low-cost).
     * **Step B**: If deterministic returns `"rejected"`, it falls back to the `ProbabilisticInterpreter`.
  3. **LLM Retry Loop**: If the LLM is invoked, it will retry up to `10` times per subprompt until `result.is_complete` is `True`, preventing premature halting on complex subtasks.
  4. **Merging**: Uses `ExecutionResult.merge()` to aggregate responses, NDF traces, and exit codes across all subprompts.
  5. Prints a clear, color-coded final summary (e.g., `✓ All 3 subprompts resolved successfully`).

### Features

| Feature | Description |
| :--- | :--- |
| **Unified State Merging** | The `ExecutionResult.merge()` method ensures that even if one subprompt fails, the overall trace and successful outputs are preserved (`status="partial"`). |
| **Disk-Memory Context Sync** | Prevents state loss by reading the latest context from disk before writing, capturing any side-effects from executed bash scripts. |
| **Permission Gates** | Respects `permission` flags (`"yolo"`, `"auto"`, `"ask"`). The `--yes` / `-y` CLI flag globally overrides prompts for automation. |
| **NDF Tracing** | Every step generates an NDF object, creating a complete, auditable JSON trace of the AI's "thought process" and tool calls. |

### Extending the Module

To add a new interpretation strategy (e.g., a `GraphInterpreter` that builds a dependency tree of tasks), simply inherit from the base class:

```python
from .base import Interpreter, ExecutionResult, ExecutionContext

class GraphInterpreter(Interpreter):
    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        result = ExecutionResult()
        # 1. Build task graph
        # 2. Execute topological sort
        # 3. Merge results
        return result
```

*Note: Ensure any new interpreter properly utilizes `exec_ctx.tui` for user feedback and respects the `exec_ctx.cli_args.force_yes` permission overrides.*