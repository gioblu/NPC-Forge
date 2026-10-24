from dataclasses import dataclass, field
from typing import Dict, Any, List
from rich.console import Console
from tui.tools import TuiTools

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