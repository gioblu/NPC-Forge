from dataclasses import dataclass, field
from typing import Dict, Any, List
from rich.console import Console
from tui.tools import TuiTools

import json
from pathlib import Path
from tools import TOOLS, render_tool_action

def execute_and_sync_tools(
    tools_data: list,
    context: dict,
    exec_ctx: 'ExecutionContext',
    result: 'ExecutionResult',
    thinking: str,
    global_permission: str = "ask",
    skip_tool_names: list = None
) -> list[str]:
    """
    Iterates through tool calls, renders them, executes them, and syncs context.
    Returns a list of extracted explanations (actions_taken).
    """
    if skip_tool_names is None:
        skip_tool_names = []
        
    actions_taken = []
    
    for tool_data in tools_data:
        if not isinstance(tool_data, dict):
            continue
            
        tool_name_raw = tool_data.get("name", "unknown")
        tool_name = next(iter(tool_name_raw.keys()), "unknown") if isinstance(tool_name_raw, dict) else str(tool_name_raw)
        tool_args = tool_data.get("arguments", {})

        explanation = tool_args.get("explanation", "").strip()
        if explanation and explanation not in actions_taken:
            actions_taken.append(explanation)

        exec_ctx.console.print()
        render_tool_action(
            exec_ctx.tui,
            tool_name,
            tool_args,
            explanation,
            thinking
        )

        tool_args["scripts_dir"] = Path(exec_ctx.current_bot_dir) / "scripts"
        exec_tool_name = tool_name if tool_name in TOOLS else "run_command"
        tool_module = TOOLS.get(exec_tool_name)

        if not tool_module:
            exec_ctx.console.print(f"[red]Unknown tool: {tool_name}[/red]")
            continue

        perm_prompt = f"\nShould I execute {tool_name}?"
        perm_execute = (
            global_permission == "yolo" or 
            getattr(exec_ctx.cli_args, "yes", False) or 
            getattr(exec_ctx.cli_args, "force_yes", False)
        )

        tool_call_result = tool_module.execute(
            args=tool_args,
            execute=perm_execute or exec_ctx.tui.confirm(perm_prompt),
            context=context,
            console=exec_ctx.console,
            config=exec_ctx.config
        )

        if isinstance(tool_call_result, int):
            result.exit_code = tool_call_result

        if Path(exec_ctx.context_path).exists():
            try:
                with open(exec_ctx.context_path, "r", encoding="utf-8") as f:
                    disk_context = json.load(f)
                
                # Merge disk state into in-memory context, but ONLY for keys that don't exist yet
                for key, value in disk_context.items():
                    if key == "summary" and isinstance(value, list) and isinstance(context.get("summary"), list):
                        # For summary lists, merge new items
                        for item in value:
                            if item not in context["summary"]:
                                context["summary"].append(item)
                    elif key not in context:
                        # Only add NEW keys from disk (bash scripts might add new context)
                        context[key] = value
                    # If key already exists in memory, keep the in-memory version (it's fresher)
                        
            except Exception as e:
                exec_ctx.console.print(f"[yellow]Warning: Failed to sync context from disk after tool execution: {e}[/yellow]")

        Path(exec_ctx.context_path).parent.mkdir(parents=True, exist_ok=True)
        with open(exec_ctx.context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=4, ensure_ascii=False)
            
    return actions_taken

class InterpreterResult:
    """Base marker class for interpreter results."""
    pass

@dataclass
class ExecutionResult(InterpreterResult):
    """Unified concrete result for all interpreters."""
    responses: List[str] = field(default_factory=list)
    status: str = "success"
    exit_code: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)
    ndf_objects: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Checks if the last NDF object indicates the task was explicitly finished."""
        if not self.ndf_objects:
            return False
        last_ndf = self.ndf_objects[-1]
        # Check if the LLM explicitly marked the task as done
        if last_ndf.get("status") == "done":
            return True
        # Check if the last tool called was 'finish'
        tools = last_ndf.get("tools", [])
        if tools and tools[-1].get("name") == "finish":
            return True
        return False

    def merge(self, other: 'ExecutionResult') -> None:
        """Merge another ExecutionResult into this one."""
        self.responses.extend(other.responses)
        if other.status == "rejected":
            self.status = "partial"
        self.exit_code = other.exit_code
        self.ndf_objects.extend(other.ndf_objects)

@dataclass
class ExecutionContext:
    """Holds environmental dependencies for interpretation."""
    console: Console
    tui: TuiTools
    config: Dict[str, Any]
    cli_args: Any
    current_bot_dir: str
    forge_root_dir: str
    context_path: str
    fallback: bool

class Interpreter:
    """Base class for intent interpreters."""
    def interpret(self, user_input: str, context: Dict[str, Any], exec_ctx: ExecutionContext) -> InterpreterResult:
        raise NotImplementedError("Subclasses must implement interpret()")